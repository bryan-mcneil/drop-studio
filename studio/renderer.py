"""Frame dispatch + video/audio assembly.

`render_frame(ctx, t)` is a pure function of the timeline and time — golden
tests call it directly; `render_video` streams frames straight into ffmpeg's
stdin (rawvideo), so no frame PNGs ever hit disk. The actual scene drawing
lives in the per-format packs (short_scenes.py / hero_scenes.py) selected by
the template's theme format.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import draw as D
from . import music as music_mod
from .config import MIX_SAMPLE_RATE
from .ffmpeg import ffmpeg_exe, measure_loudness
from .theme import Theme
from .timeline import Timeline


@dataclass
class SceneAssets:
    image: Image.Image | None = None
    series_xy: list | None = None


class RenderContext:
    def __init__(self, storyboard: dict, theme: Theme, timeline: Timeline):
        self.sb = storyboard
        self.theme = theme
        self.tl = timeline
        self.size = theme.resolution
        self.bg = D.gradient_bg(self.size, theme.color("bg_top"), theme.color("bg_bottom"))
        self.assets: dict[int, SceneAssets] = {}
        for slot in timeline.slots:
            a = SceneAssets()
            scene = slot.scene
            if scene.get("image"):
                a.image = D.load_product_image(scene["image"])
            if scene["type"] == "price" and scene.get("series"):
                a.series_xy = normalize_series(scene["series"], scene.get("checked_at"))
            self.assets[slot.index] = a
        # Each format brings its own drawer pack (lazy imports — the scene
        # modules import fmt_price/_pretty_date from here).
        self.chrome = None
        if theme.format == "hero":
            from . import hero_scenes

            self.drawers = hero_scenes.SCENE_DRAWERS
            hero_scenes.prepare(self)
        else:
            from . import short_scenes

            self.drawers = short_scenes.SCENE_DRAWERS
            self.chrome = short_scenes.draw_chrome
            short_scenes.prepare(self)


def normalize_series(series: list, checked_at: str | None, window_days: int = 90) -> list:
    """Sparse [date, price] change-points -> carry-forward daily -> normalized xy."""
    pts = sorted((date.fromisoformat(d), float(p)) for d, p in series)
    if not pts:
        return []
    end = date.fromisoformat(checked_at) if checked_at else pts[-1][0]
    start = max(pts[0][0], end - timedelta(days=window_days))
    daily: list[float] = []
    price = pts[0][1]
    i = 0
    day = start
    while day <= end:
        while i < len(pts) and pts[i][0] <= day:
            price = pts[i][1]
            i += 1
        daily.append(price)
        day += timedelta(days=1)
    lo, hi = min(daily), max(daily)
    span = (hi - lo) or max(hi * 0.05, 1.0)
    lo_pad, span_pad = lo - span * 0.12, span * 1.24
    n = len(daily)
    return [(idx / max(n - 1, 1), (p - lo_pad) / span_pad) for idx, p in enumerate(daily)]


def fmt_price(value) -> str:
    if value is None:
        return ""
    return f"${value:,.0f}" if float(value) == int(value) else f"${value:,.2f}"


# ---------------- frame ----------------

def render_frame(ctx: RenderContext, t: float) -> Image.Image:
    frame = ctx.bg.copy()
    d = ImageDraw.Draw(frame)
    slot = ctx.tl.slot_at(t)
    fn = ctx.drawers[slot.scene["type"]]
    fn(ctx, frame, d, slot.scene, slot, t - slot.start)
    if ctx.chrome:
        ctx.chrome(ctx, frame, t)
    return frame


def _pretty_date(iso: str) -> str:
    dt = date.fromisoformat(iso)
    return dt.strftime("%b %d").replace(" 0", " ")


# ---------------- audio ----------------

def build_mix(timeline: Timeline, vo_manifest: dict | None, storyboard: dict,
              vo_dir: Path | None, out_wav: Path) -> str:
    """VO + ducked music -> out_wav. Returns music provenance string."""
    import soundfile as sf

    sr = MIX_SAMPLE_RATE
    duration = timeline.duration + 0.3
    n = int(duration * sr)
    vo = np.zeros(n, dtype="float32")
    manifest_sr = (vo_manifest or {}).get("sample_rate")
    if vo_dir and manifest_sr:
        for slot in timeline.slots:
            if not slot.vo_wav:
                continue
            samples, wav_sr = sf.read(str(vo_dir / slot.vo_wav), dtype="float32")
            if samples.ndim > 1:
                samples = samples.mean(axis=1)
            if wav_sr != sr:
                idx = np.linspace(0, len(samples) - 1, int(len(samples) * sr / wav_sr))
                samples = np.interp(idx, np.arange(len(samples)), samples).astype("float32")
            start = int((slot.start + slot.vo_start) * sr)
            end = min(start + len(samples), n)
            vo[start:end] += samples[: end - start]

    music, provenance = music_mod.pick_track(duration, storyboard["slug"])
    music = music[:n]
    if len(music) < n:
        music = np.pad(music, ((0, n - len(music)), (0, 0)))
    gain_db = float((storyboard.get("music") or {}).get("gain_db", -17.0))
    music *= 10 ** (gain_db / 20)

    if np.any(vo):
        active = (np.abs(vo) > 0.008).astype("float32")
        k = int(0.35 * sr)
        active = np.convolve(active, np.ones(k), mode="same")
        active = np.clip(active, 0, 1)
        smooth = np.hanning(int(0.25 * sr))
        active = np.convolve(active, smooth / smooth.sum(), mode="same")
        duck = 10 ** ((-9.0 * active) / 20)
        music *= duck[:, None]

    mix = music + np.stack([vo, vo], axis=1) * 0.95
    peak = np.max(np.abs(mix))
    if peak > 0.98:
        mix *= 0.98 / peak
    sf.write(str(out_wav), mix, sr)
    return provenance


# ---------------- video ----------------

def render_video(ctx: RenderContext, mix_wav: Path | None, out_mp4: Path,
                 progress_every: int = 300) -> dict:
    """Stream frames into ffmpeg. mix_wav=None renders a silent video (-an)."""
    import subprocess

    w, h = ctx.size
    fps = ctx.theme.fps
    total_frames = int(round(ctx.tl.duration * fps))
    cmd = [
        ffmpeg_exe(), "-hide_banner", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "pipe:",
    ]
    if mix_wav is not None:
        measured = measure_loudness(mix_wav)
        loudnorm = (
            "loudnorm=I=-14:TP=-1.0:LRA=11:linear=true"
            f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
            f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
            f":offset={measured['target_offset']}"
        )
        cmd += ["-i", str(mix_wav), "-af", loudnorm]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p"]
    if mix_wav is not None:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-movflags", "+faststart", "-shortest"]
    else:
        cmd += ["-an", "-movflags", "+faststart"]
    cmd += [str(out_mp4)]
    log_path = out_mp4.with_suffix(".ffmpeg.log")
    with open(log_path, "wb") as log:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                stderr=log)
        try:
            for i in range(total_frames):
                frame = render_frame(ctx, i / fps)
                proc.stdin.write(frame.tobytes())
                if progress_every and i % progress_every == 0:
                    print(f"  frame {i}/{total_frames}")
            proc.stdin.close()
            ret = proc.wait()
        except BrokenPipeError:
            ret = proc.wait()
    if ret != 0:
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-3000:]
        raise RuntimeError(f"ffmpeg mux failed:\n{tail}")
    log_path.unlink(missing_ok=True)
    return {"frames": total_frames, "duration": ctx.tl.duration, "path": str(out_mp4)}


def export_thumbnail(ctx: RenderContext, out_jpg: Path) -> Path:
    slot = next((s for s in ctx.tl.slots if s.scene["type"] == "product"), ctx.tl.slots[0])
    frame = render_frame(ctx, slot.start + slot.duration * 0.55)
    frame.save(out_jpg, quality=92)
    return out_jpg
