# CLAUDE.md — DiveSZN

DiveSZN is a static diving website: a seasonal **trip planner / calendar** for
50 world dive destinations, wrapped in a dive-hub (gear buyer's guides with
price comparison, monthly destination articles, liveaboard safaris). No backend.

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
- **Design/copy work:** load the `diveszn-design` skill first
  (`.claude/skills/diveszn-design/` — brand system, editorial rules, imagery
  standard, QA workflow); `frontend-design` (official Anthropic skill) backs
  it for general visual-design craft.
- Keep the scoring formula identical in `build_rankings.py` and
  `diving-calendar.js` (rating base + marine-life bonus ≤25 + visibility 0..18).
- Brand: name **DiveSZN** ("dive season"; wordmark `Dive<b>SZN</b>`), whale-**fluke** logo (no helmets/circles),
  **light/white theme** with teal ink + accents, coral strictly for prices/CTAs,
  monospace data readouts, serif headings. Header is a dedicated ad slot.
- Editorial rules (owner-mandated): scuba only (no freediving/snorkel copy);
  never name third parties in site copy (PADI, magazines, testers…); no
  aphorism intros; taglines never cite destination counts; specs never say
  "Both" — spell options out. Full list in HANDOFF.md §3.
- Safaris is the only remaining **sample data**; the calendar/dive-site data,
  destination photos, monthly articles and the Gear guide (`gear-guide.json`,
  indicative prices + real retailer links) are **real and researched**.
- Every finished change gets merged to `main` (auto-deploys); verify on
  desktop AND ~390px mobile viewports before merging.
- Verify UI changes by serving locally (`python3 -m http.server`) — `index.html`
  fetches JSON so it needs HTTP, not `file://` (the standalone build works on
  `file://`).
