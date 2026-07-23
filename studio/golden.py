"""Golden-frame generation for the renderer tests.

The canonical scene set comes from the committed sample fixtures with a
backend-"none" voice manifest (estimated durations), so goldens are fully
deterministic: no TTS, no network, no clock. Regenerate deliberately after an
intentional design change with:  python -m studio golden --update
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GOLDEN_DIR = REPO / "tests" / "golden"
FIXTURES = REPO / "tests" / "fixtures"

# (name, slot index, fraction into the scene) — one probe per scene type,
# late-scene fractions so intro animations are settled.
GOLDEN_PROBES = [
    ("hook", 0, 0.85),
    ("product", 1, 0.60),
    ("feature", 2, 0.80),
    ("feature_scan", 4, 0.80),
    ("price", 5, 0.90),
    ("cta", 6, 0.75),
]

# Hero probes: slot 3 is the scan-viz feature (conic sweep + rings + count-up);
# price at 0.9 (t=7.2s) covers the finished chart, ping halo, verdict chip and
# fine print.
HERO_GOLDEN_PROBES = [
    ("hero_hook", 0, 0.85),
    ("hero_product", 1, 0.60),
    ("hero_feature", 3, 0.80),
    ("hero_price", 5, 0.90),
]


def _fixtures():
    post = json.loads((FIXTURES / "sample_post.json").read_text(encoding="utf-8"))
    price = json.loads((FIXTURES / "sample_price.json").read_text(encoding="utf-8"))
    creative = json.loads((FIXTURES / "sample_creative.json").read_text(encoding="utf-8"))
    return post, price, creative


def build_reference_context():
    from .renderer import RenderContext
    from .storyboard import build
    from .theme import load_theme
    from .timeline import build_timeline
    from .voice import synthesize_scenes
    import tempfile

    post, price, creative = _fixtures()
    sb = build(post, images=[], price=price, creative=creative)
    with tempfile.TemporaryDirectory() as td:
        manifest = synthesize_scenes(sb, Path(td), backend="none")
    theme = load_theme(sb["template"])
    tl = build_timeline(sb, manifest, max_words=theme.caption["max_words"])
    return RenderContext(sb, theme, tl)


def build_hero_reference_context():
    from .renderer import RenderContext
    from .storyboard import build_hero
    from .theme import load_theme
    from .timeline import build_timeline

    post, price, creative = _fixtures()
    sb = build_hero(post, images=[], price=price, creative=creative)
    theme = load_theme(sb["template"])
    tl = build_timeline(sb, None, max_words=theme.caption["max_words"])
    return RenderContext(sb, theme, tl)


def generate(update: bool = False) -> list[Path]:
    from .renderer import render_frame

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for ctx, probes in ((build_reference_context(), GOLDEN_PROBES),
                        (build_hero_reference_context(), HERO_GOLDEN_PROBES)):
        for name, slot_i, frac in probes:
            slot = ctx.tl.slots[slot_i]
            frame = render_frame(ctx, slot.start + slot.duration * frac)
            out = GOLDEN_DIR / f"{name}.png"
            if out.exists() and not update:
                continue
            frame.save(out)
            written.append(out)
    return written
