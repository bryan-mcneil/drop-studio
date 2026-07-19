# Morning review — drop-studio Phases 1+2 (built overnight 2026-07-19)

**Watch this first:** `work/demo/final.mp4` — a 53s Short for the Roborock
Q7 M5+ (today's review), rendered end-to-end with Kokoro voiceover, burned
captions, animated 90-day sparkline + GOOD PRICE verdict, synth music bed,
−14.4 LUFS. All QA gates pass. `work/demo/probes/` has still frames if you
just want a quick look. (Product image is placeholder art — real photos
arrive with the Phase 3 feed; `--image path.jpg` already works.)

## What exists now

New repo `drop-studio` (sibling of gadget-drop), pushed to GitHub
(`bryan-mcneil/drop-studio`, private). Phases 1 and 2 of
`docs/plans/07-video-pipeline.md` are complete — see `docs/PLAN.md` phase log.
**37 tests, all green** (schema, storyboard builder, captions, timeline,
music, layout probe, golden frames, voice, slow e2e that renders a real mp4).

```
python -m studio demo --voice-backend kokoro     # what produced the demo
python -m studio video --post ..\gadget-drop\daily-drop\output.json ...
```

## Decisions I made as tech lead (flag anything you'd reverse)

1. **ffmpeg via imageio-ffmpeg wheel** — no system install, bundled static
   ffmpeg 7.1 inside the venv; `DROP_STUDIO_FFMPEG` env or PATH ffmpeg
   overrides. ffprobe isn't bundled, so probing parses `ffmpeg -i` output.
2. **Plain venv, not uv** — uv isn't installed and I avoided system
   installers overnight. pyproject is uv-compatible; `uv sync` will work if
   you install uv later.
3. **Per-scene TTS drives timing** — each scene's VO is synthesized
   separately; the scene stretches to fit its audio, captions are chunked
   inside the real span. No word-timestamp complexity needed.
4. **Auto-fit text instead of hard caps** — `fit_text()` steps the font down
   until copy fits; renderer and QA layout probe share the same table, so QA
   approves exactly what renders. (First demo run caught a 3-line feature
   title; this fixed it.)
5. **Golden tests use estimated (no-TTS) timing** — deterministic in CI, no
   model download there; Kokoro-specific tests run locally only.
6. **Music = generated synth pad by default** — zero Content ID surface.
   Licensed tracks go in `assets/music/` + manifest with mandatory
   source/license fields.
7. **Verdict honesty gate is enforced twice** — schema rejects a verdict
   without a series; the renderer shows a "we track this price daily" panel
   when stats are absent. Same rules as `PriceIntel`.
8. **Figtree TTFs are committed** (converted from the site's woff2, OFL —
   notice file included) so CI and tests never need the sibling repo.
9. **Em-dash-free on-screen labels** (matches your site-wide scrub).
10. **Committed Figtree conversion + goldens + fixtures; Kokoro weights and
    work/ output are gitignored.**

## Sample-data caveat (important)

The demo's price series/verdict is a **hand-written fixture**
(`tests/fixtures/sample_price.json`) shaped like the future
`drop:video-feed` export. Fine for a demo; a published video must use the
real export (Phase 3) — the fixture file says so in its `_note`.

## What I'd do next (Phase 3, needs your sign-off — touches gadget-drop)

- `php artisan drop:video-feed {post}` — post JSON + image paths +
  `PriceIntel` series in exactly the `sample_price.json` shape.
- `/drop-video` skill in gadget-drop for the creative fields, optional
  `/morning` step ("render today's Short?").
- Then Phase 4: `metadata.json` generator + channel setup checklist, you
  upload via Studio (~2 min/day).

## Known gaps / honest notes

- Piper backend is a thin shim (only used if a `piper` binary is on PATH);
  chain is kokoro → piper → openai → hard fail, `--voice-backend none` always
  works for captions-only.
- Kokoro pronounces "Q7 M5 Plus" cleanly; other model names may need
  phonetic spelling in the creative VO fields (that's what they're for).
- Feature-scene optional images aren't rendered yet (title + detail only) —
  deliberate scope cut; the storyboard field exists.
- **CI couldn't be pushed**: the gh CLI token lacks the `workflow` scope, so
  `.github/workflows/ci.yml` sits locally (gitignored for now). To enable:
  `gh auth refresh -h github.com -s workflow`, then remove the
  `.github/workflows/` line from `.gitignore` and commit the file. The
  workflow runs the non-voice suite with a looser golden tolerance (6.0 vs
  3.0) for Linux FreeType differences.
- The synth bed is serviceable, not memorable. A one-time $20 loop pack (or
  YouTube Audio Library picks) into `assets/music/` is the cheap upgrade.
