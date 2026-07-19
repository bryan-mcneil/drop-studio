from studio.storyboard import build, product_name_from_title


def test_product_name_extraction():
    assert product_name_from_title(
        "Roborock Q7 M5+ Review: The $250 Self-Empty Sweet Spot"
    ) == "Roborock Q7 M5+"
    assert product_name_from_title("Some Gadget") == "Some Gadget"


def test_scene_structure(demo_storyboard):
    types = [s["type"] for s in demo_storyboard["scenes"]]
    assert types == ["hook", "product", "feature", "feature", "feature", "price", "cta"]
    assert demo_storyboard["slug"] == "roborock-q7-m5-plus-review"


def test_creative_overrides_land(demo_storyboard, sample_creative):
    assert demo_storyboard["scenes"][0]["text"] == sample_creative["hook"]
    assert demo_storyboard["scenes"][2]["vo"] == sample_creative["feature_vo"]["1"]


def test_no_price_feed_keeps_honesty_gate(sample_post):
    sb = build(sample_post, images=[], price=None, creative=None)
    price_scene = next(s for s in sb["scenes"] if s["type"] == "price")
    assert price_scene["verdict"] is None
    assert price_scene["series"] == []
    assert "track" in price_scene["vo"].lower()


def test_post_url_built_from_slug(demo_storyboard):
    assert demo_storyboard["meta"]["post_url"].endswith("/posts/roborock-q7-m5-plus-review")
