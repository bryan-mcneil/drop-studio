from studio.config import VO_SCENE_LEAD_S, VO_SCENE_TAIL_S
from studio.timeline import build_timeline


def _manifest_for(sb, durations):
    return {
        "backend": "none", "sample_rate": None,
        "scenes": [{"index": i, "wav": None, "duration": d} for i, d in enumerate(durations)],
    }


def test_scene_stretches_to_fit_vo(demo_storyboard):
    n = len(demo_storyboard["scenes"])
    durations = [20.0] + [0.0] * (n - 1)
    tl = build_timeline(demo_storyboard, _manifest_for(demo_storyboard, durations))
    assert tl.slots[0].duration == 20.0 + VO_SCENE_LEAD_S + VO_SCENE_TAIL_S
    # scenes without VO keep their storyboard duration
    assert tl.slots[1].duration == demo_storyboard["scenes"][1]["duration"]


def test_short_vo_keeps_min_duration(demo_storyboard):
    n = len(demo_storyboard["scenes"])
    tl = build_timeline(demo_storyboard, _manifest_for(demo_storyboard, [0.5] * n))
    assert tl.slots[0].duration == demo_storyboard["scenes"][0]["duration"]


def test_slots_are_contiguous(demo_storyboard):
    n = len(demo_storyboard["scenes"])
    tl = build_timeline(demo_storyboard, _manifest_for(demo_storyboard, [3.0] * n))
    for a, b in zip(tl.slots, tl.slots[1:]):
        assert abs(a.end - b.start) < 1e-9
    assert tl.duration == tl.slots[-1].end


def test_cta_scene_gets_no_captions(demo_storyboard):
    n = len(demo_storyboard["scenes"])
    tl = build_timeline(demo_storyboard, _manifest_for(demo_storyboard, [3.0] * n))
    cta = tl.slots[-1]
    assert cta.scene["type"] == "cta"
    assert all(c.end <= cta.start + 1e-6 for c in tl.captions)


def test_hero_timeline_uses_design_durations(hero_storyboard):
    tl = build_timeline(hero_storyboard, None)
    assert [s.duration for s in tl.slots] == [4.5, 6.0, 4.0, 4.0, 4.0, 8.0]
    assert abs(tl.duration - 30.5) < 1e-9
    assert tl.captions == []
