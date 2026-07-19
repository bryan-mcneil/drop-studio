"""Voiceover synthesis with a pluggable backend chain: kokoro -> piper -> openai -> none.

Kokoro-82M via kokoro-onnx is the production path ($0, local, Apache 2.0).
Piper is only used if a `piper` binary is already on PATH. OpenAI TTS is the
paid fallback (needs OPENAI_API_KEY). Backend "none" skips audio and lets the
renderer fall back to estimated caption timing — the pipeline must never be
blocked on TTS.

Each scene is synthesized separately: scene duration then adapts to its real
VO length, and caption timing is exact. The manifest ties it together:
work/<date>/vo/manifest.json  {"sample_rate": 24000, "scenes": [{"index", "wav", "duration"}]}
"""

import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

from .config import KOKORO_MODEL, KOKORO_RELEASE, KOKORO_VOICES, MODELS_DIR

ESTIMATE_CHARS_PER_SEC = 15.5  # backend "none": caption timing estimate


def models_present() -> bool:
    return KOKORO_MODEL.is_file() and KOKORO_VOICES.is_file()


def download_models(force: bool = False) -> None:
    MODELS_DIR.mkdir(exist_ok=True)
    for target, min_mb in ((KOKORO_MODEL, 200), (KOKORO_VOICES, 5)):
        if target.is_file() and not force:
            print(f"already present: {target.name}")
            continue
        url = f"{KOKORO_RELEASE}/{target.name}"
        print(f"downloading {url} ...")
        tmp = target.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp)
        size_mb = tmp.stat().st_size / 1e6
        if size_mb < min_mb:
            tmp.unlink()
            raise RuntimeError(f"{target.name} download too small ({size_mb:.1f} MB) — bad release URL?")
        tmp.replace(target)
        print(f"  -> {target.name} ({size_mb:.0f} MB)")


class VoiceBackendError(RuntimeError):
    pass


def _synth_kokoro(text: str, voice: str, speed: float):
    if not models_present():
        raise VoiceBackendError(
            "Kokoro model files missing — run `python -m studio setup --models`"
        )
    from kokoro_onnx import Kokoro

    global _KOKORO
    try:
        _KOKORO
    except NameError:
        _KOKORO = Kokoro(str(KOKORO_MODEL), str(KOKORO_VOICES))
    samples, sample_rate = _KOKORO.create(text, voice=voice, speed=speed, lang="en-us")
    return samples, sample_rate


def _synth_piper(text: str, voice: str, speed: float):
    exe = shutil.which("piper")
    if not exe:
        raise VoiceBackendError("no `piper` binary on PATH")
    import tempfile

    import soundfile as sf

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.wav"
        proc = subprocess.run(
            [exe, "--model", voice, "--output_file", str(out)],
            input=text, text=True, capture_output=True,
        )
        if proc.returncode != 0:
            raise VoiceBackendError(f"piper failed: {proc.stderr[-500:]}")
        samples, sample_rate = sf.read(str(out), dtype="float32")
    return samples, sample_rate


def _synth_openai(text: str, voice: str, speed: float):
    import io
    import os

    import soundfile as sf

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise VoiceBackendError("OPENAI_API_KEY not set")
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=json.dumps(
            {"model": "gpt-4o-mini-tts", "voice": voice if voice.isalpha() else "onyx",
             "input": text, "speed": speed, "response_format": "wav"}
        ).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        samples, sample_rate = sf.read(io.BytesIO(resp.read()), dtype="float32")
    return samples, sample_rate


BACKENDS = {"kokoro": _synth_kokoro, "piper": _synth_piper, "openai": _synth_openai}
FALLBACK_CHAIN = ("kokoro", "piper", "openai")


def synthesize_scenes(storyboard: dict, out_dir: Path, backend: str | None = None) -> dict:
    """Synthesize every scene's VO. Returns and writes the manifest."""
    import numpy as np
    import soundfile as sf

    cfg = storyboard.get("voice") or {}
    requested = backend or cfg.get("backend", "kokoro")
    voice = cfg.get("voice", "am_michael")
    speed = float(cfg.get("speed", 1.0))
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {"backend": None, "voice": voice, "speed": speed, "sample_rate": None, "scenes": []}
    if requested == "none":
        for i, scene in enumerate(storyboard["scenes"]):
            vo = (scene.get("vo") or "").strip()
            manifest["scenes"].append(
                {"index": i, "wav": None,
                 "duration": round(len(vo) / ESTIMATE_CHARS_PER_SEC, 2) if vo else 0.0}
            )
        manifest["backend"] = "none"
    else:
        chain = [requested] + [b for b in FALLBACK_CHAIN if b != requested]
        for i, scene in enumerate(storyboard["scenes"]):
            vo = (scene.get("vo") or "").strip()
            if not vo:
                manifest["scenes"].append({"index": i, "wav": None, "duration": 0.0})
                continue
            samples = sample_rate = None
            for candidate in chain:
                try:
                    samples, sample_rate = BACKENDS[candidate](vo, voice, speed)
                    manifest["backend"] = candidate
                    break
                except VoiceBackendError as e:
                    print(f"voice backend '{candidate}' unavailable: {e}")
            if samples is None:
                raise VoiceBackendError(
                    "no voice backend available — use `--voice-backend none` for a captions-only render"
                )
            samples = np.asarray(samples, dtype="float32")
            wav = out_dir / f"scene-{i:02d}.wav"
            sf.write(str(wav), samples, sample_rate)
            manifest["sample_rate"] = sample_rate
            manifest["scenes"].append(
                {"index": i, "wav": wav.name, "duration": round(len(samples) / sample_rate, 3)}
            )
            chain = [manifest["backend"]]  # lock the chain after first success

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
