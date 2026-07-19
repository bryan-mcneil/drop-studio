"""drop-studio — automated YouTube Shorts for gadgetdrop.tech reviews.

Claude is the orchestrator, this code is the renderer: the model writes the
creative inputs (storyboard hook/captions), deterministic Python turns them
into a finished vertical video. Mirrors the daily-drop pipeline philosophy —
the model never touches FFmpeg, the renderer never depends on a model.
"""

__version__ = "0.1.0"
