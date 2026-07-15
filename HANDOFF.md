# DiveSZN — project handoff & framework

**Read this file first in every new session.** It is the single source of truth
for what DiveSZN is, how it's built, the non-negotiable editorial rules, the
operating playbook, and the roadmap. When the owner asks for "a new thing",
slot it into this framework rather than inventing a parallel one.

---

## 1. What DiveSZN is

A static diving website whose USP is answering **WHEN to dive WHERE**:

- **Core product — Dive Planner:** a seasonal trip planner over 83 world dive
  destinations × 12 months of researched data (season rating, water temp,
  visibility, marine life, conditions, currents). Results render three ways:
  ranked cards, world map, year calendar — and the tab + filter state lives
  in the URL, so filtered views survive the back button and are shareable.
- **Wrapped in a dive hub:** a monetization-ready Scuba Gear guide
  (6 categories, 118 items, 346 retailer buy links, price comparison),
  a Destinations directory with search (each destination opens its own
  static page), Marine Life "Encounter Files" (9 species pages), 12 monthly
  "Top Destinations in <Month>" hub pages ranked by the scoring engine,
  and 725 named dive sites.
- **No backend.** Pure static: HTML + CSS + vanilla JS + JSON. GitHub Pages.

- **Live site:** https://donlybero.github.io/Diving-site/
- **Repo:** `DonLybero/Diving-site` · trunk is `main`; work on a feature
  branch, then **merge every finished change into `main`** (standing owner
  instruction) — pushing to `main` auto-deploys in ~1–2 min.

## 2. Brand & design system

- **Name:** DiveSZN ("dive season", sports-slang SZN). Wordmark `Dive<b>SZN</b>`.
  Renamed from "Scubanaut" 2026-07 (`docs/name-change-diveszn-2026-07.md`).
- **Logo:** a whale **fluke** — bare tail, no circles, no helmets. Inline SVG
  in the header + data-URI favicon.
- **Theme:** **light/white** (owner-directed redesign 2026-07; the old deep-teal
  dark theme is retired). Palette lives in `:root` of `index.html`:
  near-white backgrounds (`--bg:#f4f9f9`, panels `#ffffff`), dark teal ink
  (`#0e2f37`), teal accent (`#0e9c92` family), **coral (`#ff7a59`) strictly for
  buy/booking CTAs** — prices are quiet ink mono, never coral (owner ruling
  2026-07).
- **Season ratings — tonal palette everywhere** (owner ruling 2026-07):
  Peak `#0e7569`, Good `#5cb8ab`, Shoulder `#dfa826`, Low `#cfe4e0`,
  Closed `#b9c6c9`; white text only on Peak. Duplicated by design in
  `index.html` (`TONAL`/`RCOLOR`) and `scripts/build_pages.py`
  (`TONAL`/`TONAL_TEXT`) — keep them in sync.
- **Typography:** editorial serif (Georgia) for headings, sans for body,
  **monospace "dive-computer" chips** for data readouts (temps, viz, scores).
- **Header is brand-only** — the owner removed the ad slot 2026-07; keep it
  slim, don't reintroduce ad placements without an owner decision.
- **Icons:** inline SVG system (`ICONS` map) — never emoji in UI.

## 3. Editorial rules (owner-mandated, NON-NEGOTIABLE)

1. **Scuba only.** Never mention freediving/snorkelling as the site's audience;
   snorkel-only sites were deliberately removed from the data.
2. **Never name third parties in site copy** (no PADI, ScubaLab, DiveIn,
   magazines, YouTubers, testers, "listed by" credits) — legal-risk decision.
   Retailer names inside buy links/price tables are the only exception.
3. **No aphorism intros.** Never open copy with lines like *"Dive trips are won
   in the planning."* Say directly what DiveSZN does for the reader.
4. **Taglines** say DiveSZN helps you plan your dive ahead / pick the best
   destination for your dates — and **never cite destination counts**.
5. **Gear specs must be explicit** — never write "Both"; spell out
   e.g. "open heel and full foot". Reviews must be genuinely informative
   (what it is, why it matters underwater), not marketing fluff.
6. **Photo credits:** keep attribution data, but on the page it renders as a
   corner tooltip-only ⓘ (owner didn't want a visible photographer name, and
   did NOT want the photo itself replaced). No other credit treatment.
7. Prices are indicative; depth figures always carry the "confirm with your
   operator" caveat.

### Owner rulings, 2026-07 redesign week (same weight as the rules above)
8. **No prices on the homepage gear band** — the homepage sells the guides,
   not the products; prices live on the gear pages/tables.
9. **No colour mentions anywhere in gear copy** — reviews, blurbs, specs,
   static pages, standalone build. (`colors`/`color_source` fields remain in
   `gear-guide.json` as data but are never rendered.)
10. **Season ratings use the tonal palette everywhere** (see §2) — the old
    bright badge palette (green/blue/amber) is retired on every surface.
11. **Photos carry no overlays**: destination, gear and marine photos get no
    fact pills, no captions, no numbering on the image. Credits are the
    corner tooltip only (rule 6).
12. **A destination opens its own page** (`destinations/<slug>.html`) — same
    pattern as gear products — never an inline profile below the directory.
13. **Photo heroes carry the name only** — no kicker sentences, no sub-lines
    on any photo (destination pages: just the destination name; hubs may keep
    a two-word section label).
14. **Grandfathered vocabulary (owner-reviewed 2026-07-11):** the 10 existing
    uses of "mecca" (Cocos, Galápagos highlights), "world-class" (Scapa Flow,
    Apo/Dumaguete, Bali, Marsa Alam highlights + one dive-site blurb) and
    "playground" (Mallorca, Tenerife descriptions + one blurb) were shown to
    the owner, who ruled **they stay as written** — do NOT "fix" them. The
    banned-vocabulary rule still applies in full to all NEW copy.

## 4. Architecture & file map

| File | What it is |
|------|-----------|
| `index.html` | **The whole app** — HTML + CSS + inline JS in one file. What Pages serves. Tabs: Home (brand), **Scuba Gear**, **Destinations** (browse directory + search; each destination opens its static page), **Marine Life** (the Encounter Files: cover wall, scrubbable season pulse, evidence ledger), **Articles** (12 monthly), **Dive Planner** (seasonal filter + ranked results — cards/map/year calendar — with tab + filter state in the URL), Search. The footer link tree is **static HTML** (works without JS). |
| `diving-calendar.js` | Scoring/query engine: `rankPeriod`, `rankWindow`, `getDestination`, `searchDestinations`, `destinationSeasonSummary`. Browser + Node. |
| `diving-destinations.json` | **Canonical data** — 102 destinations × 12 monthly entries + metadata (coords, currents, wetsuit, access, dive_sites — 725 named sites total, image). |
| `gear-guide.json` | Gear guide data — 6 categories, **118 items** (wetsuits grouped by thickness), **346 buy links**: review, specs dict, image (local `assets/gear/`), cheapest-first buy options, article intro/tips. Unrendered `colors`/`color_source` fields remain as data (owner ruling: no colour mentions in copy). |
| `diving-site.html` | Single-file offline build (all JSON/JS inlined). **Regenerate after every index.html or data change** (`scripts/build_standalone.py`). |
| `destinations/*.html` | 102 static destination pages + directory (`scripts/build_pages.py`). |
| `gear/`, `marine-life/`, `months/` | Static gear pages (per item + per category + index), 9 marine species pages + index, 12 month hub pages + index — all generated by `scripts/build_pages.py`, which also writes `about.html`, `how-we-score.html`, **`privacy.html`**, `sitemap.xml` and `robots.txt`. Never hand-edit these; edit the generator. |
| `assets/gear/` | ~111 self-hosted product images (no hotlinking) + `studio/` uniform-background derivatives (`scripts/studio_gear.py`). |
| `vendor/` | Self-hosted Leaflet + world-land geojson (offline map basemap) + `fxp.esm.min.js` (pinned fast-xml-parser 5.10.0 ESM bundle for the dive log — rebuild command in its banner). |
| `divelog.html` + `divelog.js` | **Dive log** — client-side logbook (UDDF/Subsurface/Suunto SML/Garmin FIT/CSV imports, depth-profile charts, UDDF export). Hash-routed views; dives live in the visitor's IndexedDB, nothing uploaded. Installable PWA: `divelog.webmanifest` + `divelog-sw.js` (narrow, whitelist-only, network-first service worker → the logbook opens offline; it never touches other pages' requests). v1 PRD: `docs/divelog-prd.md`; accounts/sync design: `docs/divelog-phase2-accounts-sync.md`. |
| `lib/divelog/` | Dive log engine (plain ES modules, browser + node): hardened XML boundary (`xml.js` — rejects DTD/ENTITY), parser registry with content sniffing (`parsers/` — UDDF, Subsurface, Suunto SML, CSV w/ column mapping), canonical model + validation (`types.js`), ±3 min/±2 min duplicate detection, swappable store (IndexedDB/Memory), import pipeline, UDDF exporter. **How to add a parser: see CLAUDE.md.** |
| `tests/` + `test-fixtures/` | `node --test` suite (85 tests, zero deps — `npm test`): per-parser fixtures cross-checked against format specs, hostile files (XXE, billion-laughs, truncated, masquerading extensions), and the export→re-import round-trip that must always flag 100% duplicates. |
| `scripts/` | Data build pipeline + CI fetchers (below) + audits: `audit_marine_keywords.py` (read-only check of the keyword matching behind every marine "where & when" surface), `studio_gear.py` (gear photo → studio-shot pipeline). |
| `.github/workflows/deploy-pages.yml` | Deploys repo root to Pages on push to `main`; also manual `workflow_dispatch`. |
| `.github/workflows/fetch-images.yml` | Destination photos from Wikimedia/Pexels (runs on Actions runners — they have internet). |
| `.github/workflows/fetch-gear-images.yml` | Gear product images from retailer og:image, localized into `assets/gear/`. |
| `.github/workflows/check-buy-links.yml` | Monthly report-only health check of every gear-guide buy link (`scripts/check_buy_links.py`); dead/redirected links in the run summary + JSON artifact. |
| other workflows | `fetch-marine-images.yml`, `fetch-brand-photos.yml`, `photo-candidates.yml`, `audit-marine-images.yml`, `ui-audit.yml` and small fetch/screenshot helpers — all follow the same "runners have internet" pattern (§8). |

### Key JS structures inside `index.html`
- `AFFILIATE` config + `affLink()` — affiliate wiring (§7).
- `REGION_GROUPS` / `DEST_GROUP` + `buildRegionMenu()` etc. — the planner's
  cascading region picker (8 continents, alphabetical, arrow expands to
  destination · country; picking filters cards/map/calendar).
- `MONTH_INTROS` + `renderDestinations()` / `openMonthArticle()` — 12 monthly
  articles, ranked live by the engine.
- `GEAR_GUIDE` + `renderGear()` / `gearEntry()` — magazine-style article list +
  per-item photo/review/specs/price-table.
- `openProfile()` — navigates to the destination's **static page**
  (`destinations/<slug>.html`), same pattern as gear products. There is no
  inline profile any more (the old renderer was dead code and was deleted);
  the full profile — intro, season calendar, conditions grid, dive-sites
  table, month-by-month — is generated by `build_pages.py`.

## 5. Data pipeline

`diving-destinations.json` is canonical. Either edit it directly or regenerate:

```bash
python3 scripts/build_master.py      # sources -> diving-destinations.json + CSVs (safe merge)
python3 scripts/build_rankings.py    # -> diving-rankings.json
python3 scripts/build_standalone.py  # -> diving-site.html (ALWAYS after UI/data edits)
python3 scripts/build_pages.py       # -> destinations/gear/marine-life/months/*.html + sitemap
```

**`build_master.py` is a safe merge by default** (fixed in commit `afc25e5`):
the sources under `scripts/` only describe the ORIGINAL 50-destination world,
while the canonical file has grown to 102 (destinations added/split/retired
directly in the output file). A plain run keeps the canonical roster and
order authoritative — sources only refresh the destinations they know about,
and the script hard-refuses to drop anything. Flags: `--dry-run` (compute and
report, write nothing), `--allow-additions` (let sources-only entries enter —
usually retired ones, so off by default), `--allow-removals` (DANGEROUS: full
regenerate from sources, dropping canonical-only destinations). The old
danger — a documented plain run silently overwriting the canonical roster with
50 — is gone.

Sources: `scripts/build_csv.py` + `scripts/meta11.py` (original 11
destinations), `scripts/data/*.json` (the other 39), `scripts/data/dive_sites.json`
(the original 409 verified dive sites — Google-verified, snorkel-only culled,
per-site `source` field is research provenance and is **stripped from
published output**; sites for newer destinations live directly in the
canonical file, **725 sites total**), `scripts/data/verification.json`
(hand-verified currents). `build_master.py` merges everything, derives
`visibility_m` and `current_strength`, and preserves baked `image` fields.

### Scoring (MUST stay identical in `build_rankings.py` and `diving-calendar.js`)
```
score = rating_base (Peak 100 / Good 72 / Shoulder 48 / Low 22; Closed excluded)
      + min(marine-life keyword bonus, 25)
      + visibility bonus 0..18 (visibility_m <=5m → 0, >=35m → 18)
```

## 6. What's real vs sample

- **REAL:** the 102-destination seasonal dataset, 725 dive sites, destination
  photos (Wikimedia/Pexels, openly licensed, attribution kept in data), the
  Gear guide (118 researched picks, indicative prices, real retailer links,
  local images), the 9 marine-life species pages, and the 12 monthly
  Destination articles / month hub pages (computed from real data).
- **SAMPLE:** none left on the published site. The old sample Reviews,
  Dive Centres and Liveaboard Safaris sections were **removed** 2026-07; the
  old "coming soon" Trip Planner placeholder was replaced 2026-07 by the
  **Dive Planner** tab — the real seasonal filter + ranked result views
  (cards / map / year calendar), moved out of the Destinations tab, which now
  holds only the browse directory + profiles. (Only sample strings left in
  code: the `GEAR` fallback array in `index.html`, shown solely if
  `gear-guide.json` fails to load and labelled "sample price" when it does.)

## 7. Monetization (wired, awaiting owner sign-ups)

- `AFFILIATE` config at the top of the gear JS in `index.html`:
  Amazon Associates (`amazon_tag`), AvantLink (Scuba.com/LeisurePro), Awin
  (Tradeinn/Diveinn/Scubastore), eBay EPN (`ebay_campid`), optional Skimlinks.
  **Empty values leave links raw — safe in production.** After pasting IDs,
  rerun `build_standalone.py`.
- All buy links: `rel="noopener sponsored"`, cheapest-first tables.
- `AFFILIATE.liveaboard_aff` is configured but currently **unreferenced in
  the app** (its only consumer was the inline profile, deleted as dead code)
  — see §9 for the static-page monetization note.
- The header ad slot was removed 2026-07 (header is brand-only, §2); an ad
  placement would need a fresh owner decision.

## 8. Operating playbook (how work gets done here)

- **Branch → verify → merge to main** every finished change. The owner expects
  changes to be *live*, not parked on a branch.
- **Always rerun `build_standalone.py`** after touching `index.html` or any
  JSON — `diving-site.html` must stay in sync (it ships in the same commit).
- **Verify in a real browser before shipping:** serve with
  `python3 -m http.server` (index.html fetches JSON — `file://` won't work) and
  drive it with Playwright (Chromium at `/opt/pw-browsers/chromium`,
  `--no-sandbox`). Test BOTH desktop (~1280px) and phone (~390px) viewports;
  assert zero horizontal page scroll and zero page errors. External images
  failing to load in the sandbox is normal (blocked egress), not a bug.
- **The dev sandbox has no internet** (proxy 403s). Anything that needs the
  web (image fetching, link checking) runs as a GitHub Actions workflow —
  runners have internet. Pattern: `fetch-images.yml`, `fetch-gear-images.yml`.
- **Deploy quirks:** pushes made by workflows with `GITHUB_TOKEN` do NOT
  trigger the Pages deploy — dispatch `deploy-pages.yml` manually after bot
  commits. **Never re-run a failed Pages run** (it dies with "Multiple
  artifacts named github-pages") — trigger a *fresh* dispatch instead.
  Occasional "Deployment failed, try again later" = GitHub incident; retry.
- **Cache note:** Pages serves with ~10-min browser cache; "nothing changed"
  reports right after a deploy are usually the phone's cache.
- **MCP `actions_list` output is huge** — save to file and extract
  status/conclusion with a small python snippet instead of reading it raw.
- **Mobile CSS gotchas already solved** (keep them working): grid/`.gentry`
  items need `min-width:0`; `.specs` auto-fill grid must cap at 2 columns on
  phones; `.ptable` restacks (store+price line, full-width buy button);
  `.rsel-menu` anchors to the controls panel on ≤640px; `#profile` tables
  scroll inside their own box; `.controls` carries `z-index:30` so the region
  dropdown isn't painted under the result cards (its `backdrop-filter`
  creates a stacking context).

## 9. Roadmap

### Owner decision (2026-07): site to be owned by a UAE freezone company
The owner is forming a **UAE freezone company** that will own DiveSZN (domain +
site as company assets), so several items below are deliberately **deferred
until the company + domain exist** — to avoid doing them twice and to keep the
IP with the entity from day one. Do them as one batch at launch (see checklist).

**Launch checklist — blocked on company + domain (do together):**
1. **Register diveszn.com** under the company (grab/watch the name meanwhile so
   it isn't sniped; a personal→company transfer later is cheap if needed).
2. **Google Search Console** — set up **once, as a Domain property on
   diveszn.com** (DNS TXT verify), then submit the sitemap. Deliberately NOT
   done on the github.io URL-prefix property to avoid duplicate setup + a
   Change-of-Address migration. Update sitemap.xml/robots.txt to the new domain.
3. **Privacy policy** (`privacy.html`) — swap operator to the real entity name +
   real contact email (currently placeholder `privacy@diveszn.com`), and add a
   UAE **PDPL** governing-law line (plus DIFC/ADGM rules if incorporated there).
   Not legal advice — owner's formation agent/lawyer to confirm.
4. Apply to affiliate programs (business details/payout under the company);
   paste IDs into `AFFILIATE`; rebuild standalone. NOTE: the static gear
   pages (`gear/*.html`, built by `build_pages.py`) link *raw* retailer URLs
   — the JS `affLink()` only wraps links in the SPA. Once IDs are live,
   either port `affLink()` into `build_pages.py` (add a Python `aff_link`
   used by `buy_box`) or accept that the crawlable gear pages funnel buy
   clicks to raw retailers while the app is the monetized surface.
5. Attorney trademark knockout for "DiveSZN" before marketing spend.
6. Consider a short **Terms of Use** page to sit beside the privacy policy.

### Owner tasks (not domain-blocked)
- Optional: add `PEXELS_API_KEY` repo secret, rerun fetch-images `--force`
  for higher-quality destination photos.
- Pick an ad network / direct sponsor for the header slot **when there's
  traffic** (also triggers a cookie-consent banner + privacy-policy ad section).

### Analytics (PM recommendation, 2026-07)
Measure the minimum that answers "what earns," cookielessly, when traffic
arrives — not before. Recommended: a **cookieless tool** (Cloudflare Web
Analytics free, or Plausible/Fathom) + **outbound "Buy"-click event tracking**
(the money signal), which needs no consent banner and only a one-line policy
mention. Hold **GA4** until running Google Ads or needing deep funnels (it
brings the consent banner). Wiring is ready to add once the owner picks a tool
and supplies the site token.

### Near-term engineering / known leftovers (2026-07 audit)
- Quarterly gear-price refresh ritual (prices are indicative, drift over time).
- **Owner photo needs:** a genuine Fuvahmulah **underwater** shot, and a real
  **Protea Banks** photo (the wrong-location stand-ins — Tiger Beach and
  Aliwal Shoal — were removed; run the owner A/B/C review flow to fill them).
- `gear/wetsuits.html` is ~236KB — 5–7× heavier than any other generated
  page; worth splitting or trimming before it hurts mobile.
- `scripts/build_standalone.py` is brittle: exact-string patching of
  `index.html` plus unescaped JSON embedding — cosmetic app edits can break
  the build silently. Harden when next touched.
- `AFFILIATE.liveaboard_aff` is configured but unreferenced in the app (its
  only consumer was the deleted inline profile). When wiring static-page
  monetization (launch checklist item 4), give it a consumer on the
  generated destination pages (Python `aff_link` in `build_pages.py`).

### Mid-term product
- Dive Planner: shipped 2026-07 (seasonal filter + ranked results, with tab +
  filter state in the URL — shareable, back-button-safe). Still open: growing
  it into an end-to-end trip tool (it superseded the removed sample Safaris
  listings; any listings it shows must match the gear guide's research
  standard).
- Wetsuit-by-temperature recommender (data already has per-month temps +
  wetsuit field — pure front-end feature).
- Destination comparison view (pick 2–3, compare months side by side) — the
  gear compare shipped; the destination version is still open.
- Logo refinement (fluke + a diving cue; lockup + size rules).
- Dive log: shipped 2026-07 as a client-side v1 (`divelog.html` — UDDF,
  Subsurface XML, Suunto SML, Garmin FIT and CSV import; profile charts; UDDF
  export; installable/offline PWA; dives stay in the visitor's browser).
  Still open, in priority order: accounts + sync
  (`docs/divelog-phase2-accounts-sync.md`, blocked on company/domain),
  "switching from [brand] to [brand]" SEO articles linking the tool at the
  new-computer purchase moment, Shearwater Cloud XML, DAN DL7, and promoting
  the footer link into the SPA's tab row (owner call).
- Dive log format requests: the importer's rejection message invites divers to
  name the app their file came from — collect these; they are the parser
  roadmap, for free (PRD §12).

### Long-term (needs a backend or third-party services)
- Price alerts; verified-diver reviews; dive-log accounts + cross-device sync
  (Phase 2 in `docs/divelog-prd.md` — the store interface in
  `lib/divelog/store.js` is the swap point; parsers/UI don't change).

## 10. How to continue in a new session

1. Read this file, then `CLAUDE.md`.
2. Honor §3 editorial rules and §8 playbook in every change — they are owner
   directives, not suggestions.
3. Workflow for any request: implement on the feature branch → rebuild
   standalone → Playwright-verify desktop + mobile → commit → push → merge
   `--no-ff` to `main` → confirm the `deploy-pages.yml` run is green (fresh
   dispatch if needed) → report back with what changed and evidence
   (screenshots for UI work).
