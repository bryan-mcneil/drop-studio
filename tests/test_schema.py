from studio.schema import validate


def test_demo_storyboard_is_valid(demo_storyboard):
    errors, _ = validate(demo_storyboard)
    assert errors == []


def test_missing_hook_fails(demo_storyboard):
    sb = {**demo_storyboard, "scenes": demo_storyboard["scenes"][1:]}
    errors, _ = validate(sb)
    assert any("hook" in e for e in errors)


def test_cta_must_be_last(demo_storyboard):
    scenes = list(demo_storyboard["scenes"])
    scenes.append({"type": "feature", "title": "extra", "duration": 5.0})
    errors, _ = validate({**demo_storyboard, "scenes": scenes})
    assert any("last scene" in e for e in errors)


def test_over_cap_text_fails(demo_storyboard):
    scenes = [dict(s) for s in demo_storyboard["scenes"]]
    scenes[0]["text"] = "x" * 120
    errors, _ = validate({**demo_storyboard, "scenes": scenes})
    assert any("'text' is 120 chars" in e for e in errors)


def test_verdict_without_series_fails(demo_storyboard):
    scenes = [dict(s) for s in demo_storyboard["scenes"]]
    price = next(s for s in scenes if s["type"] == "price")
    price["series"] = []
    errors, _ = validate({**demo_storyboard, "scenes": scenes})
    assert any("honesty gate" in e for e in errors)


def test_banned_phrase_warns(demo_storyboard):
    scenes = [dict(s) for s in demo_storyboard["scenes"]]
    scenes[0]["vo"] = "This is the best ever robot vacuum."
    _, warnings = validate({**demo_storyboard, "scenes": scenes})
    assert any("banned phrase" in w for w in warnings)


def test_bad_duration_fails(demo_storyboard):
    scenes = [dict(s) for s in demo_storyboard["scenes"]]
    scenes[1]["duration"] = 60.0
    errors, _ = validate({**demo_storyboard, "scenes": scenes})
    assert any("duration" in e for e in errors)


# ---- hero format ----

def test_hero_storyboard_is_valid(hero_storyboard):
    errors, warnings = validate(hero_storyboard)
    assert errors == []
    assert warnings == []


def test_hero_rejects_cta(hero_storyboard):
    scenes = list(hero_storyboard["scenes"])
    scenes.append({"type": "cta", "url": "gadgetdrop.tech", "duration": 5.0})
    errors, _ = validate({**hero_storyboard, "scenes": scenes})
    assert any("not allowed in the hero format" in e for e in errors)


def test_hero_must_end_on_price(hero_storyboard):
    scenes = [s for s in hero_storyboard["scenes"] if s["type"] != "price"]
    errors, _ = validate({**hero_storyboard, "scenes": scenes})
    assert any("last scene must be the price" in e for e in errors)
    assert any("must contain a 'price'" in e for e in errors)


def test_hero_verdict_without_series_fails(hero_storyboard):
    scenes = [dict(s) for s in hero_storyboard["scenes"]]
    next(s for s in scenes if s["type"] == "price")["series"] = []
    errors, _ = validate({**hero_storyboard, "scenes": scenes})
    assert any("honesty gate" in e for e in errors)


def test_hero_cap_hi_out_of_range_fails(hero_storyboard):
    scenes = [dict(s) for s in hero_storyboard["scenes"]]
    feature = next(s for s in scenes if s["type"] == "feature")
    feature["cap"] = ["ONE", "TWO"]
    feature["cap_hi"] = [2]
    errors, _ = validate({**hero_storyboard, "scenes": scenes})
    assert any("cap_hi" in e for e in errors)


def test_hero_bad_viz_fails(hero_storyboard):
    scenes = [dict(s) for s in hero_storyboard["scenes"]]
    next(s for s in scenes if s["type"] == "feature")["viz"] = "radar"
    errors, _ = validate({**hero_storyboard, "scenes": scenes})
    assert any("viz" in e for e in errors)


def test_unknown_template_fails(demo_storyboard):
    errors, _ = validate({**demo_storyboard, "template": "no-such-template"})
    assert any("unknown template" in e for e in errors)
