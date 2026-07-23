"""Build storyboard.json from a daily-drop post + optional price feed + creative overrides.

Deterministic defaults come from the post itself (title, excerpt, pros); the
optional creative JSON is where Claude's per-video writing (hook line, feature
captions, VO lines) lands — same split as the site pipeline: model writes
inputs, script assembles the artifact.

Price feed shape (Phase 3 will export this from gadget-drop as
`php artisan drop:video-feed {post}`; until then it can be hand-written):
{
  "current": 249.99, "list_price": 359.99, "checked_at": "2026-07-19",
  "verdict": "good" | "lowest" | "typical" | "elevated" | null,
  "low90": 219.99, "avg90": 261.4, "high90": 359.99,
  "series": [["2026-04-20", 359.99], ...]   # sparse change-points, carry-forward
}
Honesty gate mirrors PriceIntel: no verdict / no stats in the feed -> the video
shows a "tracking since" panel instead of a verdict chip. Never invent one.
"""

import json
import re
from pathlib import Path

from .config import DEFAULT_TEMPLATE, HERO_TEMPLATE
from .schema import validate

SITE_URL = "https://gadgetdrop.tech"


def product_name_from_title(title: str) -> str:
    """'Roborock Q7 M5+ Review: The $250 …' -> 'Roborock Q7 M5+'."""
    m = re.match(r"^(.*?)\s+Review\b", title)
    return (m.group(1) if m else title).strip()


def first_sentence(text: str, cap: int = 140) -> str:
    m = re.match(r"(.+?[.!?])\s", text + " ")
    s = m.group(1) if m else text
    return s if len(s) <= cap else s[: cap - 1].rsplit(" ", 1)[0] + "…"


def build(post: dict, images: list[str] | None = None, price: dict | None = None,
          creative: dict | None = None) -> dict:
    creative = creative or {}
    images = images or []
    title = post["title"]
    product_name = creative.get("product_name") or product_name_from_title(title)
    slug = post.get("seo", {}).get("slug") or re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    pros = (post.get("pros") or [])[:3]
    price = price or {}

    hook_text = creative.get("hook") or first_sentence(post.get("excerpt", title), cap=90)
    feature_vo = creative.get("feature_vo") or {}
    feature_detail = creative.get("feature_detail") or {}

    product_img = images[0] if images else None
    scenes: list[dict] = [
        {
            "type": "hook",
            "duration": 5.0,
            "text": hook_text,
            "sub": product_name,
            "vo": creative.get("hook_vo") or hook_text,
        },
        {
            "type": "product",
            "duration": 8.0,
            "product_name": product_name,
            "image": product_img,
            "price": price.get("current"),
            "list_price": price.get("list_price"),
            "rating": post.get("rating"),
            "vo": creative.get("product_vo") or first_sentence(post.get("excerpt", ""), cap=200),
        },
    ]
    for i, pro in enumerate(pros):
        scenes.append(
            {
                "type": "feature",
                "duration": 6.0,
                "index": i + 1,
                "count": len(pros),
                "title": creative.get("feature_titles", {}).get(str(i + 1)) or pro,
                "detail": feature_detail.get(str(i + 1)),
                "image": images[i + 1] if len(images) > i + 1 else None,
                "vo": feature_vo.get(str(i + 1)) or pro,
            }
        )
    scenes.append(
        {
            "type": "price",
            "duration": 9.0,
            "current": price.get("current"),
            "list_price": price.get("list_price"),
            "verdict": price.get("verdict"),
            "low90": price.get("low90"),
            "avg90": price.get("avg90"),
            "high90": price.get("high90"),
            "series": price.get("series") or [],
            "checked_at": price.get("checked_at"),
            "vo": creative.get("price_vo") or _default_price_vo(price, product_name),
        }
    )
    scenes.append(
        {
            "type": "cta",
            "duration": 6.0,
            "text": creative.get("cta") or "Full review + live price history",
            "url": "gadgetdrop.tech",
            "post_url": f"{SITE_URL}/posts/{slug}",
            "vo": creative.get("cta_vo")
            or "Full review and live price history at gadget drop dot tech. Link in the description.",
        }
    )

    sb = {
        "version": 1,
        "template": creative.get("template", DEFAULT_TEMPLATE),
        "slug": slug,
        "product_name": product_name,
        "voice": creative.get("voice") or {"backend": "kokoro", "voice": "am_michael", "speed": 1.0},
        "music": creative.get("music") or {"mode": "auto", "gain_db": -17.0},
        "scenes": scenes,
        "meta": {"post_url": f"{SITE_URL}/posts/{slug}", "title": title},
    }
    return sb


def _default_price_vo(price: dict, product_name: str) -> str:
    current = price.get("current")
    if current is None:
        return f"We track the {product_name}'s price every day, so you never overpay."
    verdict = price.get("verdict")
    lines = {
        "lowest": f"Right now it's {_say_price(current)}, the lowest price we've tracked.",
        "good": f"Right now it's {_say_price(current)}, below its ninety day average. That's a good price.",
        "typical": f"Right now it's {_say_price(current)}, which is a typical price. No rush.",
        "elevated": f"Right now it's {_say_price(current)}, above its usual range. We'd wait.",
    }
    return lines.get(verdict, f"Right now it's {_say_price(current)}. We track this price every day.")


def _say_price(value: float) -> str:
    if value == int(value):
        return f"{int(value)} dollars"
    dollars, cents = divmod(round(value * 100), 100)
    return f"{dollars} {cents:02d}"


def build_hero(post: dict, images: list[str] | None = None, price: dict | None = None,
               creative: dict | None = None) -> dict:
    """Storyboard for the silent 16:9 hero embed: hook / product / feature x3 /
    price, fixed design durations (4.5 / 6 / 4 / 8 = 30.5s), no VO, no music."""
    creative = creative or {}
    images = images or []
    price = price or {}
    if price.get("current") is None:
        raise ValueError("hero video needs a price feed with 'current' (the hook is a price slam)")
    title = post["title"]
    product_name = creative.get("product_name") or product_name_from_title(title)
    slug = post.get("seo", {}).get("slug") or re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    pros = (post.get("pros") or [])[:3]
    hero_creative = creative.get("hero") or {}
    feat_over = hero_creative.get("features") or {}
    feature_detail = creative.get("feature_detail") or {}

    scenes: list[dict] = [
        {
            "type": "hook",
            "duration": 4.5,
            "product_name": product_name,
            "price": price["current"],
            "list_price": price.get("list_price"),
        },
        {
            "type": "product",
            "duration": 6.0,
            "product_name": product_name,
            "image": images[0] if images else None,
            "price": price["current"],
            "list_price": price.get("list_price"),
            "rating": post.get("rating"),
        },
    ]
    for i, pro in enumerate(pros):
        over = feat_over.get(str(i + 1)) or {}
        scene = {
            "type": "feature",
            "duration": 4.0,
            "index": i + 1,
            "count": len(pros),
            "title": over.get("title") or creative.get("feature_titles", {}).get(str(i + 1)) or pro,
            "sub": over.get("sub") or feature_detail.get(str(i + 1)),
            "kicker": over.get("kicker") or "KEY FEATURE",
            "metric": over.get("metric") or _metric_from(pro),
            "unit": over.get("unit"),
            "viz": over.get("viz"),
            "cap": over.get("cap"),
            "cap_hi": over.get("cap_hi"),
        }
        scenes.append({k: v for k, v in scene.items() if v is not None})
    scenes.append(
        {
            "type": "price",
            "duration": 8.0,
            "current": price["current"],
            "list_price": price.get("list_price"),
            "verdict": price.get("verdict"),
            "low90": price.get("low90"),
            "avg90": price.get("avg90"),
            "high90": price.get("high90"),
            "series": price.get("series") or [],
            "checked_at": price.get("checked_at"),
        }
    )
    return {
        "version": 1,
        "template": hero_creative.get("template", HERO_TEMPLATE),
        "slug": slug,
        "product_name": product_name,
        "scenes": scenes,
        "meta": {"post_url": f"{SITE_URL}/posts/{slug}", "title": title},
    }


def _metric_from(pro: str) -> str | None:
    """First numeric token in a pro ('Strong 10,000Pa suction' -> '10,000')."""
    m = re.search(r"\d[\d,]*", pro)
    return m.group(0) if m else None


def build_from_files(post_path: Path, index: int, images: list[str], price_path: Path | None,
                     creative_path: Path | None, fmt: str = "short") -> dict:
    posts = json.loads(Path(post_path).read_text(encoding="utf-8"))
    if isinstance(posts, dict):
        posts = [posts]
    reviews = [p for p in posts if p.get("type", "article") == "article"]
    pool = reviews or posts
    if index >= len(pool):
        raise IndexError(f"post index {index} out of range ({len(pool)} available)")
    post = pool[index]
    price = json.loads(Path(price_path).read_text(encoding="utf-8")) if price_path else None
    creative = json.loads(Path(creative_path).read_text(encoding="utf-8")) if creative_path else None
    builder = build_hero if fmt == "hero" else build
    sb = builder(post, images=images, price=price, creative=creative)
    errors, warnings = validate(sb)
    if errors:
        raise ValueError("storyboard failed validation:\n  " + "\n  ".join(errors))
    for w in warnings:
        print(f"WARN: {w}")
    return sb
