"""Burned-in caption timing.

Shorts are watched muted about half the time, so every VO line is chunked into
short caption groups and timed inside its scene. With real TTS the scene's VO
duration is exact (we synthesized it); without VO we estimate from chars/sec.
Duration is split across chunks proportionally to character count.
"""

import re
from dataclasses import dataclass

MIN_CHUNK_S = 0.45


@dataclass
class Caption:
    text: str
    start: float  # global seconds
    end: float


def chunk_text(text: str, max_words: int = 4) -> list[str]:
    """Split VO text into caption chunks along punctuation, then word count.
    A trailing 1-2 word orphan is merged into the previous chunk."""
    chunks: list[str] = []
    for clause in re.split(r"(?<=[.,;:!?])\s+", text.strip()):
        clause = clause.strip().strip(",;:").strip()
        if not clause:
            continue
        words = clause.split()
        clause_chunks = [
            " ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)
        ]
        if len(clause_chunks) >= 2 and len(clause_chunks[-1].split()) <= 2:
            clause_chunks[-2] = f"{clause_chunks[-2]} {clause_chunks[-1]}"
            clause_chunks.pop()
        chunks.extend(clause_chunks)
    return chunks


def scene_captions(vo_text: str, scene_start: float, vo_start: float, vo_duration: float,
                   max_words: int = 4) -> list[Caption]:
    """Timeline for one scene. vo_start is the offset of speech inside the scene."""
    chunks = chunk_text(vo_text, max_words=max_words)
    if not chunks or vo_duration <= 0:
        return []
    weights = [max(len(c), 1) for c in chunks]
    total = sum(weights)
    captions: list[Caption] = []
    t = scene_start + vo_start
    for chunk, w in zip(chunks, weights):
        dur = max(vo_duration * w / total, MIN_CHUNK_S)
        captions.append(Caption(chunk, t, t + dur))
        t += dur
    # Proportional minimums can overrun the true span; rescale back onto it.
    overrun = captions[-1].end - (scene_start + vo_start + vo_duration)
    if overrun > 0.01:
        scale = vo_duration / (captions[-1].end - captions[0].start)
        t = scene_start + vo_start
        rescaled = []
        for c in captions:
            dur = (c.end - c.start) * scale
            rescaled.append(Caption(c.text, t, t + dur))
            t += dur
        captions = rescaled
    return captions


def active_caption(captions: list[Caption], t: float) -> str | None:
    for c in captions:
        if c.start <= t < c.end:
            return c.text
    return None
