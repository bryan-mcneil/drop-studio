"""Hero (16:9) scene drawers — the landscape review embed.

Pillow port of the Claude Design source (docs/design/hero-16x9-scenes.jsx,
landscape components): 1920x1080, silent, hard cuts, no watermark/CTA.
Design space equals render space, so every pixel value and timing below is
transliterated 1:1 from the jsx via D.tween. Two deliberate deviations from
the design, both honesty rules: the price chart plots the real feed series
(the jsx hardcodes demo vals), and the verdict chip comes from the feed's
verdict — no series, no chart, no verdict.
"""

import math

from PIL import Image, ImageDraw

from . import draw as D
from .fonts import font
from .renderer import fmt_price, _pretty_date

WHITE = (255, 255, 255)


class HeroAssets:
    """Per-render precomputed sprites (blurs and distance fields happen once)."""

    def __init__(self):
        self.glow_main = None
        self.glow_deep = None
        self.conic = None
        self.hook_price = None  # (sprite, pad)
        self.metric_cache: dict[str, tuple] = {}
        self.images: dict[int, Image.Image] = {}


def prepare(ctx):
    th = ctx.theme
    w, h = ctx.size
    bg = D.gradient_bg((w, h), th.color("bg_top"), th.color("bg_bottom"), halo=False)
    D.dot_grid(bg, 46, 2, th.color("glow"), 0.084)
    ctx.bg = bg

    a = HeroAssets()
    a.glow_main = D.radial_glow(1600, 860, th.color("glow"))
    a.glow_deep = D.radial_glow(900, 700, th.color("brand_deep"))
    a.conic = D.conic_sweep_sprite(440, th.color("brand"))
    for slot in ctx.tl.slots:
        scene = slot.scene
        if scene["type"] == "hook" and scene.get("price") is not None:
            a.hook_price = D.text_glow_sprite(fmt_price(scene["price"]), 800, 280,
                                              WHITE, th.color("glow"), glow_alpha=140,
                                              tracking=-0.03 * 280)
        if scene["type"] == "product" and scene.get("image"):
            img = ctx.assets[slot.index].image
            if img is not None:
                a.images[slot.index] = img
    ctx.hero = a


def _studio(ctx, frame, tl):
    """Shared backdrop: two drifting/pulsing radial glows over the baked
    gradient+dot-grid. Scene-local clock, so the phase resets on each cut."""
    a = ctx.hero
    drift = 14 * math.sin(tl * 0.6)
    pulse = 0.28 + 0.06 * math.sin(tl * 1.4)
    D.paste_glow(frame, a.glow_main, (160, int(-360 + drift)), pulse)
    D.paste_glow(frame, a.glow_deep, (576, int(800 + drift)), 0.34)


def _wordmark(d, th, cx, y, size=40):
    fnt = font(800, size)
    gw, dw = fnt.getlength("Gadget"), fnt.getlength("Drop")
    x = cx - (gw + dw) / 2
    d.text((x, y), "Gadget", font=fnt, fill=th.color("muted_soft"))
    d.text((x + gw, y), "Drop", font=fnt, fill=th.color("wordmark_drop"))


def _eyebrow(odr, th, w, text, top, tl, at, color=None):
    o = D.tween(tl, 0, 1, at, at + 0.4)
    if o <= 0:
        return
    y = D.tween(tl, 18, 0, at, at + 0.4, D.ease_out_back)
    fnt = font(800, 34)
    tw_ = D.tracked_caps_width(text.upper(), fnt, 10)
    _tracked_alpha(odr, (w - tw_) / 2, top + y, text, fnt,
                   color or th.color("wordmark_drop"), int(o * 255), tracking=10)


def _tracked_alpha(odr, x, y, text, fnt, rgb, alpha, tracking=10):
    for ch in text.upper():
        odr.text((x, y), ch, font=fnt, fill=(*rgb, alpha))
        x += fnt.getlength(ch) + tracking


def _paste_sprite(frame, sprite, cx, cy, scale, alpha):
    """Paste an RGBA sprite scaled about its center with a global alpha."""
    if scale <= 0 or alpha <= 0:
        return
    sw, sh = sprite.size
    if abs(scale - 1) > 1e-3:
        sprite = sprite.resize((max(int(sw * scale), 1), max(int(sh * scale), 1)),
                               Image.BILINEAR)
    mask = sprite.getchannel("A")
    if alpha < 1:
        mask = mask.point(lambda v: int(v * alpha))
    frame.paste(sprite, (int(cx - sprite.size[0] / 2), int(cy - sprite.size[1] / 2)), mask)


def _tag_chip_full_width(text, fnt, pad_x, pad_y):
    ascent, descent = fnt.getmetrics()
    h = ascent + descent + pad_y * 2
    return fnt.getlength(text) + pad_x * 2 + h * 0.52


def _card_with_shadow(frame, card, x, y, radius, alpha, scale=1.0):
    """Paste a white card + soft shadow, optionally scaled about center-top."""
    if alpha <= 0:
        return
    cw, ch = card.size
    if abs(scale - 1) > 1e-3:
        sw, sh = max(int(cw * scale), 1), max(int(ch * scale), 1)
        card = card.resize((sw, sh), Image.BILINEAR)
        x += (cw - sw) // 2
        cw, ch = sw, sh
    pad = D.shadow_pad()
    shadow = D.card_shadow(cw, ch, radius)
    smask = shadow.getchannel("A").point(lambda v: int(v * alpha * 0.9))
    frame.paste(shadow, (int(x) - pad, int(y) - pad + 40), smask)
    mask = D.rounded_mask((cw, ch), radius)
    if alpha < 1:
        mask = mask.point(lambda v: int(v * alpha))
    frame.paste(card, (int(x), int(y)), mask)


def _deal_math(scene):
    price, list_price = scene.get("price"), scene.get("list_price")
    if not price or not list_price or list_price <= price:
        return None, None
    pct = round((1 - price / list_price) * 100)
    save = max(0, round(list_price - price))
    return (pct, save) if pct >= 5 else (None, None)


# ---------------- scenes ----------------

def draw_hook(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    a = ctx.hero
    _studio(ctx, frame, tl)
    ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    odr = ImageDraw.Draw(ov)

    _wordmark(d, th, w / 2, 80)
    _eyebrow(odr, th, w, "Today's Drop", 200, tl, at=0.15)

    pct, save = _deal_math(scene)

    # center row: price slam left, was/tag/save column right (y 340..760)
    slam = D.ease_out_back(D.clamp01((tl - 0.55) / 0.55))
    breathe = 1 + 0.012 * math.sin((tl - 1.15) * 2.4) if tl > 1.15 else 1
    price_scale = (0.55 + 0.45 * slam) * breathe
    price_o = D.clamp01((tl - 0.5) / 0.3)

    sprite, pad = a.hook_price
    price_w = sprite.size[0] - pad * 2  # ink width at scale 1

    right_items = []
    if pct is not None:
        was_fnt = font(700, 64)
        was_txt = f"was {fmt_price(scene['list_price'])}"
        tag_fnt = font(800, 52)
        save_fnt = font(800, 60)
        col_w = max(was_fnt.getlength(was_txt),
                    _tag_chip_full_width(f"{pct}% OFF", tag_fnt, 34, 16),
                    save_fnt.getlength(f"Save ${save}"))
        right_items = [was_fnt, tag_fnt, save_fnt]
    else:
        col_w = 0

    gap = 72 if right_items else 0
    row_left = (w - price_w - gap - col_w) / 2
    price_cx = row_left + price_w / 2
    _paste_sprite(frame, sprite, price_cx, 550, price_scale, price_o)

    if right_items:
        was_fnt, tag_fnt, save_fnt = right_items
        x = row_left + price_w + gap
        was_h = sum(was_fnt.getmetrics())
        tag_h = sum(tag_fnt.getmetrics()) + 32
        save_h = sum(save_fnt.getmetrics())
        col_h = was_h + 26 + tag_h + 26 + save_h
        y = 550 - col_h / 2

        was_o = D.tween(tl, 0, 1, 0.7, 1.0)
        if was_o > 0:
            was_txt = f"was {fmt_price(scene['list_price'])}"
            odr.text((x, y), was_txt, font=was_fnt,
                     fill=(*th.color("muted_soft"), int(was_o * 255)))
            strike = D.tween(tl, 0, 1, 0.9, 1.4, D.ease_in_out_cubic)
            if strike > 0:
                sw = was_fnt.getlength(was_txt)
                sy = y + was_h * 0.52
                odr.rounded_rectangle((x - 6, sy - 3, x - 6 + (sw + 12) * strike, sy + 3),
                                      radius=3, fill=(*th.color("strike"), int(was_o * 255)))
        y += was_h + 26

        tag_p = D.ease_out_back(D.clamp01((tl - 1.35) / 0.4))
        if tag_p > 0:
            full_w = _tag_chip_full_width(f"{pct}% OFF", tag_fnt, 34, 16)
            D.tag_chip(odr, int(x + full_w * tag_p / 2), int(y + tag_h / 2), f"{pct}% OFF",
                       tag_fnt, 34, 16, th.color("positive"), WHITE, scale=tag_p)
        y += tag_h + 26

        save_o = D.tween(tl, 0, 1, 1.6, 2.0)
        if save_o > 0:
            save_y = D.tween(tl, 24, 0, 1.6, 2.0, D.ease_out_back)
            odr.text((x, y + save_y), f"Save ${save}", font=save_fnt,
                     fill=(*th.color("positive_bright"), int(save_o * 255)))

    # product-name pill
    chip_o = D.tween(tl, 0, 1, 2.0, 2.35)
    if chip_o > 0:
        chip_y = D.tween(tl, 38, 0, 2.0, 2.4, D.ease_out_back)
        pill_fnt, pill_lines, _ = D.fit_text(th, "hook", "product_name", scene["product_name"])
        alpha = int(chip_o * 255)
        D.pill(odr, w // 2, int(870 + chip_y), pill_lines[0], pill_fnt, 48, 20,
               (*th.color("brand_light"), alpha), (*th.color("brand_deep"), alpha))

    frame.paste(Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB"), (0, 0))
    if pct is not None:
        D.kinetic_words(frame, [f"{pct}%", "OFF", "RIGHT", "NOW"], [0],
                        th.color("brand_pale"), tl, start=2.4,
                        y=th.caption["y"], size=th.caption["size"])


def draw_product(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    _studio(ctx, frame, tl)
    ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    odr = ImageDraw.Draw(ov)
    _eyebrow(odr, th, w, "Today's Drop", 86, tl, at=0.1)
    frame.paste(Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB"), (0, 0))

    card_o = D.tween(tl, 0, 1, 0.05, 0.5)
    card_scale = D.tween(tl, 0.94, 1, 0.05, 0.6, D.ease_out_cubic)
    float_y = 6 * math.sin(tl * 1.1)
    card_w, card_h = w - 220, h - 280  # 110/176/110/104
    card = Image.new("RGB", (card_w, card_h), th.color("surface"))
    cd = ImageDraw.Draw(card)

    # column split: the detail column expands to fit its content (the design's
    # flex min-width:auto), the photo panel takes the remainder
    inner_w = card_w - 108
    name_fnt, name_lines, _ = D.fit_text(th, "product", "product_name", scene["product_name"])
    name_w = max(D.tracked_text_width(name_fnt, ln, -0.02 * name_fnt.size) for ln in name_lines)
    price_size = 168
    lp = scene.get("list_price")
    pct, _save = _deal_math(scene)
    lp_fnt = font(700, 52)
    tag_fnt = font(800, 40)
    col_w = 0
    if lp and lp > scene["price"]:
        col_w = lp_fnt.getlength(fmt_price(lp))
        if pct is not None:
            col_w = max(col_w, _tag_chip_full_width(f"{pct}% OFF", tag_fnt, 26, 16))
    def _row_w(size):
        return D.tracked_text_width(font(800, size), fmt_price(scene["price"]),
                                    -0.03 * size) + (30 + col_w if col_w else 0)
    detail_w = min(max(_row_w(price_size), name_w, 724), 950)
    while _row_w(price_size) > detail_w and price_size > 100:
        price_size -= 6
    photo_w = int(inner_w - 56 - detail_w)
    photo_h = card_h - 108
    panel = Image.new("RGB", (photo_w, photo_h), th.color("surface_alt"))
    D.paste_glow(panel, D.radial_glow(photo_w, photo_h, th.color("surface_soft")),
                 (0, int(-photo_h * 0.05)), 1.0)
    kb = D.clamp01((tl - 0.4) / (max(slot.duration, 1) - 0.4))
    photo_o = D.tween(tl, 0, 1, 0.35, 0.9)
    src = ctx.hero.images.get(slot.index)
    if src is None:
        src = D.placeholder_art(600, 600, th.color("surface_alt"), th.color("brand"))
    pic = D.contain_fit(src, photo_w, photo_h, fraction=0.9, zoom=1 + 0.08 * kb)
    px = (photo_w - pic.size[0]) // 2
    py = (photo_h - pic.size[1]) // 2
    pmask = Image.new("L", pic.size, int(photo_o * 255))
    if "A" in pic.getbands():
        pmask = pic.getchannel("A").point(lambda v: int(v * photo_o))
    panel.paste(pic.convert("RGB"), (px, py), pmask)
    card.paste(panel, (54, 54), D.rounded_mask((photo_w, photo_h), 36))

    # detail column (right), slides in
    det_o = D.tween(tl, 0, 1, 0.6, 1.0)
    det_x = 54 + photo_w + 56 + D.tween(tl, 40, 0, 0.6, 1.05, D.ease_out_cubic)
    name_h = D.text_block_height(name_lines, name_fnt, 8)
    stars_h = 66 if scene.get("rating") else 0
    price_h = sum(font(800, price_size).getmetrics())
    col_h = name_h + (34 + stars_h if stars_h else 0) + 52 + price_h
    y = (card_h - col_h) / 2

    ink = D.mix(th.color("surface"), th.color("ink"), det_o)
    for line in name_lines:
        D.tracked_text(cd, det_x, y, line, name_fnt, ink, -0.02 * name_fnt.size)
        y += sum(name_fnt.getmetrics()) + 8
    y -= 8
    if stars_h:
        stars_appear = D.clamp01((tl - 1.0) / 0.9)
        stars_total = 5 * 66 + 4 * 22
        D.star_row(cd, int(det_x + stars_total / 2), int(y + 34 + 33), scene["rating"], 66,
                   th.color("star"), th.color("star_empty"), appear=stars_appear)
        y += 34 + stars_h
    y += 52

    price_slam = D.ease_out_back(D.clamp01((tl - 1.5) / 0.5))
    price_o = D.tween(tl, 0, 1, 1.5, 1.85)
    if price_o > 0:
        size = max(int(price_size * (0.7 + 0.3 * price_slam)), 1)
        pfnt = font(800, size)
        ptxt = fmt_price(scene["price"])
        pink = D.mix(th.color("surface"), th.color("ink"), price_o)
        # origin left-bottom: anchor the baseline
        D.tracked_text(cd, det_x, y + price_h - sum(pfnt.getmetrics()), ptxt, pfnt, pink,
                       -0.03 * size)
        if col_w:
            lx = det_x + D.tracked_text_width(font(800, price_size), ptxt,
                                              -0.03 * price_size) + 30
            lp_txt = fmt_price(lp)
            lp_h = sum(lp_fnt.getmetrics())
            tag_h = sum(tag_fnt.getmetrics()) + 32
            ly = y + price_h - 14 - tag_h - 16 - lp_h
            muted = D.mix(th.color("surface"), th.color("muted_soft"), price_o)
            cd.text((lx, ly), lp_txt, font=lp_fnt, fill=muted)
            cd.line((lx - 4, ly + lp_h * 0.52, lx + lp_fnt.getlength(lp_txt) + 4, ly + lp_h * 0.52),
                    fill=muted, width=5)
            if pct is not None:
                tag_p = D.ease_out_back(D.clamp01((tl - 1.95) / 0.4))
                if tag_p > 0:
                    full_w = _tag_chip_full_width(f"{pct}% OFF", tag_fnt, 26, 16)
                    D.tag_chip(cd, int(lx + full_w * tag_p / 2),
                               int(ly + lp_h + 16 + tag_h / 2),
                               f"{pct}% OFF", tag_fnt, 26, 16,
                               th.color("positive"), WHITE, scale=tag_p)

    _card_with_shadow(frame, card, 110, 176 + float_y, 52, card_o, card_scale)


def draw_feature(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    a = ctx.hero
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
        box = (x, 108, x + pw, 126)
        done, active = s < step, s == step
        edge = accent if done or active else (*WHITE, 64)
        if done:
            odr.rounded_rectangle(box, radius=9, fill=accent, outline=accent, width=2)
        else:
            odr.rounded_rectangle(box, radius=9, fill=(*WHITE, 36), outline=edge, width=2)
            if active:
                fill_p = D.tween(tl, 0, 1, 0.1, 0.5)
                if fill_p > 0:
                    odr.rounded_rectangle((x, 108, x + pw * fill_p, 126), radius=9, fill=accent)
        x += pw + 16

    if scene.get("kicker"):
        _eyebrow(odr, th, w, scene["kicker"], 200, tl, at=0.2, color=th.color("positive_bright"))

    # hero metric (left zone: x 120..920, y 320..820)
    hero_o = D.tween(tl, 0, 1, 0.2, 0.55)
    hero_scale = 0.6 + 0.4 * D.ease_out_back(D.clamp01((tl - 0.2) / 0.5))
    if scene.get("viz") == "scan" and hero_o > 0:
        cx, cy = 520, 570
        ring_a = int(hero_o * 255)
        for inset, width_, alpha in ((0, 3, 0.35), (80, 2, 0.25), (160, 2, 0.2)):
            r = (440 - inset * 2) / 2
            odr.ellipse((cx - r, cy - r, cx + r, cy + r),
                        outline=(*accent, int(alpha * ring_a)), width=width_)
        beam = a.conic.rotate(-tl * 130, resample=Image.BILINEAR)
        mask = beam.getchannel("A")
        if hero_o < 1:
            mask = mask.point(lambda v: int(v * hero_o))
        ov.paste(beam, (cx - 220, cy - 220), mask)

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
        key = shown
        if key not in a.metric_cache:
            a.metric_cache[key] = D.text_glow_sprite(shown, 800, 230, WHITE, accent,
                                                     glow_alpha=128, tracking=-0.03 * 230)
        sprite, pad = a.metric_cache[key]
        unit = scene.get("unit") or ""
        unit_fnt = font(800, 96)
        unit_w = unit_fnt.getlength(unit) if unit else 0
        m_w = (sprite.size[0] - pad * 2) * hero_scale
        left = 520 - (m_w + unit_w) / 2
        _paste_sprite(frame, sprite, left + m_w / 2, 570, hero_scale, hero_o)
        if unit:
            ua = int(hero_o * 255)
            m_h = (sprite.size[1] - pad * 2) * hero_scale
            uy = 570 - m_h / 2 if unit == "°" else 570 + m_h / 2 - sum(unit_fnt.getmetrics())
            odr.text((left + m_w + (4 if unit == "°" else 0), uy), unit,
                     font=unit_fnt, fill=(*accent, ua))

    frame.paste(Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB"), (0, 0))

    # feature card (right)
    card_o = D.tween(tl, 0, 1, 0.45, 0.9)
    card_x = 1010 + D.tween(tl, 60, 0, 0.45, 0.95, D.ease_out_cubic)
    card_w = w - 1010 - 120
    title_fnt, title_lines, _ = D.fit_text(th, "feature", "title", scene["title"])
    title_h = D.text_block_height(title_lines, title_fnt, 6)
    sub_lines, sub_fnt, sub_h = [], None, 0
    if scene.get("sub"):
        sub_fnt, sub_lines, _ = D.fit_text(th, "feature", "sub", scene["sub"])
        sub_h = D.text_block_height(sub_lines, sub_fnt, 8)
    card_h = 108 + max(122, title_h + (20 + sub_h if sub_h else 0))
    card = Image.new("RGB", (card_w, card_h), th.color("surface"))
    cd = ImageDraw.Draw(card)
    check_p = D.ease_out_back(D.clamp01((tl - 0.7) / 0.45))
    if check_p > 0:
        D.check_mark(cd, 54 + 61, 54 + 61, int(61 * check_p), accent, WHITE,
                     progress=D.clamp01((tl - 0.85) / 0.4))
    tx = 54 + 122 + 40
    ty = 54
    for line in title_lines:
        cd.text((tx, ty), line, font=title_fnt, fill=th.color("ink"))
        ty += sum(title_fnt.getmetrics()) + 6
    if sub_lines:
        ty += 14
        for line in sub_lines:
            cd.text((tx, ty), line, font=sub_fnt, fill=th.color("muted"))
            ty += sum(sub_fnt.getmetrics()) + 8
    _card_with_shadow(frame, card, card_x, 358, 44, card_o)

    if scene.get("cap"):
        D.kinetic_words(frame, scene["cap"], scene.get("cap_hi") or [], th.color("brand"),
                        tl, start=1.2, y=th.caption["y"], size=th.caption["size"])


def draw_price(ctx, frame, d, scene, slot, tl):
    th = ctx.theme
    w, h = ctx.size
    accent = th.color("brand")
    _studio(ctx, frame, tl)
    ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    odr = ImageDraw.Draw(ov)

    # two-tone headline
    title_o = D.tween(tl, 0, 1, 0.05, 0.5)
    if title_o > 0:
        title_y = 96 + D.tween(tl, 24, 0, 0.05, 0.5, D.ease_out_cubic)
        t_fnt = font(800, 76)
        left_txt, right_txt = "Is the price good ", "right now?"
        total = t_fnt.getlength(left_txt + right_txt)
        tx = (w - total) / 2
        ta = int(title_o * 255)
        odr.text((tx, title_y), left_txt, font=t_fnt, fill=(*WHITE, ta))
        odr.text((tx + t_fnt.getlength(left_txt), title_y), right_txt, font=t_fnt,
                 fill=(*th.color("brand_pale"), ta))
    frame.paste(Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB"), (0, 0))

    card_o = D.tween(tl, 0, 1, 0.3, 0.7)
    card_scale = D.tween(tl, 0.97, 1, 0.3, 0.75, D.ease_out_cubic)
    card_w = w - 180
    asset = ctx.assets[slot.index]

    now_fnt = font(800, 96)
    header_h = sum(font(800, 30).getmetrics()) + sum(now_fnt.getmetrics())
    if asset.series_xy:
        card_h = 44 + header_h + 10 + 300 + 22 + 110 + 22 + 40 + 38
    else:
        card_h = 620
    card = Image.new("RGB", (card_w, card_h), th.color("surface"))
    cd = ImageDraw.Draw(card)

    if asset.series_xy:
        # header row
        eb_fnt = font(700, 32)
        cd.ellipse((56, 60, 76, 80), fill=accent)
        D.tracked_caps(cd, 92, 56, "90-day tracked price", eb_fnt, th.color("muted"), tracking=4)
        nl_fnt = font(800, 30)
        nl_w = D.tracked_caps_width("NOW", nl_fnt, 4)
        D.tracked_caps(cd, card_w - 56 - nl_w, 44, "NOW", nl_fnt, accent, tracking=4)
        if scene.get("current") is not None:
            now_v = D.tween(tl, 0, float(scene["current"]), 0.6, 2.9, D.ease_out_expo)
            D.tabular_text(cd, card_w - 56, 44 + sum(nl_fnt.getmetrics()) + 4,
                           f"${now_v:,.2f}", now_fnt, th.color("ink"), align="right")

        # chart
        chart = (56, 44 + header_h + 10, card_w - 56, 44 + header_h + 10 + 300)
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
                avg_fnt = font(700, 26)
                D.tracked_caps(cd, chart[2] - D.tracked_caps_width("AVG", avg_fnt, 3),
                               ay - 40, "AVG", avg_fnt, lbl_c, tracking=3)

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

        # stats row + verdict
        sy = chart[3] + 22
        sx = 56
        stats = [("90-day low", scene.get("low90"), th.color("positive"), 2.4),
                 ("Average", scene.get("avg90"), th.color("ink"), 2.6),
                 ("90-day high", scene.get("high90"), th.color("ink"), 2.8)]
        lbl_fnt = font(700, 28)
        val_fnt = font(800, 58)
        for label, value, color, s0 in stats:
            if value is None:
                continue
            D.tracked_caps(cd, sx, sy, label, lbl_fnt, th.color("muted_soft"), tracking=3)
            val = D.tween(tl, 0, float(value), s0, s0 + 0.5, D.ease_out_expo)
            D.tabular_text(cd, sx, sy + sum(lbl_fnt.getmetrics()) + 8,
                           f"${val:,.2f}", val_fnt, color)
            sx += D.tracked_caps_width(label, lbl_fnt, 3) + 140

        verdict = scene.get("verdict")
        if verdict and verdict in th.verdicts:
            v_show = D.clamp01((tl - 3.5) / 0.3)
            if v_show > 0:
                v_p = 0.7 + 0.3 * D.ease_out_back(D.clamp01((tl - 3.5) / 0.5))
                spec = th.verdicts[verdict]
                v_fnt = font(800, 44)
                full_w = _tag_chip_full_width(spec["label"], v_fnt, 34, 16)
                D.tag_chip(cd, int(card_w - 56 - full_w * v_p / 2),
                           int(sy + (sum(lbl_fnt.getmetrics()) + 8 + sum(val_fnt.getmetrics())) / 2),
                           spec["label"], v_fnt, 34, 16,
                           th.color(spec["color"]), th.color(spec.get("fg", "surface")),
                           scale=v_p)

        date_o = D.tween(tl, 0, 1, 4.2, 4.7)
        if date_o > 0 and scene.get("checked_at"):
            note = f"Price checked {_pretty_date(scene['checked_at'])}. Confirm at checkout."
            n_fnt = font(500, 30)
            cd.text(((card_w - n_fnt.getlength(note)) / 2, card_h - 38 - sum(n_fnt.getmetrics())),
                    note, font=n_fnt, fill=D.mix(th.color("surface"), th.color("muted_soft"), date_o))
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
            n_fnt = font(500, 30)
            cd.text(((card_w - n_fnt.getlength(note)) / 2, card_h - 80), note, font=n_fnt,
                    fill=th.color("muted_soft"))

    _card_with_shadow(frame, card, 90, 236, 48, card_o, card_scale)


SCENE_DRAWERS = {
    "hook": draw_hook,
    "product": draw_product,
    "feature": draw_feature,
    "price": draw_price,
}
