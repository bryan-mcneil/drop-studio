"""Template theme loading + color helpers."""

import json
from functools import lru_cache

from .config import TEMPLATES_DIR


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def mix(a: tuple, b: tuple, t: float) -> tuple[int, int, int]:
    """Linear blend between two RGB tuples, t in [0, 1]."""
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Theme:
    def __init__(self, data: dict):
        self.data = data
        self.resolution = tuple(data["resolution"])
        self.fps = data["fps"]
        self.colors = {k: hex_rgb(v) for k, v in data["colors"].items()}
        self.safe = data["safe_area"]
        self.caption = data["caption"]
        self.watermark = data["watermark"]
        self.qa = data["qa"]
        self.verdicts = data["verdicts"]

    def color(self, name: str) -> tuple[int, int, int]:
        return self.colors[name]


@lru_cache(maxsize=4)
def load_theme(template: str) -> Theme:
    path = TEMPLATES_DIR / template / "theme.json"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown template '{template}' (no {path})")
    return Theme(json.loads(path.read_text(encoding="utf-8")))
