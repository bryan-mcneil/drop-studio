"""Slow end-to-end test: mini storyboard -> mix -> mp4 -> QA gates.

Uses backend "none" (no TTS dependency) and a short two-scene storyboard, with
the QA duration gate overridden to the mini length.
"""

import pytest

from studio.ffmpeg import probe_media
from studio.qa import gates
from studio.renderer import RenderContext, build_mix, render_video
from studio.theme import load_theme
from studio.timeline import build_timeline
from studio.voice import synthesize_scenes

MINI_SB = {
    "version": 1,
    "template": "short-review-v1",
    "slug": "mini-e2e",
    "voice": {"backend": "none"},
    "music": {"mode": "auto", "gain_db": -17.0},
    "scenes": [
        {"type": "hook", "duration": 4.0, "text": "Mini pipeline test", "sub": "E2E",
         "vo": "This is the mini end to end pipeline test."},
        {"type": "cta", "duration": 4.0, "text": "Full review + live price history",
         "url": "gadgetdrop.tech", "vo": "Link in the description."},
    ],
}


@pytest.mark.slow
def test_mini_pipeline(tmp_path):
    manifest = synthesize_scenes(MINI_SB, tmp_path / "vo", backend="none")
    theme = load_theme("short-review-v1")
    tl = build_timeline(MINI_SB, manifest, max_words=theme.caption["max_words"])
    ctx = RenderContext(MINI_SB, theme, tl)

    mix_wav = tmp_path / "mix.wav"
    provenance = build_mix(tl, manifest, MINI_SB, None, mix_wav)
    assert "synth-bed" in provenance
    out = tmp_path / "final.mp4"
    stats = render_video(ctx, mix_wav, out, progress_every=0)
    assert out.is_file() and stats["frames"] == int(tl.duration * 30)

    info = probe_media(out)
    assert (info["width"], info["height"]) == (1080, 1920)

    report = gates(out, MINI_SB, theme, duration_override=(5, 20))
    failed = [c for c in report["checks"] if not c["ok"]]
    assert report["passed"], f"QA failed: {failed}"
