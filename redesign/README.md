# DiveSZN — homepage redesign concept · "Deep Water" edition

A cinematic, video-and-photo-led concept for the DiveSZN homepage. **Not merged
to `main`** and not part of the deployed site — it lives only on the
`claude/website-redesign-ai-agents-fmwv9t` branch and as a private hosted
preview.

## What it is

A single-file redesign built around the product's core promise — *know when to
dive where* — with a dark, immersive "descent through the water column" look:

- **Full-bleed underwater video hero** (`assets/video/hero-dive.webm`) with a
  live "in season now" panel that ranks destinations for the current real month.
- **Month-scrubber planner** — pick any month and destinations re-rank live by
  the real season score (rating base + visibility bonus + marine-life bonus).
- **Featured waters** — large real dive-site photography (Fiji, Ningaloo Reef,
  Protea Banks, Sharm El Sheikh) paired with the canonical 12-bar tonal season
  calendar and an on-hover water-temp / visibility read-out; the rest of the
  flagship destinations follow as compact calendar cards.
- **Marine-life encounter pulse** — scrub the year to see when each species is
  most reliably in the water.
- **Scuba gear** — real product photography across the six buyer's-guide
  categories.
- **How-we-score** trust band, a right-edge **depth gauge**, scroll reveals,
  hero parallax, and full reduced-motion + mobile support.

Brand DNA is kept (whale-fluke mark, `Dive`**`SZN`** wordmark, serif/sans/mono
type, the exact tonal season palette) and the editorial rules are respected
(scuba-only, no banned vocabulary, no homepage prices, coral reserved for buy
CTAs). This is a deliberate single dark theme — the "deep water" cut.

## Files

- **`index.html`** — the full page. References the real media in `../assets/…`,
  so **serve it** to view (relative asset paths need HTTP, not `file://`).
- **`artifact.html`** — the same page for the hosted private preview, with the
  video and all photos inlined as `data:` URIs (self-contained, CSP-safe, ~3.4 MB).
  Regenerate it from `index.html` by base64-embedding every `../assets/…`
  reference and keeping the `<body>` contents.

## View locally

```bash
python3 -m http.server        # then open http://localhost:8000/redesign/
```

Because the hero uses video and the cards use real photography, view it over
HTTP (the assets live at the repo root under `assets/`).
