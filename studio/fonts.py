"""Figtree font pipeline.

The site self-hosts Figtree as woff/woff2 (OFL licensed). Pillow's FreeType
can't reliably load woff2, so `python -m studio setup --fonts` converts the
latin woff2 files from the gadget-drop checkout into TTFs under assets/fonts/
— which ARE committed, so tests and CI never need the sibling repo.
"""

from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from .config import FONTS_DIR, GADGET_DROP

WEIGHTS = (400, 500, 600, 700, 800)


def ttf_path(weight: int) -> Path:
    return FONTS_DIR / f"figtree-latin-{weight}-normal.ttf"


def convert_fonts(source_dir: Path | None = None) -> list[Path]:
    from fontTools.ttLib import TTFont

    source_dir = source_dir or (GADGET_DROP / "public" / "fonts" / "figtree")
    if not source_dir.is_dir():
        raise FileNotFoundError(
            f"Figtree source dir not found: {source_dir} (set GADGET_DROP_PATH?)"
        )
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for weight in WEIGHTS:
        src = source_dir / f"figtree-latin-{weight}-normal.woff2"
        if not src.is_file():
            src = source_dir / f"figtree-latin-{weight}-normal.woff"
        if not src.is_file():
            raise FileNotFoundError(f"Missing Figtree weight {weight} in {source_dir}")
        font = TTFont(str(src))
        font.flavor = None  # decompress woff/woff2 container -> plain sfnt/ttf
        out = ttf_path(weight)
        font.save(str(out))
        written.append(out)
    return written


@lru_cache(maxsize=64)
def font(weight: int, size: int) -> ImageFont.FreeTypeFont:
    path = ttf_path(weight)
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} missing — run `python -m studio setup --fonts` first"
        )
    return ImageFont.truetype(str(path), size)


def fonts_ready() -> bool:
    return all(ttf_path(w).is_file() for w in WEIGHTS)
