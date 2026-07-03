# CLAUDE.md — DiveSZN

DiveSZN is a static diving website: a seasonal **trip planner / calendar** for
50 world dive destinations, wrapped in a dive-hub (gear price-comparison,
reviews, dive centres, liveaboard safaris). No backend.

**Read `HANDOFF.md` first** — it has the full project map, brand, data pipeline
and backlog. Quick orientation:

- **Site:** `index.html` is the entire app (HTML + CSS + inline JS) and is what
  GitHub Pages serves. The scoring/query engine is `diving-calendar.js`.
- **Canonical data:** `diving-destinations.json` (50 destinations × 12 months).
  Edit it directly, or regenerate from `scripts/` (see below).
- **Live:** https://donlybero.github.io/Diving-site/ — auto-deploys on push to
  `main` via
  `.github/workflows/deploy-pages.yml`.

## Build / regenerate (paths are repo-relative)
```bash
python3 scripts/build_master.py      # diving-destinations.json + CSVs
python3 scripts/build_rankings.py    # diving-rankings.json
python3 scripts/build_standalone.py  # diving-site.html (offline single file)
python3 scripts/build_pages.py       # destinations/*.html + sitemap (SEO pages)
```
After editing data or `index.html`, rerun `build_standalone.py` so the
single-file build stays in sync, then commit. Pushing deploys automatically.

## Conventions
- Keep the scoring formula identical in `build_rankings.py` and
  `diving-calendar.js` (rating base + marine-life bonus ≤25 + visibility 0..18).
- Brand: name **DiveSZN** ("dive season"; wordmark `Dive<b>SZN</b>`), whale-**fluke** logo (no helmets/circles), deep
  teal + aqua, coral for prices/CTAs, monospace data readouts, serif headings.
- Reviews/Centres/Safaris are **sample data** wired like real feeds; the
  calendar/dive-site data and the Gear guide (`gear-guide.json`, indicative
  prices + real retailer links) are **real and researched**.
- Verify UI changes by serving locally (`python3 -m http.server`) — `index.html`
  fetches JSON so it needs HTTP, not `file://` (the standalone build works on
  `file://`).
