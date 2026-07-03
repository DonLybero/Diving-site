# DiveSZN — project handoff

A diving website: a **seasonal trip planner / calendar** for 50 world dive
destinations, wrapped in a **dive-hub** (gear price-comparison, reviews, dive
centres, liveaboard safaris). Static site, no backend, deployable anywhere.

- **Live site:** https://donlybero.github.io/Diving-site/
- **Repo:** `DonLybero/Diving-site`
- **Working branch:** `main` (trunk since 2026-07; the old claude/diving-destinations-research-73uc5i branch is retired)

## Brand
- **Name:** DiveSZN — "dive season" in sports-slang spelling ("SZN"); named for the
  site's USP (WHEN to dive WHERE). Wordmark renders as `Dive<b>SZN</b>`. Renamed from
  "Scubanaut" 2026-07 after a multi-lane naming + clearance study — see
  `docs/name-change-diveszn-2026-07.md`. **Logo:** a whale **fluke** (bare tail, no circle/text) — inline SVG in `index.html` header + the favicon (data-URI).
- **Design language:** deep-ocean "instrument panel" — luminous **aqua** (`#2fe0d6`) on deep **teal** (`#04202b`), **coral** (`#ff7a59`) reserved for prices/scores/CTAs. **Monospace** "dive-computer" readout chips for water temp / visibility / current; **editorial serif** (Georgia) for headings.

## What's real vs. sample data
- **REAL, researched:** the 50-destination seasonal dataset — per-month water
  temperature, marine life, conditions, visibility, season rating, plus
  current strength and coordinates. Powers the Calendar, Best-period, Plan,
  Map, Search and Dive Sites sections.
- **REAL, researched (2026-07):** the Gear guide (`gear-guide.json`) — top 10
  per category (masks, fins, regulators, BCDs, computers, wetsuits) compiled
  from the 20 biggest diving YouTube channels + ScubaLab/DIVE/DiveIn tests,
  each with 3 cheapest online stores (indicative prices, real links; image
  URLs best-effort with icon fallback).
- **REAL, computed live:** the Destinations tab — 12 "Top Destinations in
  <Month>" articles ranked live by the scoring engine over the seasonal
  dataset, with editorial ledes. (The old sample Reviews and Dive Centres
  sections were removed 2026-07.)

## File map
| File | What it is |
|------|-----------|
| `index.html` | The whole site (HTML + CSS + inline app JS). Loads the data/engine over HTTP. **This is what GitHub Pages serves.** |
| `diving-calendar.js` | Scoring + query engine: `rankPeriod`, `rankWindow`, `getDestination`, `searchDestinations`, `destinationSeasonSummary`. Browser + Node. |
| `diving-destinations.json` | **Canonical data** — 50 destinations, each with metadata + 12 monthly entries (rating, temp, visibility_m, marine_life, conditions) + current_strength + coordinates. |
| `diving-rankings.json` | Precomputed period rankings (optional; site computes live too). |
| `diving-site.html` | Single-file build (everything inlined) — opens offline by double-click. Regenerate with `scripts/build_standalone.py`. |
| `diving-calendar-24-periods.csv`, `diving-calendar-grid.csv` | Spreadsheet exports of the data. |
| `vendor/` | Self-hosted Leaflet + `world-land.geojson` (offline vector map basemap). |
| `index.html` Map tab | Uses the offline vector basemap by default. |
| `map-A-osm-tiles.html`, `map-B-vector-offline.html` | Standalone map-style comparison demos. |
| `scripts/` | Data generators (see below). |
| `.github/workflows/deploy-pages.yml` | Auto-deploys the repo root to GitHub Pages on every push to the working branch. |

## Data pipeline (how to regenerate)
The canonical file is `diving-destinations.json`. You can edit it directly, OR
regenerate it from source with the scripts (paths are repo-relative):

```bash
python3 scripts/build_master.py      # -> diving-destinations.json + the 2 CSVs
python3 scripts/build_rankings.py    # -> diving-rankings.json
python3 scripts/build_standalone.py  # -> diving-site.html (inlined single file)
```

Source inputs:
- `scripts/build_csv.py` + `scripts/meta11.py` — the original 11 destinations (month-by-month tuples + metadata).
- `scripts/data/*.json` — the other 39 destinations (Caribbean / Europe / Pacific / SE-Asia / Australia research fragments).
- `scripts/data/dive_sites.json` — 417 recognised named dive sites across all 50 destinations (researched 2026-07, PADI Travel first, cross-checked against SSI MyDiveGuide / Scuba Diving Magazine / operator listings). Merged into each destination as `dive_sites` by build_master; rendered in the profile, the SEO pages and searchable in the Search tab.
- `scripts/build_master.py` merges all of them, derives `visibility_m` (parsed from conditions text), `current_strength` (Low/Medium/Strong), and coordinates, then writes the JSON + CSVs.

**After changing data, rerun the three scripts**, then commit. The push
auto-deploys.

## Scoring (kept identical in `build_rankings.py` and `diving-calendar.js`)
`score = rating_base (Peak100/Good72/Shoulder48/Low22; Closed excluded)
       + min(marine-life keyword bonus, 25)
       + visibility_bonus (0..18, scaled from visibility_m: <=5m→0, >=35m→18)`

## Deploy
GitHub Pages is set to **Source = GitHub Actions**. The workflow publishes the
repo root; `index.html` is the landing page. Every push to `main` redeploys
within ~1–2 min.

## Done so far (highlights)
- 50 destinations fact-checked by research agents (2026-07); current strength
  hand-verified per destination (`scripts/data/verification.json`, applied by
  build_master); Chagos marked access-suspended.
- Destination photos baked via the fetch-images workflow (Wikimedia; add a
  PEXELS_API_KEY repo secret + rerun with --force for better quality).
- SVG icon system (no emoji); Dive Sites + Map merged into the Dive Planner
  (opens on top-3 for the current period; See more 3→10→+5).
- 50 static SEO pages under `destinations/` + sitemap.xml + robots.txt
  (`scripts/build_pages.py`).
- Dive Centres is a factual directory (no invented ratings); gear prices
  visibly labelled as samples.
- Recognised named dive sites for all 50 destinations (2026-07): 417 sites in
  `scripts/data/dive_sites.json`, shown in destination profiles + SEO pages
  and matched by search (e.g. searching "Blue Corner" finds Palau).

## Backlog
- OWNER (URGENT): register **diveszn.com / diveszn.io / diveszn.app** — all
  showed unregistered in the 2026-07 screen (`docs/name-change-diveszn-2026-07.md`)
  and standard-price availability evaporates fast.
- OWNER: attorney trademark knockout search for "DiveSZN" (certified
  USPTO/EUIPO) before merch/marketing spend; the 2026-07 screen used indexed
  mirrors + DNS only. Historical "Scubanaut" research kept in
  `docs/trademark-search-2026-07.md`.
- OWNER: add the site to Google Search Console and submit sitemap.xml.
- OWNER: add PEXELS_API_KEY repo secret; rerun fetch-images with --force.
- OWNER: apply to affiliate programs and paste the IDs into the `AFFILIATE`
  config at the top of the gear section in `index.html` (then rerun
  build_standalone): Amazon Associates (`amazon_tag`), AvantLink for
  Scuba.com + LeisurePro (`avantlink.website_id` + per-merchant IDs), Awin
  for Tradeinn/Diveinn/Scubastore (`awin`), eBay Partner Network
  (`ebay_campid`), optional Skimlinks (`skimlinks_id`) to auto-affiliate all
  other stores while approvals are pending. Empty values leave links raw —
  already safe in production.
- Swap sample Centres/Safaris for real listings.
- Mobile design pass (calendar table and planner filters on small screens).
- Logo refinement (fluke + a diving cue, lockup + size rules).
- Prune leftover artifacts: map-A/map-B demo pages, diving-calendar-24-periods.md.
- Later: wetsuit-by-temp recommender, price alerts, verified-diver reviews,
  dive log (needs a backend).

## How to continue in a new session
Open a new Claude Code session on `DonLybero/Diving-site` (branch `main`).
Tell the agent: *"Read HANDOFF.md and continue building the DiveSZN site."*
