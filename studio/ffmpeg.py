"""FFmpeg resolution and thin wrappers.

Resolution order: DROP_STUDIO_FFMPEG env var -> ffmpeg on PATH -> the static
binary bundled with the imageio-ffmpeg wheel. imageio-ffmpeg does NOT ship
ffprobe, so media probing parses `ffmpeg -i` stderr instead — one binary, zero
system installs.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path


def ffmpeg_exe() -> str:
    override = os.environ.get("DROP_STUDIO_FFMPEG")
    if override:
        return override
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run ffmpeg with the given args (exe prepended). Raises on failure."""
    cmd = [ffmpeg_exe(), "-hide_banner", "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kwargs)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}):\n{' '.join(cmd)}\n{proc.stderr[-4000:]}")
    return proc


def probe_media(path: str | Path) -> dict:
    """Parse duration / video / audio info from `ffmpeg -i` stderr."""
    cmd = [ffmpeg_exe(), "-hide_banner", "-i", str(path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    err = proc.stderr  # ffmpeg exits non-zero for -i with no output; that's expected
    info: dict = {"duration": None, "width": None, "height": None, "fps": None, "has_audio": False}

    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", err)
    if m:
        h, mnt, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
        info["duration"] = h * 3600 + mnt * 60 + s

    m = re.search(r"Stream #.*Video:.*?\s(\d{2,5})x(\d{2,5})[\s,]", err)
    if m:
        info["width"], info["height"] = int(m.group(1)), int(m.group(2))

    m = re.search(r"(\d+(?:\.\d+)?)\s*fps", err)
    if m:
        info["fps"] = float(m.group(1))

    if re.search(r"Stream #.*Audio:", err):
        info["has_audio"] = True
    return info


def measure_loudness(path: str | Path) -> dict:
    """First loudnorm pass: measured EBU R128 stats as a dict."""
    cmd = [
        ffmpeg_exe(), "-hide_banner", "-i", str(path),
        "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, re.DOTALL)
    if not m:
        raise RuntimeError(f"loudnorm measurement failed for {path}:\n{proc.stderr[-2000:]}")
    return json.loads(m.group(0))
