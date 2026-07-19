# drop-studio plan + phase log

The governing plan lives in gadget-drop:
**`docs/plans/07-video-pipeline.md`** (integration contract is defined on the
content-source side). This file tracks execution.

## Phase log

- [x] **Phase 1 — Renderer + storyboard schema** (2026-07-19, overnight build)
  Storyboard schema v1 + validation (`schema.py`), deterministic builder from
  daily-drop `output.json` (`storyboard.py`), Pillow renderer with hook /
  product / feature×3 / price / cta scenes, Ken Burns, animated sparkline with
  verdict chip honesty gate, auto-fit text (`draw.fit_text`, shared with QA),
  golden-frame tests, QA gates (duration, resolution, fps, size, LUFS, text
  layout). `python -m studio demo` renders end-to-end.
- [x] **Phase 2 — Voice + music** (2026-07-19, same session)
  `voice.py` kokoro → piper → openai → none chain, per-scene synthesis driving
  scene duration + caption timing; synth music bed (deterministic per slug) +
  licensed-track manifest; numpy VO ducking; two-pass EBU R128 loudnorm to
  −14 LUFS in the mux. Kokoro-82M runs locally (models gitignored,
  `setup --models`).
- [ ] **Phase 3 — gadget-drop integration** (next)
  `php artisan drop:video-feed {post}` export (post + image paths + PriceIntel
  series in the `sample_price.json` shape), `/drop-video` skill for creative
  fields, optional `/morning` hook.
- [ ] **Phase 4 — Semi-auto publish**
  `metadata.json` generator (title, description with review URL + disclosures,
  tags, `#shorts`), channel setup checklist, Bryan uploads via Studio.
- [ ] **Phase 5 — API upload** (private-visibility first, compliance audit)
- [ ] **Phase 6 — Iterate on data** (30-Shorts gate)

## Session working agreement

Same as gadget-drop's plans: one phase per session, tests are part of the
phase, review before commit. Renders run on the PC (or later a VPS) — never on
Hostinger.
