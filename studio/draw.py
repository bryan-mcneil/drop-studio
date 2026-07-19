"""Drawing primitives shared by all scenes: easing, text layout, cards,
sparkline, Ken Burns, placeholder art. Everything is pure Pillow."""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .fonts import font  # noqa: F401  (re-exported for scene code)
from .theme import mix  # noqa: F401  (re-exported: D.mix blends RGB tuples)


# ---------- easing ----------

def clamp01(u: float) -> float:
    return 0.0 if u < 0 else 1.0 if u > 1 else u


def ease_out_cubic(u: float) -> float:
    u = clamp01(u)
    return 1 - (1 - u) ** 3


def ease_in_out(u: float) -> float:
    u = clamp01(u)
    return u * u * (3 - 2 * u)


def ease_out_back(u: float) -> float:
    """Slight overshoot — used for chips/pills springing in."""
    u = clamp01(u)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2


def anim(t: float, start: float, dur: float, ease=ease_out_cubic) -> float:
    """Progress [0,1] of an animation starting at `start` lasting `dur`."""
    if dur <= 0:
        return 1.0
    return ease((t - start) / dur)


# ---------- text ----------

def wrap_text(text: str, fnt, max_width: int) -> list[str]:
    lines: list[str] = []
    for raw_line in text.split("\n"):
        words = raw_line.split()
        cur = ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if fnt.getlength(trial) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


# On-screen text specs: (weight, max_size, min_size, max_lines, box_name).
# The renderer draws with these and the QA layout probe checks with these —
# one table, no drift.
TEXT_SPECS = {
    ("hook", "text"): (800, 96, 64, 4, "body"),
    ("product", "product_name"): (700, 54, 42, 2, "card_inner"),
    ("feature", "title"): (700, 62, 46, 2, "feature_text"),
    ("feature", "detail"): (500, 44, 36, 3, "feature_text"),
    ("cta", "text"): (500, 54, 40, 1, "body"),
}


def box_width(theme, name: str) -> int:
    w = theme.resolution[0]
    side = theme.safe["side"]
    return {
        "body": w - side * 2,
        "card_inner": 880 - 120,               # product card minus padding
        "feature_text": (w - side * 2) - 260,  # feature card minus check gutter
    }[name]


def fit_text(theme, scene_type: str, field: str, text: str):
    """Step the font size down until the text wraps within its spec.

    Returns (font, lines, ok). When even min_size overflows, ok is False and
    the min-size layout is returned so the renderer can still draw best-effort.
    """
    weight, max_size, min_size, max_lines, box = TEXT_SPECS[(scene_type, field)]
    max_w = box_width(theme, box)
    size = max_size
    while True:
        fnt = font(weight, size)
        lines = wrap_text(text, fnt, max_w)
        ok = len(lines) <= max_lines and all(fnt.getlength(l) <= max_w for l in lines)
        if ok or size <= min_size:
            return fnt, lines, ok
        size = max(size - 6, min_size)


def text_block_height(lines: list[str], fnt, line_gap: int) -> int:
    ascent, descent = fnt.getmetrics()
    line_h = ascent + descent
    return len(lines) * line_h + max(len(lines) - 1, 0) * line_gap


def draw_text_lines(draw: ImageDraw.ImageDraw, lines: list[str], fnt, x: int, y: int,
                    fill, align: str = "center", box_w: int = 0, line_gap: int = 8) -> int:
    """Draw wrapped lines; returns the y after the block."""
    ascent, descent = fnt.getmetrics()
    line_h = ascent + descent
    for line in lines:
        if align == "center" and box_w:
            lx = x + (box_w - fnt.getlength(line)) / 2
        elif align == "right" and box_w:
            lx = x + box_w - fnt.getlength(line)
        else:
            lx = x
        draw.text((lx, y), line, font=fnt, fill=fill)
        y += line_h + line_gap
    return y


# ---------- shapes ----------

def rounded_rect(draw: ImageDraw.ImageDraw, box, radius: int, fill=None, outline=None, width: int = 1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def pill(draw: ImageDraw.ImageDraw, cx: int, cy: int, text: str, fnt, pad_x: int, pad_y: int,
         bg, fg, scale: float = 1.0) -> tuple:
    """Centered pill; returns its bounding box."""
    if scale <= 0:
        return (cx, cy, cx, cy)
    w = fnt.getlength(text) + pad_x * 2
    ascent, descent = fnt.getmetrics()
    h = ascent + descent + pad_y * 2
    w, h = w * scale, h * scale
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    draw.rounded_rectangle(box, radius=int(h / 2), fill=bg)
    if scale > 0.55:  # skip text while the pill is tiny
        draw.text((cx - fnt.getlength(text) / 2, cy - (ascent + descent) / 2), text, font=fnt, fill=fg)
    return box


def check_mark(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, circle_fill, tick_fill,
               progress: float = 1.0):
    """Brand circle with a drawn vector tick (Figtree's subset lacks the glyph)."""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=circle_fill)
    p = clamp01(progress)
    if p <= 0:
        return
    a = (cx - r * 0.45, cy + r * 0.02)
    b = (cx - r * 0.12, cy + r * 0.38)
    c = (cx + r * 0.5, cy - r * 0.32)
    w = max(int(r * 0.16), 4)
    seg1 = min(p / 0.4, 1.0)
    draw.line([a, _lerp_pt(a, b, seg1)], fill=tick_fill, width=w)
    if p > 0.4:
        seg2 = (p - 0.4) / 0.6
        draw.line([b, _lerp_pt(b, c, seg2)], fill=tick_fill, width=w)
    for pt in (a, _lerp_pt(a, b, seg1)) if p <= 0.4 else (a, b, _lerp_pt(b, c, (p - 0.4) / 0.6)):
        rr = w // 2
        draw.ellipse((pt[0] - rr, pt[1] - rr, pt[0] + rr, pt[1] + rr), fill=tick_fill)


def _lerp_pt(a, b, u):
    return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)


def star_row(draw: ImageDraw.ImageDraw, cx: int, cy: int, rating: float, size: int, fill, empty):
    total_w = 5 * size + 4 * (size // 3)
    x = cx - total_w / 2 + size / 2
    for i in range(5):
        _star(draw, x, cy, size / 2, fill if i < rating else empty)
        x += size + size // 3


def _star(draw, cx, cy, r, fill):
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(angle), cy + rad * math.sin(angle)))
    draw.polygon(pts, fill=fill)


# ---------- background ----------

def gradient_bg(size: tuple, top_rgb, bottom_rgb) -> Image.Image:
    w, h = size
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        u = y / (h - 1)
        px[0, y] = tuple(round(top_rgb[i] + (bottom_rgb[i] - top_rgb[i]) * u) for i in range(3))
    bg = col.resize((w, h))
    glow = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((w * -0.35, h * -0.18, w * 1.35, h * 0.45), fill=46)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    overlay = Image.new("RGB", (w, h), (255, 255, 255))
    bg = Image.composite(overlay, bg, glow.point(lambda v: min(v, 40)))
    return bg


# ---------- images ----------

def cover_crop(img: Image.Image, box_w: int, box_h: int, zoom: float = 1.0,
               pan: tuple = (0.5, 0.5)) -> Image.Image:
    """Crop-scale an image to fill box at `zoom`, panned toward `pan` (0..1)."""
    iw, ih = img.size
    scale = max(box_w / iw, box_h / ih) * zoom
    crop_w, crop_h = box_w / scale, box_h / scale
    max_x, max_y = iw - crop_w, ih - crop_h
    x0, y0 = max_x * pan[0], max_y * pan[1]
    return img.crop((x0, y0, x0 + crop_w, y0 + crop_h)).resize((box_w, box_h), Image.BILINEAR)


def rounded_mask(size: tuple, radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def load_product_image(path: str | None) -> Image.Image | None:
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    img = Image.open(p)
    return img.convert("RGB")


def placeholder_art(box_w: int, box_h: int, base_rgb, accent_rgb) -> Image.Image:
    """Abstract tech-disc placeholder used when a scene has no product photo."""
    img = Image.new("RGB", (box_w, box_h), base_rgb)
    d = ImageDraw.Draw(img)
    cx, cy, r = box_w / 2, box_h / 2, min(box_w, box_h) * 0.34
    for i, alpha in ((2.2, 0.06), (1.7, 0.1), (1.25, 0.16)):
        rr = r * i
        shade = tuple(round(base_rgb[c] * (1 - alpha)) for c in range(3))
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=shade)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(31, 41, 55))
    d.ellipse((cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55), outline=(75, 85, 99), width=6)
    d.ellipse((cx - r * 0.16, cy - r * 0.16, cx + r * 0.16, cy + r * 0.16), fill=accent_rgb)
    return img


# ---------- sparkline ----------

def draw_sparkline(draw: ImageDraw.ImageDraw, box: tuple, series_xy: list[tuple], progress: float,
                   line_rgb, fill_rgb, dot_rgb, width: int = 7):
    """Progressive polyline reveal inside box; series_xy are normalized (0..1, 0..1 low->high)."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    pts = [(x0 + u * w, y1 - v * h) for u, v in series_xy]
    if len(pts) < 2:
        return None
    p = clamp01(progress)
    reveal = 1 + (len(pts) - 1) * p
    full = int(reveal)
    partial = reveal - full
    visible = pts[:full]
    if full < len(pts) and partial > 0:
        visible.append(_lerp_pt(pts[full - 1], pts[full], partial))
    if len(visible) >= 2:
        area = visible + [(visible[-1][0], y1), (visible[0][0], y1)]
        draw.polygon(area, fill=fill_rgb)
        draw.line(visible, fill=line_rgb, width=width, joint="curve")
        ex, ey = visible[-1]
        draw.ellipse((ex - 13, ey - 13, ex + 13, ey + 13), fill=dot_rgb)
        draw.ellipse((ex - 7, ey - 7, ex + 7, ey + 7), fill=(255, 255, 255))
        return ex, ey
    return None
