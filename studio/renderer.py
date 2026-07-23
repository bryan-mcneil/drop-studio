"""Scene composition + video/audio assembly.

`render_frame(ctx, t)` is a pure function of the timeline and time — golden
tests call it directly; `render_video` streams frames straight into ffmpeg's
stdin (rawvideo), so no frame PNGs ever hit disk.
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import draw as D
from . import music as music_mod
from .config import MIX_SAMPLE_RATE
from .ffmpeg import ffmpeg_exe, measure_loudness
from .fonts import font
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
        # The ambient ladder: the product's real price series, drawn faintly
        # behind every scene, revealing over the whole video. Real data only —
        # no series, no line.
        self.ladder_xy: list | None = None
        for slot in timeline.slots:
            a = SceneAssets()
            scene = slot.scene
            if scene.get("image"):
                a.image = D.load_product_image(scene["image"])
            if scene["type"] == "price" and scene.get("series"):
                a.series_xy = normalize_series(scene["series"], scene.get("checked_at"))
                self.ladder_xy = a.series_xy
            self.assets[slot.index] = a
        if theme.format == "hero":
            from . import hero_scenes

            self.drawers = hero_scenes.SCENE_DRAWERS
            hero_scenes.prepare(self)
        else:
            self.drawers = SCENE_DRAWERS


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
    short_chrome = ctx.theme.format == "short"
    if short_chrome:
        _ambient_ladder(ctx, d, t)
    slot = ctx.tl.slot_at(t)
    tl = t - slot.start
    scene = slot.scene
    fn = ctx.drawers[scene["type"]]
    fn(ctx, frame, d, scene, slot, tl)
    if short_chrome:
        _watermark(ctx, d, t)
        _caption(ctx, frame, t)
    return frame


def _ambient_ladder(ctx: RenderContext, d: ImageDraw.ImageDraw, t: float):
    if not ctx.ladder_xy or len(ctx.ladder_xy) < 2:
        return
    w, h = ctx.size
    top, bottom = h * 0.42, h * 0.68  # mid-frame band, occluded by cards
    color = D.mix(ctx.theme.color("bg_bottom"), ctx.theme.color("brand"), 0.38)
    reveal = D.clamp01(t / max(ctx.tl.duration, 1e-6))
    pts = [(-30 + u * (w + 60), bottom - v * (bottom - top)) for u, v in ctx.ladder_xy]
    n = 2 + int((len(pts) - 2) * reveal)
    d.line(pts[:n], fill=color, width=3)


def _watermark(ctx, d, t):
    th = ctx.theme
    slot = ctx.tl.slot_at(t)
    if slot.scene["type"] == "cta":
        return  # CTA scene is the watermark
    fnt = font(700, 36)
    w, h = ctx.size
    alpha = D.anim(t, 0.8, 0.6)
    if alpha <= 0:
        return
    gw, dw = fnt.getlength("Gadget"), fnt.getlength("Drop")
    x = (w - gw - dw) / 2
    d.text((x, 92), "Gadget", font=fnt,
           fill=D.mix(th.color("bg_top"), (255, 255, 255), alpha * 0.62))
    d.text((x + gw, 92), "Drop", font=fnt,
           fill=D.mix(th.color("bg_top"), th.color("accent"), alpha * 0.8))


def _caption(ctx, frame, t):
    from .captions import active_caption

    text = active_caption(ctx.tl.captions, t)
    if not text:
        return
    th = ctx.theme
    cap = th.caption
    fnt = font(800, cap["size"])
    w = ctx.size[0]
    pad = cap["pad"]
    tw = fnt.getlength(text)
    ascent, descent = fnt.getmetrics()
    box_w, box_h = tw + pad * 2, ascent + descent + pad * 2
    x0, y0 = (w - box_w) / 2, cap["y"]
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle((x0, y0, x0 + box_w, y0 + box_h), radius=int(box_h / 2),
                         fill=(*th.color("caption_bg"), 200))
    od.text((x0 + pad, y0 + pad), text, font=fnt, fill=(*th.color("caption_ink"), 255))
    frame.paste(Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB"), (0, 0))


# ---------------- scenes ----------------

def draw_hook(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    x = th.safe["side"]
    fnt, lines, _ = D.fit_text(th, "hook", "text", scene["text"])
    block_h = D.text_block_height(lines, fnt, 12)
    y = (h - block_h) / 2 - 170
    ascent, descent = fnt.getmetrics()
    for i, line in enumerate(lines):
        p = D.anim(tl, 0.12 * i, 0.5)
        if p <= 0:
            continue
        ly = y + i * (ascent + descent + 12) + (1 - p) * 60
        color = D.mix(th.color("bg_top"), th.color("ink_invert"), p)
        d.text((x, ly), line, font=fnt, fill=color)
    # step-rule: a contiguous two-step orange stair instead of a centered underline
    bar_p = D.anim(tl, 0.5, 0.5)
    if bar_p > 0:
        by = y + block_h + 58
        w1 = 140 * min(bar_p / 0.6, 1.0)
        d.rectangle((x, by + 14, x + w1, by + 28), fill=th.color("accent"))
        if bar_p > 0.6:
            w2 = 96 * (bar_p - 0.6) / 0.4
            d.rectangle((x + 140, by, x + 140 + w2, by + 14), fill=th.color("accent"))
    chip_p = D.anim(tl, 0.9, 0.5, ease=D.ease_out_back)
    if chip_p > 0 and scene.get("sub"):
        chip_fnt = font(700, 46)
        chip_w = chip_fnt.getlength(scene["sub"]) + 76
        D.pill(d, int(x + chip_w / 2), int(y + block_h + 176), scene["sub"], chip_fnt, 38, 20,
               th.color("brand_light"), th.color("brand_deep"), scale=chip_p)


def draw_product(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    card_w, card_h = 880, 1080
    cx = (w - card_w) // 2
    cy = 330 + math.sin(tl * 1.3) * 7
    intro = D.anim(tl, 0.0, 0.5)
    cy += (1 - intro) * 80
    card = Image.new("RGB", (card_w, card_h), th.color("surface"))
    cd = ImageDraw.Draw(card)

    name_fnt, name_lines, _ = D.fit_text(th, "product", "product_name", scene["product_name"])
    ny = D.draw_text_lines(cd, name_lines, name_fnt, 60, 54, th.color("ink"), box_w=card_w - 120)
    if scene.get("rating"):
        D.star_row(cd, card_w // 2, ny + 26, scene["rating"], 42, th.color("warning"), th.color("star_empty"))
        ny += 60

    img_box = (60, ny + 20, card_w - 60, card_h - 250)
    bw, bh = img_box[2] - img_box[0], img_box[3] - img_box[1]
    asset = ctx.assets[slot.index]
    zoom = 1.06 + 0.08 * D.ease_in_out(tl / max(slot.duration, 1))
    pan = (0.5 + 0.06 * math.sin(tl * 0.35), 0.45)
    if asset.image:
        pic = D.cover_crop(asset.image, bw, bh, zoom=zoom, pan=pan)
    else:
        pic = D.cover_crop(D.placeholder_art(bw + 200, bh + 200, th.color("surface_alt"),
                                             th.color("brand")), bw, bh, zoom=zoom, pan=pan)
    card.paste(pic, (img_box[0], img_box[1]), D.rounded_mask((bw, bh), 36))

    if scene.get("price") is not None:
        price_fnt = font(800, 92)
        py = card_h - 195
        price_txt = fmt_price(scene["price"])
        cd.text((70, py), price_txt, font=price_fnt, fill=th.color("accent"))
        if scene.get("list_price") and scene["list_price"] > scene["price"]:
            # right column: struck list price on top, deal tag beneath
            lp_fnt = font(600, 46)
            lp_txt = fmt_price(scene["list_price"])
            lp_x = card_w - 70 - lp_fnt.getlength(lp_txt)
            cd.text((lp_x, py + 2), lp_txt, font=lp_fnt, fill=th.color("muted"))
            mid_y = py + 2 + lp_fnt.getmetrics()[0] // 2
            cd.line((lp_x - 6, mid_y, card_w - 64, mid_y), fill=th.color("negative"), width=5)
            pct = round((1 - scene["price"] / scene["list_price"]) * 100)
            if pct >= 5:
                chip_fnt = font(800, 44)
                asc, desc = chip_fnt.getmetrics()
                chip_w = chip_fnt.getlength(f"-{pct}%") + 52 + (asc + desc + 28) * 0.52
                pill_p = D.anim(tl, 1.0, 0.45, ease=D.ease_out_back)
                D.tag_chip(cd, int(card_w - 70 - chip_w / 2), py + 112, f"-{pct}%",
                           chip_fnt, 26, 14, th.color("accent"), (255, 255, 255), scale=pill_p)
    frame.paste(card, (cx, int(cy)), D.rounded_mask((card_w, card_h), 48))


def draw_feature(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    if scene.get("count"):
        p = D.anim(tl, 0.0, 0.4)
        if p > 0:
            todo = D.mix(th.color("bg_top"), (255, 255, 255), 0.42)
            D.step_progress(d, w // 2, 330, scene["count"], scene.get("index", 1),
                            th.color("brand"), todo, (255, 255, 255))
    card_w, card_h = w - th.safe["side"] * 2, 580
    slide = D.anim(tl, 0.1, 0.5)
    cx = th.safe["side"] + (1 - slide) * w * 0.6
    cy = 560
    card = Image.new("RGB", (card_w, card_h), th.color("surface"))
    cd = ImageDraw.Draw(card)
    D.check_mark(cd, 120, 130, 56, th.color("brand"), (255, 255, 255),
                 progress=D.anim(tl, 0.45, 0.5))
    title_fnt, title_lines, _ = D.fit_text(th, "feature", "title", scene["title"])
    ty = D.draw_text_lines(cd, title_lines, title_fnt, 210, 78, th.color("ink"),
                           align="left", line_gap=10)
    if scene.get("detail"):
        detail_fnt, detail_lines, _ = D.fit_text(th, "feature", "detail", scene["detail"])
        alpha = D.anim(tl, 0.7, 0.5)
        color = D.mix(th.color("surface"), th.color("muted"), alpha)
        D.draw_text_lines(cd, detail_lines, detail_fnt, 210, ty + 24, color, align="left", line_gap=8)
    frame.paste(card, (int(cx), cy), D.rounded_mask((card_w, card_h), 44))


def draw_price(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    head_fnt = font(800, 72)
    head = scene.get("headline") or "Is the price good right now?"
    head_lines = D.wrap_text(head, head_fnt, w - th.safe["side"] * 2)
    hp = D.anim(tl, 0.0, 0.45)
    color = D.mix(th.color("bg_top"), th.color("ink_invert"), hp)
    y = D.draw_text_lines(d, head_lines, head_fnt, th.safe["side"], 320, color,
                          box_w=w - th.safe["side"] * 2, line_gap=10)

    card_w, card_h = w - th.safe["side"] * 2, 980
    cx, cy = th.safe["side"], y + 40
    card = Image.new("RGB", (card_w, card_h), th.color("surface"))
    cd = ImageDraw.Draw(card)
    asset = ctx.assets[slot.index]

    if asset.series_xy:
        spark_box = (70, 170, card_w - 70, 560)
        # eyebrow: tracked caps + pulsing record dot — "this is live, tracked data"
        eb_fnt = font(600, 32)
        dot_pulse = 0.55 + 0.45 * abs(math.sin(tl * 2.2))
        dot_color = D.mix(th.color("surface"), th.color("accent"), dot_pulse)
        cd.ellipse((70, 84, 92, 106), fill=dot_color)
        D.tracked_caps(cd, 112, 78, "90-day tracked price", eb_fnt, th.color("muted"))
        # current price lives in the top-right corner, in the price color
        if scene.get("current") is not None:
            cur_fnt = font(800, 76)
            txt = fmt_price(scene["current"])
            tx = card_w - 70 - cur_fnt.getlength(txt)
            cd.text((tx, 130), txt, font=cur_fnt, fill=th.color("accent"))
            now_fnt = font(600, 30)
            now_w = D.tracked_caps_width("NOW", now_fnt, 5)
            D.tracked_caps(cd, card_w - 70 - now_w, 92, "NOW", now_fnt, th.color("accent"))

        # dashed line at the 90-day average: below this line = good price
        avg = scene.get("avg90")
        if avg is not None and scene.get("low90") is not None and scene.get("high90") is not None:
            # recover the normalized y for avg using the same padding rule as normalize_series
            lo, hi = scene["low90"], scene["high90"]
            span = (hi - lo) or max(hi * 0.05, 1.0)
            lo_pad, span_pad = lo - span * 0.12, span * 1.24
            avg_v = (avg - lo_pad) / span_pad
            ay = spark_box[3] - avg_v * (spark_box[3] - spark_box[1])
            D.dashed_hline(cd, spark_box[0], spark_box[2], ay, th.color("star_empty"))
            D.tracked_caps(cd, spark_box[2] - D.tracked_caps_width("AVG", font(600, 28), 4) ,
                           ay - 42, "AVG", font(600, 28), th.color("muted"), tracking=4)

        progress = D.anim(tl, 0.4, slot.duration * 0.42)
        D.draw_sparkline(cd, spark_box, asset.series_xy, progress,
                         th.color("brand"), th.color("brand_light"), th.color("accent"))
        stats = [("90-DAY LOW", scene.get("low90")), ("AVERAGE", scene.get("avg90")),
                 ("90-DAY HIGH", scene.get("high90"))]
        col_w = (card_w - 140) // 3
        for i, (label, value) in enumerate(stats):
            if value is None:
                continue
            x = 70 + i * col_w
            lbl_fnt = font(600, 30)
            lbl_w = D.tracked_caps_width(label, lbl_fnt, 3)
            D.tracked_caps(cd, x + (col_w - lbl_w) / 2, 644, label, lbl_fnt,
                           th.color("muted"), tracking=3)
            vtxt = fmt_price(value)
            cd.text((x + (col_w - font(700, 56).getlength(vtxt)) / 2, 692), vtxt,
                    font=font(700, 56), fill=th.color("ink"))
        verdict = scene.get("verdict")
        if verdict and verdict in th.verdicts:
            vp = D.anim(tl, slot.duration * 0.55, 0.5, ease=D.ease_out_back)
            spec = th.verdicts[verdict]
            D.tag_chip(cd, card_w // 2, 828, spec["label"], font(800, 52), 40, 24,
                       th.color(spec["color"]), (255, 255, 255), scale=vp)
    else:
        cd.text(((card_w - font(600, 44).getlength("We track this price daily")) / 2, 180),
                "We track this price daily", font=font(600, 44), fill=th.color("muted"))
        if scene.get("current") is not None:
            big = font(800, 150)
            txt = fmt_price(scene["current"])
            cd.text(((card_w - big.getlength(txt)) / 2, 300), txt, font=big, fill=th.color("ink"))
        line2 = "Price history builds with every check"
        cd.text(((card_w - font(500, 40).getlength(line2)) / 2, 560), line2,
                font=font(500, 40), fill=th.color("muted"))

    if scene.get("checked_at"):
        note = f"Price checked {_pretty_date(scene['checked_at'])}"
        cd.text(((card_w - font(500, 34).getlength(note)) / 2, card_h - 62), note,
                font=font(500, 34), fill=th.color("muted"))
    frame.paste(card, (cx, cy), D.rounded_mask((card_w, card_h), 44))


def draw_cta(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    grad = D.gradient_bg((w, h), th.color("brand"), th.color("brand_deep"))
    p = D.anim(tl, 0.0, 0.4)
    frame.paste(Image.blend(frame.copy(), grad, p), (0, 0))
    d = ImageDraw.Draw(frame)
    logo_fnt = font(800, 112)
    gw = logo_fnt.getlength("Gadget")
    dw = logo_fnt.getlength("Drop")
    lx = (w - gw - dw) / 2
    ly = 640 + (1 - D.anim(tl, 0.15, 0.5)) * 50
    alpha = D.anim(tl, 0.15, 0.5)
    d.text((lx, ly), "Gadget", font=logo_fnt,
           fill=D.mix(th.color("brand"), (255, 255, 255), alpha))
    d.text((lx + gw, ly), "Drop", font=logo_fnt,
           fill=D.mix(th.color("brand"), th.color("accent"), alpha))
    sub_p = D.anim(tl, 0.5, 0.5)
    if sub_p > 0 and scene.get("text"):
        sub_fnt, sub_lines, _ = D.fit_text(th, "cta", "text", scene["text"])
        color = D.mix(th.color("brand"), th.color("brand_light"), sub_p)
        d.text(((w - sub_fnt.getlength(sub_lines[0])) / 2, 830), sub_lines[0],
               font=sub_fnt, fill=color)
    pulse = 1 + 0.03 * math.sin(tl * 2.4)
    url_p = D.anim(tl, 0.8, 0.5, ease=D.ease_out_back)
    D.pill(d, w // 2, 1030, scene["url"], font(700, 60), 54, 30,
           (255, 255, 255), th.color("brand_deep"), scale=url_p * pulse)
    hint_p = D.anim(tl, 1.2, 0.5)
    if hint_p > 0:
        hint = "Link in the description"
        hint_fnt = font(600, 44)
        color = D.mix(th.color("brand"), th.color("brand_light"), hint_p)
        hy = 1160 + math.sin(tl * 2.4) * 5
        d.text(((w - hint_fnt.getlength(hint)) / 2, hy), hint, font=hint_fnt, fill=color)
        ax = w / 2
        ay = hy + 90
        d.line((ax, ay, ax, ay + 46), fill=color, width=7)
        d.line((ax - 18, ay + 28, ax, ay + 48, ax + 18, ay + 28), fill=color, width=7)


SCENE_DRAWERS = {
    "hook": draw_hook,
    "product": draw_product,
    "feature": draw_feature,
    "price": draw_price,
    "cta": draw_cta,
}


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
