"""Short (9:16) scene drawers — the studio identity from Claude Design.

Pillow port of the portrait components in docs/design/short-scenes.jsx
(1080x1920): price-slam hook, product card, feature metric callouts, the
90-day chart card, and the violet CTA. Design space equals render space, so
pixel values and timings transliterate 1:1 via D.tween.

Only the visuals changed — content still flows from the pipeline: captions are
the real VO chunks rendered in the design's kinetic word-pop style, the chart
plots the real feed series (the jsx hardcodes demo vals), and the verdict chip
comes from the feed's verdict — no series, no chart, no verdict.
"""

import math

from PIL import Image, ImageDraw

from . import draw as D
from .fonts import font
from .hero_scenes import (  # shared helpers proven by the hero port
    _card_with_shadow,
    _deal_math,
    _eyebrow,
    _paste_sprite,
    _tag_chip_full_width,
    _wordmark,
)
from .renderer import fmt_price, _pretty_date

WHITE = (255, 255, 255)


class ShortAssets:
    """Per-render precomputed sprites (blurs and distance fields happen once)."""

    def __init__(self):
        self.glow_main = None
        self.glow_deep = None
        self.conic = None
        self.hook_price = None  # (sprite, pad)
        self.metric_cache: dict[str, tuple] = {}
        self.images: dict[int, Image.Image] = {}
        self.cta_bg = None
        self.cta_glow = None
        self.amazon_btn = None
        self.amazon_shadow = None


def prepare(ctx):
    th = ctx.theme
    w, h = ctx.size
    bg = D.gradient_bg((w, h), th.color("bg_top"), th.color("bg_bottom"), halo=False)
    D.dot_grid(bg, 46, 2, th.color("glow"), 0.084)
    ctx.bg = bg

    a = ShortAssets()
    a.glow_main = D.radial_glow(1600, 860, th.color("glow"))
    a.glow_deep = D.radial_glow(900, 700, th.color("brand_deep"))
    a.conic = D.conic_sweep_sprite(380, th.color("brand"))
    a.cta_bg = _violet_bg((w, h), th.color("cta_top"), th.color("cta_mid"),
                          th.color("cta_bottom"))
    D.dot_grid(a.cta_bg, 46, 2, th.color("cta_dot"), 0.08)
    a.cta_glow = D.radial_glow(1200, 900, th.color("cta_glow"))
    a.amazon_btn = _amazon_button(th)
    shadow = D.card_shadow(*a.amazon_btn.size, 26)
    a.amazon_shadow = Image.new("RGBA", shadow.size, (*th.color("amazon_end"), 0))
    a.amazon_shadow.putalpha(shadow.getchannel("A"))
    for slot in ctx.tl.slots:
        scene = slot.scene
        if scene["type"] == "hook" and scene.get("price") is not None:
            a.hook_price = D.text_glow_sprite(fmt_price(scene["price"]), 800, 260,
                                              WHITE, th.color("glow"), glow_alpha=140,
                                              tracking=-0.03 * 260)
        if scene["type"] == "product" and scene.get("image"):
            img = ctx.assets[slot.index].image
            if img is not None:
                a.images[slot.index] = img
    ctx.short = a


def _violet_bg(size, top, mid, bottom, mid_at=0.44):
    """The CTA's three-stop violet gradient (near-vertical stand-in for 160deg)."""
    w, h = size
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        u = y / (h - 1)
        if u < mid_at:
            a, b, t = top, mid, u / mid_at
        else:
            a, b, t = mid, bottom, (u - mid_at) / (1 - mid_at)
        px[0, y] = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return col.resize((w, h))


def _amazon_button(th):
    """'See it on Amazon →' sprite: Amazon-orange gradient, drawn arrow (the
    Figtree subset has no arrow glyphs)."""
    fnt = font(800, 54)
    text = "See it on Amazon"
    ascent, descent = fnt.getmetrics()
    text_w = fnt.getlength(text)
    w = int(text_w) + 22 + 56 + 66 * 2
    h = ascent + descent + 34 * 2
    col = Image.new("RGB", (w, 1))
    px = col.load()
    a_rgb, b_rgb = th.color("amazon_start"), th.color("amazon_end")
    for x in range(w):
        u = x / (w - 1)
        px[x, 0] = tuple(round(a_rgb[i] + (b_rgb[i] - a_rgb[i]) * u) for i in range(3))
    btn = col.resize((w, h)).convert("RGBA")
    btn.putalpha(D.rounded_mask((w, h), 26))
    bd = ImageDraw.Draw(btn)
    bd.text((66, 34), text, font=fnt, fill=th.color("ink"))
    ax, cy = 66 + text_w + 22, h / 2
    bd.line((ax, cy, ax + 44, cy), fill=th.color("ink"), width=7)
    bd.line((ax + 26, cy - 16, ax + 46, cy), fill=th.color("ink"), width=7)
    bd.line((ax + 26, cy + 16, ax + 46, cy), fill=th.color("ink"), width=7)
    return btn


def _studio(ctx, frame, tl):
    """Shared backdrop: two drifting/pulsing radial glows over the baked
    gradient+dot-grid. Scene-local clock, so the phase resets on each cut."""
    a = ctx.short
    drift = 14 * math.sin(tl * 0.6)
    pulse = 0.28 + 0.06 * math.sin(tl * 1.4)
    D.paste_glow(frame, a.glow_main, (-260, int(-360 + drift)), pulse)
    D.paste_glow(frame, a.glow_deep, (324, int(1640 + drift)), 0.34)


def _paste_sprite_top(frame, sprite_pad, cx, top, scale, alpha):
    """Paste a (sprite, pad) glow-text scaled about its top-center — the
    design's transform-origin: center top."""
    sprite, pad = sprite_pad
    if scale <= 0 or alpha <= 0:
        return
    sw, sh = sprite.size
    if abs(scale - 1) > 1e-3:
        sprite = sprite.resize((max(int(sw * scale), 1), max(int(sh * scale), 1)),
                               Image.BILINEAR)
    mask = sprite.getchannel("A")
    if alpha < 1:
        mask = mask.point(lambda v: int(v * alpha))
    frame.paste(sprite, (int(cx - sprite.size[0] / 2), int(top - pad * scale)), mask)


# ---------------- scenes ----------------

def draw_hook(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    _studio(ctx, frame, tl)
    ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    odr = ImageDraw.Draw(ov)

    _wordmark(d, th, w / 2, 118, 44)

    if scene.get("price") is not None:
        _hook_slam(ctx, frame, odr, scene, tl)
    else:
        _hook_text_fallback(ctx, odr, scene, tl)

    frame.paste(Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB"), (0, 0))


def _hook_slam(ctx, frame, odr, scene, tl):
    th = ctx.theme
    w, _h = ctx.size
    a = ctx.short
    _eyebrow(odr, th, w, "Today's Drop", 500, tl, at=0.15)
    pct, save = _deal_math(scene)

    # was $list, struck through
    if pct is not None:
        was_o = D.tween(tl, 0, 1, 0.7, 1.0)
        if was_o > 0:
            was_fnt = font(700, 60)
            was_txt = f"was {fmt_price(scene['list_price'])}"
            was_w = was_fnt.getlength(was_txt)
            wx = (w - was_w) / 2
            was_h = sum(was_fnt.getmetrics())
            odr.text((wx, 620), was_txt, font=was_fnt,
                     fill=(*th.color("muted_soft"), int(was_o * 255)))
            strike = D.tween(tl, 0, 1, 0.9, 1.4, D.ease_in_out_cubic)
            if strike > 0:
                sy = 620 + was_h * 0.52
                odr.rounded_rectangle((wx - 8, sy - 3, wx - 8 + (was_w + 16) * strike, sy + 3),
                                      radius=3, fill=(*th.color("strike"), int(was_o * 255)))

    # deal price slam (origin center top, then breathe)
    slam = D.ease_out_back(D.clamp01((tl - 0.55) / 0.55))
    breathe = 1 + 0.014 * math.sin((tl - 1.15) * 2.4) if tl > 1.15 else 1
    price_scale = (0.55 + 0.45 * slam) * breathe
    price_o = D.clamp01((tl - 0.5) / 0.3)
    _paste_sprite_top(frame, a.hook_price, w / 2, 700, price_scale, price_o)

    # discount tag + savings row
    if pct is not None:
        tag_fnt = font(800, 52)
        save_fnt = font(800, 52)
        tag_full = _tag_chip_full_width(f"{pct}% OFF", tag_fnt, 34, 16)
        tag_h = sum(tag_fnt.getmetrics()) + 32
        save_txt = f"Save ${save}"
        total = tag_full + 26 + save_fnt.getlength(save_txt)
        left = (w - total) / 2
        tag_p = D.ease_out_back(D.clamp01((tl - 1.35) / 0.4))
        if tag_p > 0:
            D.tag_chip(odr, int(left + tag_full / 2), int(1030 + tag_h / 2), f"{pct}% OFF",
                       tag_fnt, 34, 16, th.color("positive"), WHITE, scale=tag_p)
        save_o = D.tween(tl, 0, 1, 1.6, 2.0)
        if save_o > 0:
            odr.text((left + tag_full + 26, 1030 + (tag_h - sum(save_fnt.getmetrics())) / 2),
                     save_txt, font=save_fnt,
                     fill=(*th.color("positive_bright"), int(save_o * 255)))

    # product-name pill
    chip_o = D.tween(tl, 0, 1, 1.95, 2.3)
    if chip_o > 0:
        chip_y = D.tween(tl, 40, 0, 1.95, 2.35, D.ease_out_back)
        name = scene.get("sub") or scene.get("product_name") or ""
        if name:
            pill_fnt, pill_lines, _ = D.fit_text(th, "hook", "sub", name)
            alpha = int(chip_o * 255)
            pill_h = sum(pill_fnt.getmetrics()) + 40
            D.pill(odr, w // 2, int(1200 + pill_h / 2 + chip_y), pill_lines[0], pill_fnt,
                   44, 20, (*th.color("brand_light"), alpha), (*th.color("brand_deep"), alpha))


def _hook_text_fallback(ctx, odr, scene, tl):
    """No price feed -> no slam. The hook line itself carries the scene, in the
    question-variant's typography."""
    th = ctx.theme
    w, _h = ctx.size
    q_o = D.tween(tl, 0, 1, 0.2, 0.7)
    q_y = D.tween(tl, 30, 0, 0.2, 0.7, D.ease_out_back)
    fnt, lines, _ = D.fit_text(th, "hook", "text", scene["text"])
    line_h = sum(fnt.getmetrics())
    block_h = D.text_block_height(lines, fnt, 8)
    y = 560 + q_y + (420 - block_h) / 2
    ta = int(q_o * 255)
    for line in lines:
        odr.text(((w - fnt.getlength(line)) / 2, y), line, font=fnt, fill=(*WHITE, ta))
        y += line_h + 8
    chip_o = D.tween(tl, 0, 1, 1.6, 2.0)
    if chip_o > 0 and scene.get("sub"):
        chip_y = D.tween(tl, 34, 0, 1.6, 2.0, D.ease_out_back)
        pill_fnt, pill_lines, _ = D.fit_text(th, "hook", "sub", scene["sub"])
        alpha = int(chip_o * 255)
        pill_h = sum(pill_fnt.getmetrics()) + 44
        D.pill(odr, w // 2, int(1060 + pill_h / 2 + chip_y), pill_lines[0], pill_fnt,
               48, 22, (*th.color("brand_light"), alpha), (*th.color("brand_deep"), alpha))


def draw_product(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    _studio(ctx, frame, tl)
    ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    odr = ImageDraw.Draw(ov)
    _eyebrow(odr, th, w, "Today's Drop", 150, tl, at=0.1)
    frame.paste(Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB"), (0, 0))

    card_o = D.tween(tl, 0, 1, 0.05, 0.5)
    card_scale = D.tween(tl, 0.9, 1, 0.05, 0.6, D.ease_out_cubic)
    float_y = 8 * math.sin(tl * 1.1)
    card_w = w - 160
    inner_w = card_w - 112

    name_fnt, name_lines, _ = D.fit_text(th, "product", "product_name", scene["product_name"])
    name_h = D.text_block_height(name_lines, name_fnt, 8)
    stars_h = 72 if scene.get("rating") else 0

    # price row: deal price + (list, tag) column; shrink the slam if it overflows
    price_size = 150
    lp = scene.get("list_price")
    pct, _save = _deal_math(scene)
    lp_fnt = font(700, 54)
    tag_fnt = font(800, 40)
    col_w = 0
    if lp and scene.get("price") is not None and lp > scene["price"]:
        col_w = lp_fnt.getlength(fmt_price(lp))
        if pct is not None:
            col_w = max(col_w, _tag_chip_full_width(f"{pct}% OFF", tag_fnt, 26, 16))

    def _row_w(size):
        return D.tracked_text_width(font(800, size), fmt_price(scene.get("price") or 0),
                                    -0.03 * size) + (34 + col_w if col_w else 0)

    if scene.get("price") is not None:
        while _row_w(price_size) > inner_w and price_size > 96:
            price_size -= 6
        price_h = sum(font(800, price_size).getmetrics())
        row_h = max(price_h, int(sum(lp_fnt.getmetrics()) + 16 + sum(tag_fnt.getmetrics()) + 32))
    else:
        price_h = row_h = 0

    card_h = 64 + 620 + 48 + name_h + (30 + stars_h if stars_h else 0)
    if row_h:
        card_h += 44 + row_h
    card_h += 72
    card = Image.new("RGB", (card_w, card_h), th.color("surface"))
    cd = ImageDraw.Draw(card)

    # photo panel
    pw, ph = inner_w, 620
    panel = Image.new("RGB", (pw, ph), th.color("surface_alt"))
    D.paste_glow(panel, D.radial_glow(pw, ph, th.color("surface_soft")),
                 (0, int(-ph * 0.05)), 1.0)
    kb = D.clamp01((tl - 0.4) / (max(slot.duration, 1) - 0.4))
    photo_o = D.tween(tl, 0, 1, 0.35, 0.9)
    src = ctx.short.images.get(slot.index)
    if src is None:
        src = D.placeholder_art(600, 600, th.color("surface_alt"), th.color("brand"))
    pic = D.contain_fit(src, pw, ph, fraction=0.92, zoom=1 + 0.08 * kb)
    px = (pw - pic.size[0]) // 2
    py = int((ph - pic.size[1]) * 0.55)
    pmask = Image.new("L", pic.size, int(photo_o * 255))
    if "A" in pic.getbands():
        pmask = pic.getchannel("A").point(lambda v: int(v * photo_o))
    panel.paste(pic.convert("RGB"), (px, py), pmask)
    card.paste(panel, (56, 64), D.rounded_mask((pw, ph), 36))

    # name
    name_o = D.tween(tl, 0, 1, 0.6, 1.0)
    name_y = D.tween(tl, 20, 0, 0.6, 1.0, D.ease_out_back)
    y = 64 + 620 + 48 + name_y
    ink = D.mix(th.color("surface"), th.color("ink"), name_o)
    for line in name_lines:
        lw = D.tracked_text_width(name_fnt, line, -0.02 * name_fnt.size)
        D.tracked_text(cd, (card_w - lw) / 2, y, line, name_fnt, ink, -0.02 * name_fnt.size)
        y += sum(name_fnt.getmetrics()) + 8
    y -= 8

    if stars_h:
        stars_appear = D.clamp01((tl - 1.0) / 0.9)
        D.star_row(cd, card_w // 2, int(y + 30 + 36), scene["rating"], 72,
                   th.color("star"), th.color("star_empty"), appear=stars_appear, gap=12)
        y += 30 + stars_h

    # price row, centered
    if row_h:
        y += 44
        row_left = (card_w - _row_w(price_size)) / 2
        price_slam = D.ease_out_back(D.clamp01((tl - 1.5) / 0.5))
        price_o = D.tween(tl, 0, 1, 1.5, 1.85)
        if price_o > 0:
            size = max(int(price_size * (0.7 + 0.3 * price_slam)), 1)
            pfnt = font(800, size)
            ptxt = fmt_price(scene["price"])
            pink = D.mix(th.color("surface"), th.color("ink"), price_o)
            full_w = D.tracked_text_width(font(800, price_size), ptxt, -0.03 * price_size)
            small_w = D.tracked_text_width(pfnt, ptxt, -0.03 * size)
            D.tracked_text(cd, row_left + (full_w - small_w) / 2,
                           y + (row_h - sum(pfnt.getmetrics())) / 2, ptxt, pfnt, pink,
                           -0.03 * size)
            if col_w:
                lx = row_left + full_w + 34
                lp_txt = fmt_price(lp)
                lp_h = sum(lp_fnt.getmetrics())
                tag_h = sum(tag_fnt.getmetrics()) + 32
                ly = y + (row_h - (lp_h + 16 + tag_h)) / 2
                muted = D.mix(th.color("surface"), th.color("muted_soft"), price_o)
                cd.text((lx, ly), lp_txt, font=lp_fnt, fill=muted)
                cd.line((lx - 4, ly + lp_h * 0.52, lx + lp_fnt.getlength(lp_txt) + 4,
                         ly + lp_h * 0.52), fill=muted, width=5)
                if pct is not None:
                    tag_p = D.ease_out_back(D.clamp01((tl - 1.95) / 0.4))
                    if tag_p > 0:
                        full_tag = _tag_chip_full_width(f"{pct}% OFF", tag_fnt, 26, 16)
                        D.tag_chip(cd, int(lx + full_tag * tag_p / 2),
                                   int(ly + lp_h + 16 + tag_h / 2), f"{pct}% OFF",
                                   tag_fnt, 26, 16, th.color("positive"), WHITE, scale=tag_p)

    _card_with_shadow(frame, card, 80, 300 + float_y, 52, card_o, card_scale)


def draw_feature(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    a = ctx.short
    accent = th.color("brand")
    _studio(ctx, frame, tl)
    ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    odr = ImageDraw.Draw(ov)

    # progress pills
    step, count = scene.get("index", 1), scene.get("count", 3)
    pill_ws = [96 if s == step else 30 for s in range(1, count + 1)]
    total = sum(pill_ws) + 16 * (count - 1)
    x = (w - total) / 2
    for s in range(1, count + 1):
        pw = pill_ws[s - 1]
        box = (x, 210, x + pw, 228)
        done, active = s < step, s == step
        edge = accent if done or active else (*WHITE, 64)
        if done:
            odr.rounded_rectangle(box, radius=9, fill=accent, outline=accent, width=2)
        else:
            odr.rounded_rectangle(box, radius=9, fill=(*WHITE, 36), outline=edge, width=2)
            if active:
                fill_p = D.tween(tl, 0, 1, 0.1, 0.6)
                if fill_p > 0:
                    odr.rounded_rectangle((x, 210, x + pw * fill_p, 228), radius=9, fill=accent)
        x += pw + 16

    # kicker (opacity only in the portrait design)
    if scene.get("kicker"):
        kicker_o = D.tween(tl, 0, 1, 0.2, 0.6)
        if kicker_o > 0:
            k_fnt = font(800, 34)
            k_txt = scene["kicker"].upper()
            k_w = D.tracked_caps_width(k_txt, k_fnt, 10)
            kx = (w - k_w) / 2
            ka = int(kicker_o * 255)
            for ch in k_txt:
                odr.text((kx, 300), ch, font=k_fnt, fill=(*th.color("positive_bright"), ka))
                kx += k_fnt.getlength(ch) + 10

    # hero metric zone (centered, y 400..760)
    hero_o = D.tween(tl, 0, 1, 0.2, 0.55)
    hero_scale = 0.6 + 0.4 * D.ease_out_back(D.clamp01((tl - 0.2) / 0.5))
    cx, cy = w // 2, 580
    if scene.get("viz") == "scan" and hero_o > 0:
        ring_a = int(hero_o * 255)
        for inset, width_, alpha in ((0, 3, 0.35), (70, 2, 0.25), (140, 2, 0.2)):
            r = (380 - inset * 2) / 2
            odr.ellipse((cx - r, cy - r, cx + r, cy + r),
                        outline=(*accent, int(alpha * ring_a)), width=width_)
        beam = a.conic.rotate(-tl * 130, resample=Image.BILINEAR)
        mask = beam.getchannel("A")
        if hero_o < 1:
            mask = mask.point(lambda v: int(v * hero_o))
        ov.paste(beam, (cx - 190, cy - 190), mask)

    metric = scene.get("metric")
    if metric and hero_o > 0:
        digits = "".join(c for c in str(metric) if c.isdigit() or c == ".")
        target = float(digits.replace(",", "")) if digits else 0
        has_count = any(c.isdigit() for c in str(metric)) and target > 0
        if has_count:
            count_p = D.tween(tl, 0, 1, 0.25, 1.15, D.ease_out_expo)
            shown = f"{round(target * count_p):,}"
            prefix = str(metric)[: len(str(metric)) - len(str(metric).lstrip("$"))]
            shown = prefix + shown
        else:
            shown = str(metric)
        if shown not in a.metric_cache:
            a.metric_cache[shown] = D.text_glow_sprite(shown, 800, 210, WHITE, accent,
                                                       glow_alpha=128, tracking=-0.03 * 210)
        sprite, pad = a.metric_cache[shown]
        unit = scene.get("unit") or ""
        unit_fnt = font(800, 96)
        unit_w = unit_fnt.getlength(unit) if unit else 0
        m_w = (sprite.size[0] - pad * 2) * hero_scale
        left = cx - (m_w + unit_w) / 2
        _paste_sprite(frame, sprite, left + m_w / 2, cy, hero_scale, hero_o)
        if unit:
            ua = int(hero_o * 255)
            m_h = (sprite.size[1] - pad * 2) * hero_scale
            if unit == "°":
                uy = cy - m_h / 2  # superscript, per the design
            else:
                # align the unit's baseline with the metric's
                baseline = cy - m_h / 2 + font(800, 210).getmetrics()[0] * hero_scale
                uy = baseline - unit_fnt.getmetrics()[0]
            odr.text((left + m_w + (4 if unit == "°" else 0), uy), unit,
                     font=unit_fnt, fill=(*accent, ua))

    frame.paste(Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB"), (0, 0))

    # feature card
    card_o = D.tween(tl, 0, 1, 0.45, 0.9)
    card_y = 900 + D.tween(tl, 50, 0, 0.45, 0.95, D.ease_out_cubic)
    card_w = w - 160
    title_fnt, title_lines, _ = D.fit_text(th, "feature", "title", scene["title"])
    title_h = D.text_block_height(title_lines, title_fnt, 6)
    sub_lines, sub_fnt, sub_h = [], None, 0
    if scene.get("detail"):
        sub_fnt, sub_lines, _ = D.fit_text(th, "feature", "detail", scene["detail"])
        sub_h = D.text_block_height(sub_lines, sub_fnt, 4)
    content_h = title_h + (18 + sub_h if sub_h else 0)
    card_h = max(128, content_h) + 112
    card = Image.new("RGB", (card_w, card_h), th.color("surface"))
    cd = ImageDraw.Draw(card)
    check_p = D.ease_out_back(D.clamp01((tl - 0.7) / 0.45))
    if check_p > 0:
        D.check_mark(cd, 52 + 64, card_h // 2, int(64 * check_p), accent, WHITE,
                     progress=D.clamp01((tl - 0.85) / 0.4))
    tx = 52 + 128 + 40
    ty = (card_h - content_h) / 2
    for line in title_lines:
        cd.text((tx, ty), line, font=title_fnt, fill=th.color("ink"))
        ty += sum(title_fnt.getmetrics()) + 6
    if sub_lines:
        ty += 12
        for line in sub_lines:
            cd.text((tx, ty), line, font=sub_fnt, fill=th.color("muted"))
            ty += sum(sub_fnt.getmetrics()) + 4
    _card_with_shadow(frame, card, 80, card_y, 44, card_o)


def draw_price(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    accent = th.color("brand")
    _studio(ctx, frame, tl)
    ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    odr = ImageDraw.Draw(ov)

    # headline, "right now?" in the pale accent
    title_o = D.tween(tl, 0, 1, 0.05, 0.5)
    if title_o > 0:
        title_y = 210 + D.tween(tl, 26, 0, 0.05, 0.5, D.ease_out_cubic)
        headline = scene.get("headline") or "Is the price good right now?"
        words = headline.split()
        accent_from = len(words) - 2 if headline.endswith("right now?") else len(words)
        for size in (82, 74, 66, 58):
            t_fnt = font(800, size)
            lines = D.wrap_text(headline, t_fnt, w - 160)
            if len(lines) <= 2 and all(t_fnt.getlength(l) <= w - 160 for l in lines):
                break
        ta = int(title_o * 255)
        space_w = t_fnt.getlength(" ")
        wi = 0
        y = title_y
        for line in lines:
            x = (w - t_fnt.getlength(line)) / 2
            for word in line.split():
                color = th.color("brand_pale") if wi >= accent_from else WHITE
                odr.text((x, y), word, font=t_fnt, fill=(*color, ta))
                x += t_fnt.getlength(word) + space_w
                wi += 1
            y += sum(t_fnt.getmetrics()) + 6
    frame.paste(Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB"), (0, 0))

    card_o = D.tween(tl, 0, 1, 0.3, 0.7)
    card_scale = D.tween(tl, 0.96, 1, 0.3, 0.75, D.ease_out_cubic)
    card_w = w - 140
    asset = ctx.assets[slot.index]

    nl_fnt = font(800, 30)
    now_fnt = font(800, 92)
    header_h = sum(nl_fnt.getmetrics()) + 4 + sum(now_fnt.getmetrics())
    lbl_fnt = font(700, 28)
    val_fnt = font(800, 56)
    stats_h = sum(lbl_fnt.getmetrics()) + 10 + sum(val_fnt.getmetrics())
    v_fnt = font(800, 46)
    tag_h = sum(v_fnt.getmetrics()) + 32
    note_fnt = font(500, 32)
    chart_h = 322

    if asset.series_xy:
        card_h = (54 + header_h + 30 + chart_h + 44 + stats_h
                  + (46 + tag_h if scene.get("verdict") in th.verdicts else 0)
                  + 30 + sum(note_fnt.getmetrics()) + 60)
    else:
        card_h = 640
    card = Image.new("RGB", (card_w, card_h), th.color("surface"))
    cd = ImageDraw.Draw(card)

    if asset.series_xy:
        # header row: eyebrow + NOW count-up
        eb_fnt = font(700, 32)
        cd.ellipse((52, 66, 72, 86), fill=accent)
        D.tracked_caps(cd, 88, 62, "90-day tracked price", eb_fnt, th.color("muted"), tracking=4)
        nl_w = D.tracked_caps_width("NOW", nl_fnt, 4)
        D.tracked_caps(cd, card_w - 52 - nl_w, 54, "NOW", nl_fnt, accent, tracking=4)
        if scene.get("current") is not None:
            now_v = D.tween(tl, 0, float(scene["current"]), 0.6, 2.9, D.ease_out_expo)
            D.tabular_text(cd, card_w - 52, 54 + sum(nl_fnt.getmetrics()) + 4,
                           f"${now_v:,.2f}", now_fnt, th.color("ink"), align="right")

        # chart
        chart = (52, 54 + header_h + 30, card_w - 52, 54 + header_h + 30 + chart_h)
        avg = scene.get("avg90")
        if avg is not None and scene.get("low90") is not None and scene.get("high90") is not None:
            lo, hi = scene["low90"], scene["high90"]
            span = (hi - lo) or max(hi * 0.05, 1.0)
            lo_pad, span_pad = lo - span * 0.12, span * 1.24
            avg_v = (avg - lo_pad) / span_pad
            ay = chart[3] - avg_v * (chart[3] - chart[1])
            avg_o = D.tween(tl, 0, 1, 1.0, 1.5)
            if avg_o > 0:
                line_c = D.mix(th.color("surface"), th.color("soft_line"), avg_o)
                lbl_c = D.mix(th.color("surface"), th.color("muted_soft"), avg_o)
                D.dashed_hline(cd, chart[0], chart[2], ay, line_c, width=3, on=10, off=10)
                avg_lbl = font(700, 26)
                D.tracked_caps(cd, chart[2] - D.tracked_caps_width("AVG", avg_lbl, 3),
                               ay - 40, "AVG", avg_lbl, lbl_c, tracking=3)

        progress = D.anim(tl, 0.6, 2.3, D.ease_in_out_cubic)
        end = D.draw_sparkline(cd, chart, asset.series_xy, progress,
                               accent, th.color("brand_light"), accent,
                               fill_gradient=((*accent, 71), (*accent, 8)), img=card)
        if progress >= 1 and end:
            ping = (math.sin(tl * 4) + 1) / 2
            r = 16 + ping * 26
            ring = D.mix(th.color("surface"), accent, 0.6 * (1 - ping))
            cd.ellipse((end[0] - r, end[1] - r, end[0] + r, end[1] + r),
                       outline=ring, width=3)

        # stats: three centered columns
        sy = chart[3] + 44
        inner = card_w - 104
        col_w = inner / 3
        stats = [("90-day low", scene.get("low90"), th.color("positive"), 2.4),
                 ("Average", scene.get("avg90"), th.color("ink"), 2.6),
                 ("90-day high", scene.get("high90"), th.color("ink"), 2.8)]
        for i, (label, value, color, s0) in enumerate(stats):
            if value is None:
                continue
            cxi = 52 + col_w * i + col_w / 2
            lbl_w = D.tracked_caps_width(label, lbl_fnt, 3)
            D.tracked_caps(cd, cxi - lbl_w / 2, sy, label, lbl_fnt,
                           th.color("muted_soft"), tracking=3)
            val = D.tween(tl, 0, float(value), s0, s0 + 0.5, D.ease_out_expo)
            txt = f"${val:,.2f}"
            adv = D.digit_advance(val_fnt)
            t_w = sum(adv if c.isdigit() else val_fnt.getlength(c) for c in txt)
            D.tabular_text(cd, cxi - t_w / 2, sy + sum(lbl_fnt.getmetrics()) + 10,
                           txt, val_fnt, color)

        # verdict chip, centered
        verdict = scene.get("verdict")
        if verdict and verdict in th.verdicts:
            v_show = D.clamp01((tl - 3.5) / 0.3)
            if v_show > 0:
                v_p = 0.7 + 0.3 * D.ease_out_back(D.clamp01((tl - 3.5) / 0.5))
                spec = th.verdicts[verdict]
                D.tag_chip(cd, card_w // 2, int(sy + stats_h + 46 + tag_h / 2),
                           spec["label"], v_fnt, 34, 16,
                           th.color(spec["color"]), th.color(spec.get("fg", "surface")),
                           scale=v_p)

        date_o = D.tween(tl, 0, 1, 4.0, 4.5)
        if date_o > 0 and scene.get("checked_at"):
            note = f"Price checked {_pretty_date(scene['checked_at'])}. Confirm at checkout."
            cd.text(((card_w - note_fnt.getlength(note)) / 2,
                     card_h - 60 - sum(note_fnt.getmetrics())), note, font=note_fnt,
                    fill=D.mix(th.color("surface"), th.color("muted_soft"), date_o))
    else:
        # honesty fallback: no series, no chart, no verdict
        head_fnt = font(600, 44)
        head = "We track this price daily"
        cd.text(((card_w - head_fnt.getlength(head)) / 2, 110), head, font=head_fnt,
                fill=th.color("muted"))
        if scene.get("current") is not None:
            big = font(800, 150)
            txt = fmt_price(scene["current"])
            cd.text(((card_w - big.getlength(txt)) / 2, 210), txt, font=big,
                    fill=th.color("ink"))
        line2 = "Price history builds with every check"
        l2_fnt = font(500, 40)
        cd.text(((card_w - l2_fnt.getlength(line2)) / 2, 430), line2, font=l2_fnt,
                fill=th.color("muted"))
        if scene.get("checked_at"):
            note = f"Price checked {_pretty_date(scene['checked_at'])}"
            cd.text(((card_w - note_fnt.getlength(note)) / 2, card_h - 90), note,
                    font=note_fnt, fill=th.color("muted_soft"))

    _card_with_shadow(frame, card, 70, 470, 48, card_o, card_scale)


def draw_cta(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    a = ctx.short
    frame.paste(a.cta_bg, (0, 0))
    D.paste_glow(frame, a.cta_glow, (-60, int(200 + 20 * math.sin(tl * 0.7))), 0.4)
    ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    odr = ImageDraw.Draw(ov)

    # wordmark pop
    wm_o = D.tween(tl, 0, 1, 0.1, 0.5)
    if wm_o > 0:
        wm_scale = 0.7 + 0.3 * D.ease_out_back(D.clamp01((tl - 0.1) / 0.55))
        wm_fnt = font(800, max(int(124 * wm_scale), 1))
        gw, dw = wm_fnt.getlength("Gadget"), wm_fnt.getlength("Drop")
        wx = (w - gw - dw) / 2
        wy = 637 - sum(wm_fnt.getmetrics()) / 2
        wa = int(wm_o * 255)
        odr.text((wx, wy), "Gadget", font=wm_fnt, fill=(*WHITE, wa))
        odr.text((wx + gw, wy), "Drop", font=wm_fnt, fill=(*th.color("brand_pale"), wa))

    # tagline
    tag_o = D.tween(tl, 0, 1, 0.55, 0.95)
    if tag_o > 0 and scene.get("text"):
        tag_y = D.tween(tl, 28, 0, 0.55, 0.95, D.ease_out_back)
        tag_fnt, tag_lines, _ = D.fit_text(th, "cta", "text", scene["text"])
        odr.text(((w - tag_fnt.getlength(tag_lines[0])) / 2, 760 + tag_y), tag_lines[0],
                 font=tag_fnt, fill=(*WHITE, int(tag_o * 0.92 * 255)))

    # Amazon button — the one place orange lives
    btn_o = D.tween(tl, 0, 1, 1.0, 1.35)
    if btn_o > 0:
        btn_p = D.ease_out_back(D.clamp01((tl - 1.0) / 0.5))
        btn_pulse = 1 + 0.02 * math.sin((tl - 1.5) * 3) if tl > 1.5 else 1
        scale = (0.7 + 0.3 * btn_p) * btn_pulse
        bh = a.amazon_btn.size[1]
        bcy = 920 + bh / 2
        _paste_sprite(frame, a.amazon_shadow, w / 2, bcy + 22, scale, btn_o)
        _paste_sprite(frame, a.amazon_btn, w / 2, bcy, scale, btn_o)

    # site pill
    url_o = D.tween(tl, 0, 1, 1.4, 1.8)
    if url_o > 0:
        url_fnt = font(800, 48)
        pill_h = sum(url_fnt.getmetrics()) + 44
        alpha = int(url_o * 255)
        D.pill(odr, w // 2, int(1120 + pill_h / 2), scene.get("url", "gadgetdrop.tech"),
               url_fnt, 52, 22, (*WHITE, alpha), (*th.color("brand_deep"), alpha))

    # link hint + bouncing arrow
    link_o = D.tween(tl, 0, 1, 1.8, 2.2)
    if link_o > 0:
        hint = "Link in the description"
        hint_fnt = font(600, 42)
        la = int(link_o * 255)
        odr.text(((w - hint_fnt.getlength(hint)) / 2, 1290), hint, font=hint_fnt,
                 fill=(*WHITE, int(la * 0.8)))
        bounce = abs(math.sin(tl * 2.6)) * 18
        ax, ay = w / 2, 1290 + 72 + bounce
        odr.line((ax, ay, ax, ay + 44), fill=(*WHITE, la), width=7)
        odr.line((ax - 18, ay + 26, ax, ay + 46), fill=(*WHITE, la), width=7)
        odr.line((ax + 18, ay + 26, ax, ay + 46), fill=(*WHITE, la), width=7)

    frame.paste(Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB"), (0, 0))


# ---------------- chrome ----------------

def draw_chrome(ctx, frame, t):
    """Per-frame overlays after the scene drawer: watermark + kinetic captions."""
    slot = ctx.tl.slot_at(t)
    if slot.scene["type"] != "cta":
        _watermark(ctx, frame)
    _kinetic_caption(ctx, frame, t)


def _watermark(ctx, frame):
    th = ctx.theme
    if not th.watermark:
        return
    fnt = font(600, 34)
    tracking = 0.04 * 34
    tw_ = D.tracked_text_width(fnt, th.watermark, tracking)
    d = ImageDraw.Draw(frame)
    D.tracked_text(d, (ctx.size[0] - tw_) / 2, 1806, th.watermark, fnt,
                   th.color("muted"), tracking)


def _kinetic_caption(ctx, frame, t):
    """The VO captions in the design's kinetic style: real chunk text/timing,
    word-by-word pop, number-ish words in the pale accent."""
    th = ctx.theme
    for c in ctx.tl.captions:
        if c.start <= t < c.end:
            words = c.text.split()
            hi = [i for i, word in enumerate(words)
                  if any(ch.isdigit() for ch in word) or "$" in word or "%" in word]
            max_w = ctx.size[0] - th.safe["side"] * 2
            size = D.kinetic_fit_size(words, th.caption["size"], max_w) or 40
            D.kinetic_words(frame, words, hi, th.color("brand_pale"), t,
                            start=c.start, y=th.caption["y"], size=size)
            return


SCENE_DRAWERS = {
    "hook": draw_hook,
    "product": draw_product,
    "feature": draw_feature,
    "price": draw_price,
    "cta": draw_cta,
}
