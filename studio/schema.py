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

# Character caps: these are on-screen text, one bad length breaks layout.
TEXT_CAPS = {
    ("hook", "text"): 90,
    ("product", "product_name"): 60,
    ("feature", "title"): 70,
    ("feature", "detail"): 160,
    ("cta", "text"): 60,
}

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

    types = [s.get("type") for s in scenes]
    for expected in ("hook", "cta"):
        if expected not in types:
            errors.append(f"storyboard must contain a '{expected}' scene")
    if types and types[0] != "hook":
        errors.append("first scene must be the hook")
    if types and types[-1] != "cta":
        errors.append("last scene must be the cta")
    if types.count("feature") > 4:
        errors.append("more than 4 feature scenes")

    total_duration = 0.0
    total_vo = 0
    for i, scene in enumerate(scenes):
        label = f"scene[{i}]({scene.get('type', '?')})"
        stype = scene.get("type")
        if stype not in SCENE_TYPES:
            errors.append(f"{label}: unknown type {stype!r}")
            continue
        for field in REQUIRED_FIELDS[stype]:
            if scene.get(field) in (None, ""):
                errors.append(f"{label}: missing required field '{field}'")
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
    if not (TOTAL_RANGE[0] <= total_duration <= TOTAL_RANGE[1]):
        warnings.append(
            f"total storyboard duration {total_duration:.1f}s outside {TOTAL_RANGE}"
            " (VO timing may still pull it in range)"
        )
    return errors, warnings
