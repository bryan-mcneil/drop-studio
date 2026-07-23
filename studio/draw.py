"""Drawing primitives shared by all scenes: easing, text layout, cards,
sparkline, Ken Burns, placeholder art. Everything is pure Pillow."""

import math
from functools import lru_cache
from pathlib import Path

import numpy as np
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
    if u == 0:
        return 0.0  # the closed form leaves ~2e-16 dust, which `> 0` gates see
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2


def ease_out_expo(u: float) -> float:
    """Fast start, long settle — count-ups."""
    u = clamp01(u)
    return 1.0 if u >= 1 else 1 - 2 ** (-10 * u)


def ease_in_out_cubic(u: float) -> float:
    """True cubic in-out (ease_in_out is smoothstep) — the chart reveal."""
    u = clamp01(u)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def anim(t: float, start: float, dur: float, ease=ease_out_cubic) -> float:
    """Progress [0,1] of an animation starting at `start` lasting `dur`."""
    if dur <= 0:
        return 1.0
    return ease((t - start) / dur)


def tween(t: float, frm: float, to: float, start: float, end: float,
          ease=ease_out_cubic) -> float:
    """Value tweened from `frm` to `to` over [start, end] of clock `t` — the
    hero scenes transliterate the design's tw() calls through this 1:1."""
    return frm + (to - frm) * anim(t, start, end - start, ease)


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


# On-screen text specs, keyed by template format: (weight, max_size, min_size,
# max_lines, box_name). The renderer draws with these and the QA layout probe
# checks with these — one table, no drift.
TEXT_SPECS = {
    "short": {
        ("hook", "text"): (800, 104, 64, 4, "body"),
        ("hook", "sub"): (800, 46, 34, 1, "short_pill"),
        ("product", "product_name"): (800, 78, 54, 2, "short_card_inner"),
        ("feature", "title"): (800, 62, 46, 2, "short_feature_text"),
        ("feature", "detail"): (500, 40, 32, 3, "short_feature_text"),
        ("cta", "text"): (700, 56, 40, 1, "body"),
    },
    "hero": {
        ("product", "product_name"): (800, 88, 56, 3, "hero_product_detail"),
        ("feature", "title"): (800, 64, 46, 3, "hero_feature_text"),
        ("feature", "sub"): (500, 42, 32, 3, "hero_feature_text"),
        ("hook", "product_name"): (800, 48, 36, 1, "hero_pill"),
    },
}


def box_width(theme, name: str) -> int:
    w = theme.resolution[0]
    side = theme.safe["side"]
    return {
        "body": w - side * 2,
        "short_card_inner": 808,               # product card (920) minus 56px padding
        "short_feature_text": 648,             # feature card minus padding/check/gap
        "short_pill": w - side * 2 - 88,       # hook product-name pill minus padding
        "hero_product_detail": 760,            # product card detail column (content-driven, see hero_scenes)
        "hero_feature_text": 528,              # feature card minus check gutter
        "hero_pill": 1400,                     # hook product-name pill
        "hero_full": w - side * 2,
    }[name]


def fit_text(theme, scene_type: str, field: str, text: str):
    """Step the font size down until the text wraps within its spec.

    Returns (font, lines, ok). When even min_size overflows, ok is False and
    the min-size layout is returned so the renderer can still draw best-effort.
    """
    weight, max_size, min_size, max_lines, box = TEXT_SPECS[theme.format][(scene_type, field)]
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


def tracked_text_width(fnt, text: str, tracking: float) -> float:
    """Width of text drawn with per-char tracking (negative tightens — the
    design's -0.02/-0.03em letter-spacing on big type)."""
    if not text:
        return 0.0
    return sum(fnt.getlength(ch) for ch in text) + tracking * (len(text) - 1)


def tracked_text(draw: ImageDraw.ImageDraw, x: float, y: float, text: str, fnt, fill,
                 tracking: float) -> float:
    """Draw text with per-char tracking (supports negative). Returns end x."""
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += fnt.getlength(ch) + tracking
    return x - tracking if text else x


def tracked_caps_width(text: str, fnt, tracking: int = 5) -> float:
    return sum(fnt.getlength(ch) + tracking for ch in text) - tracking


def tracked_caps(draw: ImageDraw.ImageDraw, x: float, y: float, text: str, fnt, fill,
                 tracking: int = 5) -> float:
    """Letter-spaced uppercase label (Pillow has no native tracking). Returns end x."""
    for ch in text.upper():
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += fnt.getlength(ch) + tracking
    return x


def tag_chip(draw: ImageDraw.ImageDraw, cx: int, cy: int, text: str, fnt, pad_x: int,
             pad_y: int, bg, fg, scale: float = 1.0) -> tuple:
    """Price-tag-shaped chip: pointed left end + punched hole. Deal and verdict
    chips share this silhouette — both are price judgments."""
    if scale <= 0:
        return (cx, cy, cx, cy)
    ascent, descent = fnt.getmetrics()
    body_w = (fnt.getlength(text) + pad_x * 2) * scale
    h = (ascent + descent + pad_y * 2) * scale
    point_w = h * 0.52
    total_w = body_w + point_w
    x0, y0 = cx - total_w / 2, cy - h / 2
    body = (x0 + point_w, y0, x0 + total_w, y0 + h)
    draw.rounded_rectangle(body, radius=int(h * 0.28), fill=bg)
    draw.polygon([(x0, cy), (x0 + point_w + h * 0.1, y0), (x0 + point_w + h * 0.1, y0 + h)],
                 fill=bg)
    hole_r = h * 0.09
    hx = x0 + point_w * 0.78
    draw.ellipse((hx - hole_r, cy - hole_r, hx + hole_r, cy + hole_r), fill=fg)
    if scale > 0.55:
        tx = x0 + point_w + (body_w - fnt.getlength(text) * scale) / 2
        draw.text((tx, cy - (ascent + descent) / 2), text, font=fnt, fill=fg)
    return (x0, y0, x0 + total_w, y0 + h)


def step_progress(draw: ImageDraw.ImageDraw, cx: int, y: int, total: int, current: int,
                  done_rgb, todo_rgb, outline_rgb):
    """Ascending step blocks — the staircase motif doubling as a 1..total counter.
    Done/current steps are solid; upcoming steps are outlined."""
    bw, bh, gap, rise = 74, 22, 12, 18
    total_w = total * bw + (total - 1) * gap
    x = cx - total_w / 2
    for i in range(total):
        yy = y - i * rise
        if i < current:
            draw.rounded_rectangle((x, yy, x + bw, yy + bh), radius=8, fill=done_rgb)
        else:
            draw.rounded_rectangle((x, yy, x + bw, yy + bh), radius=8,
                                   outline=todo_rgb, width=3)
        if i == current - 1:
            draw.rounded_rectangle((x - 4, yy - 4, x + bw + 4, yy + bh + 4), radius=10,
                                   outline=outline_rgb, width=2)
        x += bw + gap


def dashed_hline(draw: ImageDraw.ImageDraw, x0: float, x1: float, y: float, fill,
                 width: int = 3, on: int = 16, off: int = 12):
    x = x0
    while x < x1:
        draw.line((x, y, min(x + on, x1), y), fill=fill, width=width)
        x += on + off


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


def star_row(draw: ImageDraw.ImageDraw, cx: int, cy: int, rating: float, size: int, fill, empty,
             appear: float = 1.0, gap: int | None = None):
    """appear < 1 staggers a per-star pop-in (scale + rotate); 1.0 is static."""
    if gap is None:
        gap = size // 3
    total_w = 5 * size + 4 * gap
    x = cx - total_w / 2 + size / 2
    for i in range(5):
        p = clamp01(appear * 5.5 - i)
        if p > 0:
            e = ease_out_back(p)
            _star(draw, x, cy, (size / 2) * (0.2 + 0.8 * e), fill if i < rating else empty,
                  rotate_deg=(1 - e) * -25)
        x += size + gap


def _star(draw, cx, cy, r, fill, rotate_deg: float = 0.0):
    pts = []
    rot = math.radians(rotate_deg)
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5 + rot
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(angle), cy + rad * math.sin(angle)))
    draw.polygon(pts, fill=fill)


# ---------- background ----------

def gradient_bg(size: tuple, top_rgb, bottom_rgb, halo: bool = True) -> Image.Image:
    w, h = size
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        u = y / (h - 1)
        px[0, y] = tuple(round(top_rgb[i] + (bottom_rgb[i] - top_rgb[i]) * u) for i in range(3))
    bg = col.resize((w, h))
    if not halo:
        return bg
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
                   line_rgb, fill_rgb, dot_rgb, width: int = 7,
                   fill_gradient: tuple | None = None, img: Image.Image | None = None):
    """Progressive polyline reveal inside box; series_xy are normalized (0..1, 0..1 low->high).

    fill_gradient=((r,g,b,a)_top, (r,g,b,a)_bottom) with `img` fills the area
    with a vertical gradient instead of flat fill_rgb (hero chart)."""
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
        if fill_gradient is not None and img is not None:
            _gradient_polygon(img, area, fill_gradient)
        else:
            draw.polygon(area, fill=fill_rgb)
        draw.line(visible, fill=line_rgb, width=width, joint="curve")
        ex, ey = visible[-1]
        draw.ellipse((ex - 13, ey - 13, ex + 13, ey + 13), fill=dot_rgb)
        draw.ellipse((ex - 7, ey - 7, ex + 7, ey + 7), fill=(255, 255, 255))
        return ex, ey
    return None


# ---------- hero (16:9) primitives ----------
# Sprites with a blur or a distance field are precomputed once (lru_cache) and
# pasted/rotated/scaled per frame — deterministic and cheap at 30fps.

def dot_grid(img: Image.Image, spacing: int, radius: int, rgb, alpha: float):
    """Bake the design's dot lattice into a backdrop image (once, not per frame)."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    a = int(alpha * 255)
    for y in range(0, img.size[1] + spacing, spacing):
        for x in range(0, img.size[0] + spacing, spacing):
            od.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*rgb, a))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"), (0, 0))


@lru_cache(maxsize=8)
def radial_glow(w: int, h: int, rgb: tuple) -> Image.Image:
    """RGBA ellipse glow fading linearly to 0 at 70% radius (CSS closest-side
    radial-gradient ... transparent 70%). Paste via paste_glow."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = np.sqrt(((xx - (w - 1) / 2) / (w / 2)) ** 2 + ((yy - (h - 1) / 2) / (h / 2)) ** 2)
    sprite = np.zeros((h, w, 4), dtype=np.uint8)
    sprite[..., 0], sprite[..., 1], sprite[..., 2] = rgb
    sprite[..., 3] = (np.clip(1 - u / 0.7, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(sprite, "RGBA")


def paste_glow(frame: Image.Image, sprite: Image.Image, xy: tuple, strength: float = 1.0):
    """Paste an RGBA glow sprite with its alpha scaled by strength (the pulse)."""
    strength = clamp01(strength)
    if strength <= 0:
        return
    mask = sprite.getchannel("A")
    if strength < 1:
        mask = mask.point(lambda v: int(v * strength))
    frame.paste(sprite, xy, mask)


@lru_cache(maxsize=16)
def card_shadow(w: int, h: int, radius: int, sigma: int = 30, alpha: int = 115) -> Image.Image:
    """Soft drop shadow for a w x h rounded card (approximates CSS box-shadow).
    Paste at (card_x - pad, card_y - pad + offset) with pad = shadow_pad(sigma)."""
    pad = shadow_pad(sigma)
    img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((pad, pad, pad + w, pad + h), radius=radius,
                                          fill=(0, 0, 0, alpha))
    return img.filter(ImageFilter.GaussianBlur(sigma))


def shadow_pad(sigma: int = 30) -> int:
    return sigma * 3


def text_glow_sprite(text: str, weight: int, size: int, fill_rgb, glow_rgb,
                     glow_alpha: int = 140, sigma: int | None = None,
                     tracking: float = 0.0) -> tuple:
    """Crisp text over a blurred tinted halo (CSS text-shadow). Returns
    (RGBA sprite, pad): the text's origin sits at (pad, pad) in the sprite.
    Scale animations should resize this sprite, never rebuild it."""
    fnt = font(weight, size)
    ascent, descent = fnt.getmetrics()
    sigma = sigma or max(size // 8, 8)
    pad = sigma * 3
    w = int(math.ceil(tracked_text_width(fnt, text, tracking))) + pad * 2
    h = ascent + descent + pad * 2
    mask = Image.new("L", (w, h), 0)
    tracked_text(ImageDraw.Draw(mask), pad, pad, text, fnt, 255, tracking)
    glow_mask = mask.filter(ImageFilter.GaussianBlur(sigma)).point(
        lambda v: int(v * glow_alpha / 255))
    glow_layer = Image.new("RGBA", (w, h), (*glow_rgb, 0))
    glow_layer.putalpha(glow_mask)
    text_layer = Image.new("RGBA", (w, h), (*fill_rgb, 0))
    text_layer.putalpha(mask)
    return Image.alpha_composite(glow_layer, text_layer), pad


@lru_cache(maxsize=4)
def conic_sweep_sprite(diameter: int, rgb: tuple, sweep_deg: float = 120.0,
                       peak_deg: float = 55.0, peak_alpha: int = 128) -> Image.Image:
    """Angular alpha ramp inside a circle — the LiDAR scan beam. Rotate per
    frame (Image.rotate is CCW; the design spins CW, so rotate by -angle)."""
    r = diameter / 2
    yy, xx = np.mgrid[0:diameter, 0:diameter].astype(np.float32)
    dx, dy = xx - r + 0.5, yy - r + 0.5
    ang = np.degrees(np.arctan2(dy, dx)) % 360.0
    a = np.where(
        ang <= peak_deg, ang / peak_deg,
        np.clip((sweep_deg - ang) / (sweep_deg - peak_deg), 0, 1),
    ) * peak_alpha
    a *= (np.sqrt(dx ** 2 + dy ** 2) <= r).astype(np.float32)
    sprite = np.zeros((diameter, diameter, 4), dtype=np.uint8)
    sprite[..., 0], sprite[..., 1], sprite[..., 2] = rgb
    sprite[..., 3] = a.round().astype(np.uint8)
    return Image.fromarray(sprite, "RGBA")


def digit_advance(fnt) -> float:
    return max(fnt.getlength(c) for c in "0123456789")


def tabular_text(draw: ImageDraw.ImageDraw, x: float, y: float, text: str, fnt, fill,
                 align: str = "left") -> float:
    """Draw text with fixed-width digits so count-ups don't jitter
    (font-variant-numeric: tabular-nums). x is the left edge, or the right
    edge when align="right". Returns the total width."""
    adv = digit_advance(fnt)
    widths = [adv if ch.isdigit() else fnt.getlength(ch) for ch in text]
    total = sum(widths)
    cx = x - total if align == "right" else x
    for ch, cw in zip(text, widths):
        draw.text((cx + (cw - fnt.getlength(ch)) / 2, y), ch, font=fnt, fill=fill)
        cx += cw
    return total


def kinetic_fit_size(words: list[str], size: int, max_w: int, gap: int = 20,
                     min_size: int = 40) -> int | None:
    """Largest kinetic-band font size (stepping down from `size`) at which the
    words + gaps fit max_w; None when even min_size overflows. The caption
    renderer and the QA layout probe share this rule."""
    while size >= min_size:
        fnt = font(800, size)
        if sum(fnt.getlength(w) for w in words) + gap * (len(words) - 1) <= max_w:
            return size
        size -= 4
    return None


def kinetic_words(frame: Image.Image, words: list[str], hi: list[int], accent_rgb,
                  tl: float, start: float, y: int, size: int,
                  per: float = 0.14, gap: int = 20, shadow_alpha: int = 110):
    """Word-by-word pop caption band, centered (the design's Kinetic):
    easeOutBack over 0.26s, rise 26px, scale 0.7->1, highlights in accent."""
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    full = font(800, size)
    fa, fd = full.getmetrics()
    widths = [full.getlength(word) for word in words]
    total = sum(widths) + gap * (len(words) - 1)
    x = (frame.size[0] - total) / 2
    bottom = y + fa + fd
    drew = False
    for i, word in enumerate(words):
        p = clamp01((tl - (start + i * per)) / 0.26)
        if p > 0:
            e = ease_out_back(p)
            fnt = font(800, max(int(round(size * (0.7 + 0.3 * e))), 1))
            a_, d_ = fnt.getmetrics()
            ww = fnt.getlength(word)
            wx = x + (widths[i] - ww) / 2
            wy = bottom + (1 - e) * 26 - (a_ + d_)
            alpha = int(255 * clamp01(p * 1.8))
            color = accent_rgb if i in hi else (255, 255, 255)
            od.text((wx + 4, wy + 6), word, font=fnt,
                    fill=(0, 0, 0, shadow_alpha * alpha // 255))
            od.text((wx, wy), word, font=fnt, fill=(*color, alpha))
            drew = True
        x += widths[i] + gap
    if drew:
        frame.paste(Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB"), (0, 0))


def contain_fit(img: Image.Image, box_w: int, box_h: int, fraction: float = 1.0,
                zoom: float = 1.0) -> Image.Image:
    """Scale an image to fit inside box*fraction (CSS object-fit: contain)."""
    iw, ih = img.size
    scale = min(box_w * fraction / iw, box_h * fraction / ih) * zoom
    return img.resize((max(int(iw * scale), 1), max(int(ih * scale), 1)), Image.BILINEAR)


def _gradient_polygon(img: Image.Image, pts: list[tuple], gradient: tuple):
    """Fill a polygon on `img` with a vertical RGBA gradient (top, bottom)."""
    (r0, g0, b0, a0), (r1, g1, b1, a1) = gradient
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0 = int(min(xs)), int(min(ys))
    x1, y1 = int(math.ceil(max(xs))), int(math.ceil(max(ys)))
    w, h = max(x1 - x0, 1), max(y1 - y0, 1)
    u = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    rows = np.stack([r0 + (r1 - r0) * u, g0 + (g1 - g0) * u, b0 + (b1 - b0) * u], axis=-1)
    grad_rgb = np.broadcast_to(rows.round().astype(np.uint8), (h, w, 3))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon([(x - x0, y - y0) for x, y in pts], fill=255)
    alpha = (a0 + (a1 - a0) * u) * (np.asarray(mask, dtype=np.float32) / 255.0)
    img.paste(Image.fromarray(np.ascontiguousarray(grad_rgb)), (x0, y0),
              Image.fromarray(alpha.round().astype(np.uint8)))
