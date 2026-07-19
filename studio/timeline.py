"""Merge storyboard + voice manifest into the final render timeline.

Scene durations adapt to real VO length: duration = max(storyboard duration,
lead + vo + tail). The timeline is the single source of truth for the renderer,
the audio mix, and the captions — nothing else re-derives timing.
"""

from dataclasses import dataclass, field

from .captions import Caption, scene_captions
from .config import VO_SCENE_LEAD_S, VO_SCENE_TAIL_S


@dataclass
class SceneSlot:
    index: int
    scene: dict
    start: float
    duration: float
    vo_wav: str | None
    vo_start: float  # offset inside scene
    vo_duration: float

    @property
    def end(self) -> float:
        return self.start + self.duration


@dataclass
class Timeline:
    slots: list[SceneSlot]
    captions: list[Caption] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.slots[-1].end if self.slots else 0.0

    def slot_at(self, t: float) -> SceneSlot:
        for slot in self.slots:
            if t < slot.end:
                return slot
        return self.slots[-1]


def build_timeline(storyboard: dict, vo_manifest: dict | None, max_words: int = 4) -> Timeline:
    vo_scenes = {s["index"]: s for s in (vo_manifest or {}).get("scenes", [])}
    slots: list[SceneSlot] = []
    captions: list[Caption] = []
    cursor = 0.0
    for i, scene in enumerate(storyboard["scenes"]):
        vo = vo_scenes.get(i, {})
        vo_dur = float(vo.get("duration") or 0.0)
        base = float(scene.get("duration", 5.0))
        duration = max(base, VO_SCENE_LEAD_S + vo_dur + VO_SCENE_TAIL_S) if vo_dur else base
        slot = SceneSlot(
            index=i, scene=scene, start=cursor, duration=duration,
            vo_wav=vo.get("wav"), vo_start=VO_SCENE_LEAD_S, vo_duration=vo_dur,
        )
        slots.append(slot)
        # No captions on the CTA scene — it IS on-screen text already.
        if scene.get("vo") and vo_dur and scene.get("type") != "cta":
            captions.extend(
                scene_captions(scene["vo"], slot.start, slot.vo_start, vo_dur, max_words=max_words)
            )
        cursor += duration
    return Timeline(slots=slots, captions=captions)
