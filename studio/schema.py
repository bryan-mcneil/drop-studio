"""Storyboard validation — the drop-studio analog of daily-drop-build.php.

Hand-rolled on purpose (clear error strings, no jsonschema dep). `validate()`
returns (errors, warnings); the CLI exits non-zero on any error. The renderer
trusts a validated storyboard completely.
"""

STORYBOARD_VERSION = 1

SCENE_TYPES = ("hook", "product", "feature", "price", "cta")

# Per-scene required fields beyond "type" (duration is defaulted upstream).
REQUIRED_FIELDS = {
    "hook": ("text",),
    "product": ("product_name", "price"),
    "feature": ("title",),
    "price": ("current",),
    "cta": ("url",),
}

HERO_REQUIRED_FIELDS = {
    "hook": ("product_name", "price"),
    "product": ("product_name", "price"),
    "feature": ("title",),
    "price": ("current",),
}

# Structural rules per template format. The template's theme.json declares its
# format; the Short's rules are unchanged, the hero has no cta and ends on the
# price scene.
FORMAT_RULES = {
    "short": {
        "allowed": SCENE_TYPES,
        "required": ("hook", "cta"),
        "first": "hook",
        "last": "cta",
        "max_features": 4,
        "required_fields": REQUIRED_FIELDS,
    },
    "hero": {
        "allowed": ("hook", "product", "feature", "price"),
        "required": ("hook", "product", "price"),
        "first": "hook",
        "last": "price",
        "max_features": 3,
        "required_fields": HERO_REQUIRED_FIELDS,
    },
}

# Character caps: these are on-screen text, one bad length breaks layout.
TEXT_CAPS = {
    ("hook", "text"): 90,
    ("product", "product_name"): 60,
    ("feature", "title"): 70,
    ("feature", "detail"): 160,
    ("feature", "sub"): 140,
    ("cta", "text"): 60,
}

# Feature-scene extras, both formats (metric callout, scan viz, kicker; the
# hero adds kinetic caption words — the Short's caption band is the VO).
HERO_FEATURE_CAPS = {"kicker": 28, "metric": 12, "unit": 4}
HERO_VIZ_VALUES = ("scan", None)
HERO_CAP_MAX_WORDS = 6
HERO_CAP_MAX_WORD_CHARS = 14

VO_CHARS_PER_SEC = 16  # ~ Kokoro at speed 1.0; used only for sanity caps
MAX_SCENE_VO_CHARS = 340  # ~ 21s of speech; nothing in a Short should be longer
MAX_TOTAL_VO_CHARS = 1600  # ~ 100s absolute ceiling

BANNED_VO_PHRASES = (
    "best ever", "world's best", "#1", "guaranteed", "insane", "unbelievable",
    "life-changing", "game changer", "game-changing", "revolutionary",
)

DURATION_RANGE = (2.0, 25.0)  # per scene, seconds
TOTAL_RANGE = (30.0, 120.0)  # hard bounds; the QA gate enforces 45–90 on the file

VALID_VERDICTS = ("lowest", "good", "typical", "elevated", None)


def validate(sb: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if sb.get("version") != STORYBOARD_VERSION:
        errors.append(f"version must be {STORYBOARD_VERSION}, got {sb.get('version')!r}")
    for key in ("template", "slug", "scenes"):
        if not sb.get(key):
            errors.append(f"missing required top-level field '{key}'")
    scenes = sb.get("scenes") or []
    if errors:
        return errors, warnings

    from .theme import load_theme

    try:
        fmt = load_theme(sb["template"]).format
    except FileNotFoundError:
        errors.append(f"unknown template {sb['template']!r}")
        return errors, warnings
    rules = FORMAT_RULES.get(fmt)
    if rules is None:
        errors.append(f"template {sb['template']!r} declares unknown format {fmt!r}")
        return errors, warnings

    types = [s.get("type") for s in scenes]
    for expected in rules["required"]:
        if expected not in types:
            errors.append(f"storyboard must contain a '{expected}' scene")
    if types and types[0] != rules["first"]:
        errors.append(f"first scene must be the {rules['first']}")
    if types and types[-1] != rules["last"]:
        errors.append(f"last scene must be the {rules['last']}")
    if types.count("feature") > rules["max_features"]:
        errors.append(f"more than {rules['max_features']} feature scenes")
    if fmt == "hero" and 0 < types.count("feature") != 3:
        warnings.append("hero storyboards look best with exactly 3 feature scenes")

    total_duration = 0.0
    total_vo = 0
    for i, scene in enumerate(scenes):
        label = f"scene[{i}]({scene.get('type', '?')})"
        stype = scene.get("type")
        if stype not in SCENE_TYPES:
            errors.append(f"{label}: unknown type {stype!r}")
            continue
        if stype not in rules["allowed"]:
            errors.append(f"{label}: scene type {stype!r} not allowed in the {fmt} format")
            continue
        for field in rules["required_fields"][stype]:
            if scene.get(field) in (None, ""):
                errors.append(f"{label}: missing required field '{field}'")
        if stype == "feature":
            _validate_feature_extras(scene, label, errors)
        dur = scene.get("duration", 0)
        if not isinstance(dur, (int, float)) or not (DURATION_RANGE[0] <= dur <= DURATION_RANGE[1]):
            errors.append(f"{label}: duration {dur!r} outside {DURATION_RANGE}")
        else:
            total_duration += dur

        for (cap_type, field), cap in TEXT_CAPS.items():
            if stype == cap_type and scene.get(field) and len(scene[field]) > cap:
                errors.append(f"{label}: '{field}' is {len(scene[field])} chars (cap {cap})")

        vo = scene.get("vo") or ""
        total_vo += len(vo)
        if len(vo) > MAX_SCENE_VO_CHARS:
            errors.append(f"{label}: vo is {len(vo)} chars (cap {MAX_SCENE_VO_CHARS})")
        low_vo = vo.lower()
        for phrase in BANNED_VO_PHRASES:
            if phrase in low_vo:
                warnings.append(f"{label}: vo contains banned phrase '{phrase}'")
        if stype == "price":
            verdict = scene.get("verdict")
            if verdict not in VALID_VERDICTS:
                errors.append(f"{label}: verdict {verdict!r} not in {VALID_VERDICTS}")
            if verdict and not scene.get("series"):
                errors.append(f"{label}: a verdict without a price series violates the honesty gate")

    if total_vo > MAX_TOTAL_VO_CHARS:
        errors.append(f"total vo is {total_vo} chars (cap {MAX_TOTAL_VO_CHARS})")
    if fmt == "hero" and total_vo:
        warnings.append("hero storyboards are voiceless; vo fields are ignored")
    if not (TOTAL_RANGE[0] <= total_duration <= TOTAL_RANGE[1]):
        warnings.append(
            f"total storyboard duration {total_duration:.1f}s outside {TOTAL_RANGE}"
            " (VO timing may still pull it in range)"
        )
    return errors, warnings


def _validate_feature_extras(scene: dict, label: str, errors: list[str]) -> None:
    for field, cap in HERO_FEATURE_CAPS.items():
        value = scene.get(field)
        if value and len(str(value)) > cap:
            errors.append(f"{label}: '{field}' is {len(str(value))} chars (cap {cap})")
    if scene.get("viz") not in HERO_VIZ_VALUES:
        errors.append(f"{label}: viz {scene.get('viz')!r} not in {HERO_VIZ_VALUES}")
    cap_words = scene.get("cap")
    if cap_words is not None:
        if not isinstance(cap_words, list) or not all(isinstance(w, str) for w in cap_words):
            errors.append(f"{label}: 'cap' must be a list of words")
        else:
            if len(cap_words) > HERO_CAP_MAX_WORDS:
                errors.append(f"{label}: 'cap' has {len(cap_words)} words (cap {HERO_CAP_MAX_WORDS})")
            for w in cap_words:
                if len(w) > HERO_CAP_MAX_WORD_CHARS:
                    errors.append(f"{label}: cap word '{w}' over {HERO_CAP_MAX_WORD_CHARS} chars")
            hi = scene.get("cap_hi") or []
            if not all(isinstance(i, int) and 0 <= i < len(cap_words) for i in hi):
                errors.append(f"{label}: 'cap_hi' indices out of range for cap of {len(cap_words)}")
