"""QA gates — deterministic checks a finished video must pass before publish.

File gates: duration, resolution, fps, size, integrated loudness.
Layout probe: re-wraps every piece of on-screen text with the real fonts and
fails if anything exceeds its box (line-count caps must match renderer.py's
scene layouts — a golden-frame test keeps the renderer honest).
"""

import json
from pathlib import Path

from .captions import chunk_text
from .draw import TEXT_SPECS, fit_text, kinetic_fit_size
from .ffmpeg import measure_loudness, probe_media
from .fonts import font
from .theme import Theme


def probe_layout(storyboard: dict, theme: Theme) -> list[str]:
    violations: list[str] = []
    for i, scene in enumerate(storyboard["scenes"]):
        for (stype, field) in TEXT_SPECS[theme.format]:
            if scene.get("type") != stype or not scene.get(field):
                continue
            _, lines, ok = fit_text(theme, stype, field, scene[field])
            if not ok:
                violations.append(
                    f"scene[{i}]({stype}).{field}: does not fit even at minimum font size"
                    f" ({len(lines)} lines)"
                )
        if theme.format == "hero" and scene.get("cap"):
            cap_fnt = font(800, theme.caption["size"])
            joined = "  ".join(scene["cap"])
            if cap_fnt.getlength(joined) > theme.resolution[0] - theme.safe["side"] * 2:
                violations.append(f"scene[{i}] kinetic caption too wide: '{joined}'")
        vo = scene.get("vo")
        if vo:
            # kinetic caption band: same fit rule the renderer applies
            cap_w = theme.resolution[0] - theme.safe["side"] * 2
            for chunk in chunk_text(vo, max_words=theme.caption["max_words"]):
                if kinetic_fit_size(chunk.split(), theme.caption["size"], cap_w) is None:
                    violations.append(f"scene[{i}].vo caption too wide: '{chunk}'")
    return violations


def gates(video_path: Path, storyboard: dict, theme: Theme,
          duration_override: tuple | None = None) -> dict:
    qa = theme.qa
    min_s, max_s = duration_override or (qa["min_duration_s"], qa["max_duration_s"])
    report = {"video": str(video_path), "checks": [], "passed": True}

    def check(name: str, ok: bool, detail: str):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            report["passed"] = False

    info = probe_media(video_path)
    dur = info["duration"] or 0
    check("duration", min_s <= dur <= max_s, f"{dur:.1f}s (allowed {min_s}-{max_s}s)")
    check("resolution", (info["width"], info["height"]) == tuple(theme.resolution),
          f"{info['width']}x{info['height']} (want {theme.resolution[0]}x{theme.resolution[1]})")
    check("fps", info["fps"] is not None and abs(info["fps"] - theme.fps) < 0.6,
          f"{info['fps']} (want {theme.fps})")
    size_mb = video_path.stat().st_size / 1e6
    check("file_size", size_mb <= qa["max_size_mb"], f"{size_mb:.1f} MB (max {qa['max_size_mb']})")
    if qa.get("require_audio", True):
        check("has_audio", info["has_audio"], "audio stream present")
        if info["has_audio"]:
            loud = measure_loudness(video_path)
            lufs = float(loud["input_i"])
            check("loudness",
                  abs(lufs - qa["target_lufs"]) <= qa["lufs_tolerance"],
                  f"{lufs:.1f} LUFS (target {qa['target_lufs']} +/-{qa['lufs_tolerance']})")
    else:
        # Silent-by-design format: a stray audio stream is the failure.
        check("no_audio", not info["has_audio"],
              "silent as designed" if not info["has_audio"] else "unexpected audio stream")

    violations = probe_layout(storyboard, theme)
    check("text_layout", not violations, "; ".join(violations) or "all text fits")
    return report


def write_report(report: dict, out_path: Path) -> None:
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
