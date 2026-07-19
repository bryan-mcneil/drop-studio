# Music beds

Default is the generated synth pad (`studio/music.py`) — zero cost, zero
Content ID risk. To use real tracks:

1. Download tracks you are licensed to use (YouTube Audio Library, CC0, or a
   purchased loop pack) into this directory manually.
2. Add each one to `manifest.json` with `file`, `title`, `source` (URL), and
   `license`. Tracks without a manifest entry are never picked.
3. Keep the source/receipt — that manifest is the provenance record if a
   Content ID claim ever appears.

Never auto-scrape "no copyright music" channels — that's how claims happen.
Audio files here are gitignored; the manifest is tracked.
