from studio.draw import fit_text
from studio.qa import probe_layout
from studio.theme import load_theme

THEME = load_theme("short-review-v1")


def test_demo_storyboard_has_no_violations(demo_storyboard):
    assert probe_layout(demo_storyboard, THEME) == []


def test_fit_text_steps_down_for_long_titles():
    short_fnt, _, ok = fit_text(THEME, "feature", "title", "Short title")
    assert ok and short_fnt.size == 62
    long_fnt, _, ok = fit_text(
        THEME, "feature", "title", "Accurate LiDAR mapping and no subscription"
    )
    assert ok and long_fnt.size < 62


def test_probe_flags_unfittable_text(demo_storyboard):
    scenes = [dict(s) for s in demo_storyboard["scenes"]]
    scenes[0]["text"] = "Pneumonoultramicroscopicsilicovolcanoconiosisextreme"
    violations = probe_layout({**demo_storyboard, "scenes": scenes}, THEME)
    assert violations and "hook" in violations[0]


def test_probe_flags_overwide_caption(demo_storyboard):
    scenes = [dict(s) for s in demo_storyboard["scenes"]]
    scenes[1]["vo"] = "pneumonoultramicroscopicsilicovolcanoconiosis supercalifragilistic expialidocious antidisestablishmentarianism"
    violations = probe_layout({**demo_storyboard, "scenes": scenes}, THEME)
    assert any("caption" in v for v in violations)


# ---- hero format ----

HERO_THEME = load_theme("hero-16x9-v1")


def test_hero_storyboard_has_no_violations(hero_storyboard):
    assert probe_layout(hero_storyboard, HERO_THEME) == []


def test_hero_fit_text_steps_down_for_long_titles():
    fnt, _, ok = fit_text(HERO_THEME, "feature", "title", "Short title")
    assert ok and fnt.size == 64
    long_fnt, _, ok = fit_text(
        HERO_THEME, "feature", "title", "An unreasonably wordy feature headline for a card"
    )
    assert ok and long_fnt.size < 64


def test_hero_probe_flags_overwide_cap(hero_storyboard):
    scenes = [dict(s) for s in hero_storyboard["scenes"]]
    feature = next(s for s in scenes if s["type"] == "feature")
    feature["cap"] = ["WWWWWWWWWWWWWW"] * 6
    violations = probe_layout({**hero_storyboard, "scenes": scenes}, HERO_THEME)
    assert any("kinetic caption" in v for v in violations)
