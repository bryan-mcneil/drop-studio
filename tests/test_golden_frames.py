"""Golden-frame regression tests.

Tolerance-based comparison (mean absolute pixel difference) so FreeType
anti-aliasing wiggle across environments doesn't flake, while real layout or
palette regressions fail loudly. Regenerate after an intentional design
change:  python -m studio golden --update
"""

import os

import numpy as np
import pytest
from PIL import Image

from studio.golden import GOLDEN_DIR, GOLDEN_PROBES, HERO_GOLDEN_PROBES
from studio.renderer import render_frame

# CI (different FreeType build) sets GOLDEN_TOLERANCE=6; locally stay strict.
MEAN_ABS_TOLERANCE = float(os.environ.get("GOLDEN_TOLERANCE", "3.0"))

ALL_PROBES = [("reference_context", *p) for p in GOLDEN_PROBES] + [
    ("hero_reference_context", *p) for p in HERO_GOLDEN_PROBES
]


@pytest.mark.parametrize("ctx_fixture,name,slot_i,frac", ALL_PROBES)
def test_golden_frame(request, ctx_fixture, name, slot_i, frac):
    ctx = request.getfixturevalue(ctx_fixture)
    golden_path = GOLDEN_DIR / f"{name}.png"
    assert golden_path.is_file(), f"missing golden {golden_path.name} — run `python -m studio golden`"
    slot = ctx.tl.slots[slot_i]
    frame = render_frame(ctx, slot.start + slot.duration * frac)
    golden = Image.open(golden_path).convert("RGB")
    assert frame.size == golden.size
    diff = np.abs(
        np.asarray(frame, dtype=np.int16) - np.asarray(golden, dtype=np.int16)
    ).mean()
    assert diff <= MEAN_ABS_TOLERANCE, (
        f"{name}: mean abs pixel diff {diff:.2f} > {MEAN_ABS_TOLERANCE}"
        " (design change? regenerate goldens deliberately)"
    )


@pytest.mark.parametrize("ctx_fixture", ["reference_context", "hero_reference_context"])
def test_frames_are_not_blank(request, ctx_fixture):
    ctx = request.getfixturevalue(ctx_fixture)
    for slot in ctx.tl.slots:
        frame = render_frame(ctx, slot.start + slot.duration * 0.8)
        assert np.asarray(frame).std() > 10, f"scene {slot.scene['type']} rendered ~blank"
