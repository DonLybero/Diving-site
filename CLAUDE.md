# CLAUDE.md — DiveSZN

DiveSZN is a static diving website: a seasonal **trip planner / calendar** for
102 world dive destinations, wrapped in a dive-hub (gear buyer's guides with
price comparison, 12 monthly destination hubs, marine-life encounter pages).
No backend.

**Read `HANDOFF.md` first** — it has the full project map, brand, data pipeline
and backlog. Quick orientation:

- **Site:** `index.html` is the entire app (HTML + CSS + inline JS) and is what
  GitHub Pages serves. The scoring/query engine is `diving-calendar.js`.
- **Canonical data:** `diving-destinations.json` (102 destinations × 12 months,
  725 named dive sites). Edit it directly — the `scripts/` sources only cover
  the original 50 destinations, so `build_master.py` runs as a safe merge
  against the canonical file (see below).
- **Live:** https://donlybero.github.io/Diving-site/ — auto-deploys on push to
  `main` via
  `.github/workflows/deploy-pages.yml`.

## Build / regenerate (paths are repo-relative)
```bash
python3 scripts/build_master.py      # diving-destinations.json + CSVs (safe merge)
python3 scripts/build_rankings.py    # diving-rankings.json
python3 scripts/build_standalone.py  # diving-site.html (offline single file)
python3 scripts/build_pages.py       # destinations/gear/marine-life/months/*.html
                                     #   + about/how-we-score/privacy + sitemap
npm test                             # dive log test suite (node --test, zero deps)
```

## Dive log (divelog.html — client-side, no backend)
PRD + every architecture decision: `docs/divelog-prd.md`. Shape: `divelog.html`
+ `divelog.js` (UI) over `lib/divelog/` (plain ES modules, browser + node —
no build step, no TypeScript). Dives live in the visitor's IndexedDB behind a
swappable store interface (`store.js` — Phase 2 accounts/sync replaces only
that module); import pipeline is detect → parse → validate → dedupe (±3 min
start/±2 min duration) → preview → commit; the UDDF exporter is the
portability guarantee (round-trip test must always flag 100% duplicates).
Security invariants: all user XML goes through `lib/divelog/xml.js`, which
rejects any DTD/ENTITY markup before parsing (XXE + billion-laughs); 20 MB
cap + sample/dive caps in `types.js`; never render imported text as HTML
(`divelog.js` builds DOM via textContent only); the page makes no network
requests with user data.

**Adding a parser** (one module, never touches existing code):
1. Create `lib/divelog/parsers/<format>.js` exporting a `ParserModule`
   (`{id, displayName, extensions, sniff(bytes,text), parse(bytes,text,opts)}`
   — see `types.js`). `parse` never throws and may be async (the pipeline
   awaits it — FIT lazy-loads its 400 KB vendored SDK this way): file-level
   failures → `errors[]`,
   per-dive salvage → `warnings[]`, dives in metric canonical form
   (`validateDive` runs later in the pipeline). Base field semantics on
   Subsurface/libdivecomputer reference code, not guesswork.
2. Register it in `lib/divelog/parsers/index.js` (`PARSERS` — order matters:
   strongest sniffs first, CSV stays last).
3. Add a realistic fixture in `test-fixtures/` + a test file in
   `tests/divelog/` (dive count, first/last dive fields, samples length, one
   salvage case), and extend the UDDF export round-trip check.
4. `npm test`, then verify in the browser (serve locally, import the fixture).
`build_master.py` **safe-merges by default**: the canonical file's roster and
order are authoritative, sources only refresh the destinations they know
about, and it refuses to drop anything without an explicit flag. Flags:
`--dry-run` (report, write nothing), `--allow-additions` (let sources-only
entries in), `--allow-removals` (DANGEROUS full regenerate — sources only
describe the original 50 destinations). The old behaviour where a plain run
could overwrite the full dataset with 50 is fixed (commit
`afc25e5`).

After editing data or `index.html`, rerun `build_standalone.py` so the
single-file build stays in sync, then commit. Pushing deploys automatically.

## Working agreement (owner-mandated — binding for EVERY session)
- **All work happens on feature branches.** Never commit to or push `main`
  directly, and never merge to `main` on your own judgement — pushing `main`
  deploys the live site.
- **Merge to `main` only when the owner explicitly says "merge" in the
  current session.** Approval given in another session, or for an earlier
  change, does not carry over. If in doubt, ask; do not merge.
- **One session per area.** Before touching a file, assume another session
  may be active: fetch first, work only on your own branch, and never push
  to or delete another session's branch. (Two sessions merged to `main`
  minutes apart on 2026-07-15 — this rule exists so that never races the
  live site again.)
- Preview work by serving the branch locally or via a hosted artifact —
  never by deploying.

## Conventions
- **Design/copy work:** load the `diveszn-design` skill first
  (`.claude/skills/diveszn-design/` — brand system, editorial rules, imagery
  standard, QA workflow); `frontend-design` (official Anthropic skill) backs
  it for general visual-design craft.
- Keep the scoring formula identical in `build_rankings.py` and
  `diving-calendar.js` (rating base + marine-life bonus ≤25 + visibility 0..18).
- Brand: name **DiveSZN** ("dive season"; wordmark `Dive<b>SZN</b>`), whale-**fluke** logo (no helmets/circles),
  **light/white theme** with teal ink + accents, coral strictly for buy/booking
  CTAs (prices are quiet ink mono — never coral), monospace data readouts,
  serif headings. Header is brand-only (the ad slot was removed 2026-07).
- Season ratings use the **tonal palette** everywhere (Peak `#0e7569`,
  Good `#5cb8ab`, Shoulder `#dfa826`, Low `#cfe4e0`, Closed `#b9c6c9`; white
  text only on Peak). It lives in TWO places that MUST stay in sync: the
  `TONAL`/`RCOLOR` maps in `index.html` and `TONAL`/`TONAL_TEXT` in
  `scripts/build_pages.py`.
- Editorial rules (owner-mandated): scuba only (no freediving/snorkel copy);
  never name third parties in site copy (PADI, magazines, testers…); no
  aphorism intros; taglines never cite destination counts; specs never say
  "Both" — spell options out. Full list in HANDOFF.md §3.
- Everything published is **real and researched** — calendar/dive-site data,
  destination photos, monthly articles, the Gear guide (`gear-guide.json`,
  118 items, 346 retailer buy links, indicative prices). No sample sections
  remain. Tabs: the **Dive Planner** tab is the filter + ranked results
  (cards/map/year calendar) with its tab + filter state written to the URL;
  the **Destinations** tab is the browse directory + search — destinations
  open their own static pages (`destinations/<slug>.html`), no inline
  profile; the gear tab is named **Scuba Gear**; **Marine Life** is the
  Encounter Files (cover wall, scrubbable season pulse, evidence ledger).
  See HANDOFF §4/§6.
- Every finished change gets merged to `main` (auto-deploys); verify on
  desktop AND ~390px mobile viewports before merging.
- Verify UI changes by serving locally (`python3 -m http.server`) — `index.html`
  fetches JSON so it needs HTTP, not `file://` (the standalone build works on
  `file://`).
