"""Hero draw primitives: easings, tween, sprites, tabular digits."""

from PIL import Image, ImageDraw

from studio.draw import (
    card_shadow,
    conic_sweep_sprite,
    digit_advance,
    ease_in_out_cubic,
    ease_out_back,
    ease_out_expo,
    font,
    radial_glow,
    tabular_text,
    tween,
)


def test_easing_endpoints():
    for ease in (ease_out_expo, ease_in_out_cubic, ease_out_back):
        assert abs(ease(0)) < 1e-9
        assert abs(ease(1) - 1) < 1e-9
        assert abs(ease(-5)) < 1e-9
        assert abs(ease(5) - 1) < 1e-9
    assert abs(ease_in_out_cubic(0.5) - 0.5) < 1e-9


def test_easing_monotonic():
    for ease in (ease_out_expo, ease_in_out_cubic):
        samples = [ease(i / 50) for i in range(51)]
        assert all(b >= a for a, b in zip(samples, samples[1:]))


def test_tween_endpoints_and_hold():
    assert tween(0.0, 10, 20, 0.5, 1.0) == 10  # before start
    assert tween(2.0, 10, 20, 0.5, 1.0) == 20  # after end
    mid = tween(0.75, 10, 20, 0.5, 1.0)
    assert 10 < mid < 20


def test_sprites_are_deterministic():
    a = radial_glow(200, 120, (99, 102, 241))
    b = radial_glow.__wrapped__(200, 120, (99, 102, 241))
    assert a.tobytes() == b.tobytes()
    c = conic_sweep_sprite(160, (79, 70, 229))
    d = conic_sweep_sprite.__wrapped__(160, (79, 70, 229))
    assert c.tobytes() == d.tobytes()
    e = card_shadow(300, 200, 40)
    f = card_shadow.__wrapped__(300, 200, 40)
    assert e.tobytes() == f.tobytes()


def test_glow_fades_to_transparent_edge():
    glow = radial_glow(200, 120, (99, 102, 241))
    alpha = glow.getchannel("A")
    assert alpha.getpixel((100, 60)) > 240  # center
    assert alpha.getpixel((0, 0)) == 0  # corner


def test_tabular_text_fixed_advance():
    fnt = font(800, 60)
    img = Image.new("RGB", (600, 100))
    d = ImageDraw.Draw(img)
    w1 = tabular_text(d, 0, 0, "$111.11", fnt, (255, 255, 255))
    w2 = tabular_text(d, 0, 0, "$888.88", fnt, (255, 255, 255))
    assert w1 == w2  # same digit count -> same width, no count-up jitter
    assert digit_advance(fnt) >= fnt.getlength("1")
