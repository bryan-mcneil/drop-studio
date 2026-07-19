"""Music bed: licensed local tracks if present, synthesized ambient pad otherwise.

assets/music/ is gitignored except manifest.json — every real track must have a
manifest entry with source + license (Content ID risk lives here; provenance is
mandatory). The synth bed is the true-$0 fallback: a soft additive-synthesis
chord pad, deterministic per slug, no samples, no claims possible.
"""

import hashlib
import json
from pathlib import Path

import numpy as np

from .config import MIX_SAMPLE_RATE, MUSIC_DIR

# A minor-ish progression, frequencies in Hz (Am, F, C, G root voicings)
PROGRESSION = [
    (220.00, 261.63, 329.63),
    (174.61, 220.00, 261.63),
    (130.81, 196.00, 261.63),
    (196.00, 246.94, 293.66),
]
CHORD_SECONDS = 4.0


def pick_track(duration: float, slug: str) -> tuple[np.ndarray, str]:
    """Returns (stereo float32 at MIX_SAMPLE_RATE, provenance string)."""
    manifest_path = MUSIC_DIR / "manifest.json"
    if manifest_path.is_file():
        entries = json.loads(manifest_path.read_text(encoding="utf-8")).get("tracks", [])
        usable = [e for e in entries if (MUSIC_DIR / e["file"]).is_file() and e.get("license")]
        if usable:
            pick = usable[_seed(slug) % len(usable)]
            audio = _load_loop(MUSIC_DIR / pick["file"], duration)
            return audio, f"{pick['file']} ({pick['license']}, {pick.get('source', 'unknown')})"
    return synth_bed(duration, _seed(slug)), "synth-bed (generated, no third-party audio)"


def _seed(slug: str) -> int:
    return int(hashlib.sha256(slug.encode()).hexdigest()[:8], 16)


def _load_loop(path: Path, duration: float) -> np.ndarray:
    import soundfile as sf

    audio, sr = sf.read(str(path), dtype="float32", always_2d=True)
    if sr != MIX_SAMPLE_RATE:  # cheap linear resample; beds are background
        n = int(len(audio) * MIX_SAMPLE_RATE / sr)
        idx = np.linspace(0, len(audio) - 1, n)
        audio = np.stack([np.interp(idx, np.arange(len(audio)), audio[:, c]) for c in range(audio.shape[1])], axis=1)
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    need = int(duration * MIX_SAMPLE_RATE)
    reps = int(np.ceil(need / len(audio)))
    audio = np.tile(audio, (reps, 1))[:need]
    return _fade(audio.astype("float32"))


def synth_bed(duration: float, seed: int = 0) -> np.ndarray:
    """Ambient chord pad: detuned sine partials, slow attack, gentle motion."""
    rng = np.random.default_rng(seed)
    sr = MIX_SAMPLE_RATE
    n = int(duration * sr)
    t = np.arange(n) / sr
    out = np.zeros(n, dtype="float64")

    rotation = [PROGRESSION[(i + rng.integers(0, 4)) % 4] for i in range(int(np.ceil(duration / CHORD_SECONDS)))]
    for c, chord in enumerate(rotation):
        start, end = c * CHORD_SECONDS, min((c + 1) * CHORD_SECONDS, duration)
        if start >= duration:
            break
        seg = slice(int(start * sr), int(end * sr))
        ts = t[seg]
        env = _chord_env(len(ts), sr)
        for freq in chord:
            detune = 1 + rng.normal(0, 0.0015)
            for mult, amp in ((1.0, 1.0), (2.0, 0.35), (3.0, 0.12)):
                phase = rng.uniform(0, 2 * np.pi)
                out[seg] += amp * env * np.sin(2 * np.pi * freq * detune * mult * ts + phase)

    # slow amplitude shimmer so the pad breathes
    out *= 0.85 + 0.15 * np.sin(2 * np.pi * 0.1 * t + rng.uniform(0, 6))
    # moving-average lowpass to soften highs (vectorized FIR)
    kernel = np.hanning(48)
    kernel /= kernel.sum()
    out = np.convolve(out, kernel, mode="same")

    peak = np.max(np.abs(out)) or 1.0
    out = out / peak * 0.5
    stereo = np.stack([out, np.roll(out, int(0.008 * sr))], axis=1).astype("float32")
    return _fade(stereo)


def _chord_env(n: int, sr: int) -> np.ndarray:
    attack = min(int(0.8 * sr), max(n // 3, 1))
    release = min(int(1.2 * sr), max(n // 3, 1))
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] *= np.linspace(1, 0.25, release)
    return env


def _fade(stereo: np.ndarray, fade_s: float = 1.5) -> np.ndarray:
    sr = MIX_SAMPLE_RATE
    n = len(stereo)
    f = min(int(fade_s * sr), n // 2)
    stereo[:f] *= np.linspace(0, 1, f)[:, None]
    stereo[-f:] *= np.linspace(1, 0, f)[:, None]
    return stereo
