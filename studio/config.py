"""Paths and cross-module constants. Everything is relative to the repo root."""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
ASSETS_DIR = REPO_ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts" / "figtree"
MUSIC_DIR = ASSETS_DIR / "music"
MODELS_DIR = REPO_ROOT / "models"
WORK_DIR = REPO_ROOT / "work"

# Sibling gadget-drop checkout — source of fonts and (via Phase 3) the video feed.
GADGET_DROP = Path(os.environ.get("GADGET_DROP_PATH", REPO_ROOT.parent / "gadget-drop"))

DEFAULT_TEMPLATE = "short-review-v1"

KOKORO_MODEL = MODELS_DIR / "kokoro-v1.0.onnx"
KOKORO_VOICES = MODELS_DIR / "voices-v1.0.bin"
KOKORO_RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"

# Audio pipeline constants
MIX_SAMPLE_RATE = 44100
VO_SCENE_LEAD_S = 0.35  # silence before a scene's VO starts
VO_SCENE_TAIL_S = 0.55  # breathing room after a scene's VO ends


def work_dir_for(date_str: str) -> Path:
    d = WORK_DIR / date_str
    d.mkdir(parents=True, exist_ok=True)
    return d
