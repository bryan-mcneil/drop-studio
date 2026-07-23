# drop-studio

Automated YouTube Shorts for [gadgetdrop.tech](https://gadgetdrop.tech) daily
reviews. Tier 0 (programmatic motion graphics, Pillow + FFmpeg) + Tier 1
(self-hosted Kokoro-82M voiceover). Total running cost: **$0**.

Claude orchestrates, code renders: the model writes the creative inputs
(storyboard hook, VO lines), deterministic Python turns them into a finished
1080×1920 Short. Governing plan: `docs/plans/07-video-pipeline.md` in
gadget-drop (phase log mirrored in `docs/PLAN.md` here).

## Setup (once)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install pillow numpy soundfile fonttools brotli imageio-ffmpeg kokoro-onnx pytest
.venv\Scripts\python -m studio setup --fonts        # Figtree woff2 -> ttf (needs ../gadget-drop)
.venv\Scripts\python -m studio setup --models       # Kokoro-82M weights (~340 MB, gitignored)
.venv\Scripts\python -m studio setup --check
```

(`uv sync` works too if uv is installed — pyproject is uv-compatible.)

No system installs needed: ffmpeg comes bundled via the `imageio-ffmpeg`
wheel (override with `DROP_STUDIO_FFMPEG` or a PATH ffmpeg if preferred).

## Daily use

```powershell
# Full pipeline from a daily-drop output.json:
python -m studio video --post ..\gadget-drop\daily-drop\output.json `
    --image path\to\product.jpg --price work\price.json --creative work\creative.json

# Or step by step: storyboard -> voice -> render -> qa
python -m studio storyboard --post ... --out work\2026-07-19\storyboard.json
python -m studio voice --storyboard work\2026-07-19\storyboard.json
python -m studio render --storyboard work\2026-07-19\storyboard.json
python -m studio qa --video work\2026-07-19\final.mp4 --storyboard work\2026-07-19\storyboard.json

# Demo on committed fixtures (Roborock sample):
python -m studio demo --voice-backend kokoro    # or `none` for captions-only
```

### Hero (16:9) review embed

Silent 1920x1080 companion video for the top of each review page — same
data, no VO, no music, hard cuts, 30.5s. Design source:
`docs/design/hero-16x9-scenes.jsx` (Claude Design export).

```powershell
python -m studio hero --post ..\gadget-drop\daily-drop\output.json `
    --image path\to\product.jpg --price work\price.json --creative work\creative.json
python -m studio hero --demo                    # fixtures -> work\demo\hero\final.mp4
```

Output: `work/<date>/hero/final.mp4` + `thumb.jpg` + `qa_report.json`. The
hero QA gates require the *absence* of an audio stream; the price honesty
gate applies unchanged (no series, no chart, no verdict).

Output per run: `final.mp4` (H.264/AAC, −14 LUFS, ready for Shorts),
`thumb.jpg`, `qa_report.json`, `storyboard.json`, `vo/` wavs, `mix.wav`.

## Pipeline

```
output.json ─► storyboard.json ─► vo/*.wav ─► frames ─► final.mp4 ─► QA gates
              (deterministic       (Kokoro,   (Pillow    (ffmpeg     (duration, res,
               defaults + Claude's  per        stream     rawvideo    fps, size, LUFS,
               creative overrides)  scene)     -> stdin)  + loudnorm) text layout)
```

- Scene durations adapt to real VO length; captions are timed per scene chunk.
- Price scene renders the real 90-day series with PriceIntel's honesty gates:
  **no verdict chip without a series**; a missing feed shows the tracking
  panel instead. Never hand-write a price feed for a published video —
  Phase 3 exports it from gadget-drop (`drop:video-feed`).
- Music: generated synth pad by default; licensed tracks via
  `assets/music/manifest.json` (provenance required).

## Tests

```powershell
.venv\Scripts\python -m pytest              # full suite
.venv\Scripts\python -m pytest -m "not slow"
python -m studio golden --update            # after a deliberate design change
```

Golden frames are rendered from committed fixtures with estimated VO timing —
no TTS, network, or clock in the test path.
