# Scubanaut — project handoff

A diving website: a **seasonal trip planner / calendar** for 50 world dive
destinations, wrapped in a **dive-hub** (gear price-comparison, reviews, dive
centres, liveaboard safaris). Static site, no backend, deployable anywhere.

- **Live site:** https://donlybero.github.io/Diving-site/
- **Repo:** `DonLybero/Diving-site`
- **Working branch:** `claude/diving-destinations-research-73uc5i`

## Brand
- **Name:** Scubanaut. **Logo:** a whale **fluke** (bare tail, no circle/text) — inline SVG in `index.html` header + the favicon (data-URI).
- **Design language:** deep-ocean "instrument panel" — luminous **aqua** (`#2fe0d6`) on deep **teal** (`#04202b`), **coral** (`#ff7a59`) reserved for prices/scores/CTAs. **Monospace** "dive-computer" readout chips for water temp / visibility / current; **editorial serif** (Georgia) for headings.

## What's real vs. sample data
- **REAL, researched:** the 50-destination seasonal dataset — per-month water
  temperature, marine life, conditions, visibility, season rating, plus
  current strength and coordinates. Powers the Calendar, Best-period, Plan,
  Map, Search and Dive Sites sections.
- **SAMPLE/placeholder (structured like real feeds, ready to swap):** Gear
  prices/dealers, the Reviews article picks, Dive Centres, Safaris. Buttons
  pop a demo message; they become affiliate links later.

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
- `scripts/build_master.py` merges all of them, derives `visibility_m` (parsed from conditions text), `current_strength` (Low/Medium/Strong), and coordinates, then writes the JSON + CSVs.

**After changing data, rerun the three scripts**, then commit. The push
auto-deploys.

## Scoring (kept identical in `build_rankings.py` and `diving-calendar.js`)
`score = rating_base (Peak100/Good72/Shoulder48/Low22; Closed excluded)
       + min(marine-life keyword bonus, 25)
       + visibility_bonus (0..18, scaled from visibility_m: <=5m→0, >=35m→18)`

## Deploy
GitHub Pages is set to **Source = GitHub Actions**. The workflow publishes the
repo root; `index.html` is the landing page. Every push to the working branch
redeploys within ~1–2 min. If you rename the branch, update the `on.push.branches`
list in `.github/workflows/deploy-pages.yml`.

## Common next tasks / backlog
- Group the nav (11 tabs is a lot) — e.g. a "Plan" group (Calendar/Best/Plan/Map) vs "Hub" group (Gear/Reviews/Centres/Safaris).
- Swap sample Gear/Centres/Safaris for real affiliate-feed data (Amazon, ShareASale/AvantLink, Booking/Divebooker).
- Hand-tune borderline current-strength ratings (auto-classified from text).
- Add a real recompression-chamber directory; add wetsuit-by-temp recommender; price-history/alerts; user dive log (needs a backend).
- Verify a couple of destinations' data with local operators.

## How to continue in a new session
Open a new Claude Code session on `DonLybero/Diving-site`, working branch
`claude/diving-destinations-research-73uc5i` (or merge it to `main` first and
work there — then update the workflow branch). Tell the agent: *"Read
HANDOFF.md and continue building the Scubanaut site."*
