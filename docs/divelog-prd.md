# DiveSZN Dive Log — import any brand's dive computer export

**Status:** approved for build, 2026-07-15 · **Branch:** `claude/dive-log-import-yc69au`
**This is the DiveSZN redraft** of the original "Fathom" PRD. The name is replaced
throughout, and §6/§9/§13/§14 are adapted to DiveSZN's actual stack (static
GitHub Pages site, no backend) — every deviation is listed in §15 with the
reasoning and the owner decision that authorised it.

## 1. Problem statement

Divers lose their dive history when they switch dive computer brands or upgrade
devices, because manufacturers (Suunto, Cressi, Mares, Shearwater, Garmin, etc.)
keep logs in proprietary, siloed apps and file formats. There is no mainstream
consumer website that lets a diver upload whatever export file their brand's app
produces and get a permanent, brand-neutral logbook. DiveSZN will offer this as
a free feature: it solves a real, widely complained-about pain point, and it
converts anonymous content readers into returning users with a reason to come
back — the audience DiveSZN's affiliate revenue depends on.

## 2. Goals

- A diver can open the Dive Log page, upload a dive log export file from any of
  the Phase-1 supported formats, and see their dives in a clean logbook within
  2 minutes, with zero manual re-entry — and (v1) zero sign-up.
- Every imported dive preserves the data that matters to divers: date/time,
  site, max/avg depth, duration, water temperature, and the full depth-over-time
  profile where the source file contains one.
- The diver can export their entire logbook at any time as UDDF (the open
  standard), proving DiveSZN is the opposite of a silo. This is the marketing
  story: **"your dives, finally yours."** In the v1 client-side architecture the
  story is even stronger: *your dives never leave your browser.*
- The system is maintainable by one person: each file format is an isolated
  parser module behind a single common interface, so adding a new brand never
  touches existing code.

## 3. Non-goals (v1)

- **No direct device connections.** No Bluetooth, USB, or cable downloads from
  dive computers. That is driver/firmware territory (what libdivecomputer does
  natively) and is out of reach for a web app. We import the files that every
  brand's own app can already export.
- **No dive planning, deco calculation, or gas blending tools.** Logbook only.
  Anything that computes decompression is a safety liability and a separate
  product.
- **No accounts, sync, or server storage in v1** (deviation from the original
  draft — see §15). Dives persist in the browser (IndexedDB); UDDF export is the
  diver's portable backup. The account + cloud-sync layer is Phase 2 and the
  store interface is written so it can be swapped in without touching parsers
  or UI.
- **No social features.** Architecture should not preclude them (dives have a
  `visibility` field defaulting to `private`), but nothing is built.
- **No mobile app.** Responsive web only.
- **No paid tier logic.** Free while we learn; don't build billing.

## 4. User stories (priority order)

1. As a diver switching from Suunto to Shearwater, I want to upload my old
   Suunto export so that my 400-dive history lives on in one place.
2. As a diver, I want to see each dive's depth profile as a chart so that my
   logbook feels like a real logbook, not a spreadsheet.
3. As a diver, I want duplicate dives detected when I upload overlapping files
   so that importing twice doesn't wreck my log.
4. As a diver, I want to export everything as UDDF so that I'm never locked
   in — including by DiveSZN.
5. As a diver with a paper logbook past, I want to add dives manually so that
   my count is complete.
6. As a diver, I want to edit imported dives (site name, buddy, notes) so that
   I can fix what the computer didn't know.

## 5. Format support matrix (phased)

The strategy: accept export files, normalize everything into one canonical
internal model based on UDDF concepts. Reference implementations for every
parser exist in the open-source Subsurface project and its libdivecomputer
library — use their documentation and code as the source of truth for field
semantics, not guesswork.

| Phase | Format | File ext | Notes |
|---|---|---|---|
| P0 | UDDF (Universal Dive Data Format) | `.uddf` | Open XML standard; also our canonical model and export format |
| P0 | Subsurface XML | `.xml`, `.ssrf` | Huge installed base; well-documented open format |
| P0 | Generic CSV | `.csv` | Column-mapping UI; catches everything else, incl. spreadsheet logbooks |
| P0 | Suunto DM4/DM5 export | `.sml`, `.xml` (SDE zip = P1) | DM5 exports SML and XML; largest legacy brand pain point |
| P1 | Garmin FIT | `.fit` | Binary; use Garmin's FIT SDK (JS). Warning: the Suunto app also emits FIT with different field encoding — detect vendor and branch, or reject Suunto-FIT with a message pointing to DM5 export until handled |
| P1 | Shearwater Cloud XML | `.xml` | Shearwater desktop/cloud exports XML; DB import is P2 |
| P1 | DAN DL7 | `.zxu`, `.txt` | Interchange format some apps emit |
| P2 | Shearwater Desktop DB | `.db` (SQLite) | Parse SQLite client-side (sql.js/WASM) |
| P2 | Mares, Cressi, MacDive, Diving Log exports | various | One module each, added on user demand — track requests |

**Format detection:** by extension first, then content sniffing (XML root
element, FIT magic bytes, CSV header row). Never trust extension alone.

## 6. Architecture — adapted to the DiveSZN stack

*(This section is rewritten from the original draft, which assumed an existing
Next.js 15 / React 19 app on Vercel with Auth.js and Supabase. DiveSZN is a
static site on GitHub Pages with no backend — see §15. The owner chose the
client-side, static-first architecture on 2026-07-15.)*

Integrate into the existing static site: plain HTML + ES-module JavaScript,
served by GitHub Pages, no build toolchain, no server, no new managed services.
Boring wins.

- **Auth:** none in v1. The feature works anonymously; dives are private by
  construction because they never leave the device. Phase 2 (accounts + sync)
  slots in behind the store interface.
- **Storage:** IndexedDB, behind a thin data-access layer
  (`lib/divelog/store.js`) exposing a store interface so the backing store is
  swappable (Phase 2: a synced server store) and no IndexedDB call ever appears
  in UI code. A `MemoryStore` implements the same interface for node tests.
- **File handling:** files are read in the browser (`File` → `ArrayBuffer`)
  and parsed locally. Nothing is uploaded anywhere. 20 MB cap and parse
  time-box enforced at the parse boundary.
- **Parsing runtime:** all parsers are pure functions
  `(bytes, name, options) → ParseResult` in dependency-light ES modules that
  run identically in the browser and under `node --test`. XML via a pinned,
  vendored `fast-xml-parser` (the repo already vendors Leaflet the same way).
- **Charts:** depth profiles rendered as inline SVG (no React in this repo;
  Recharts from the original draft applies to the Phase-2 stack if ever
  needed). Monospace axis readouts per DiveSZN brand.
- **Routes** (hash views on one static page, mirroring the original route plan):
  - `divelog.html` — the logbook (list + stats header: total dives, hours, max depth)
  - `divelog.html#import` — upload & preview flow
  - `divelog.html#dive/<id>` — single dive detail with profile chart
  - export = a client-generated UDDF download (no API route needed)

### Parser module contract

```
lib/divelog/
  parsers/
    index.js        // registry + format detection
    uddf.js
    subsurface.js
    csv.js
    suunto-sml.js
    // later: garmin-fit.js, shearwater-xml.js, dl7.js ...
  types.js          // CanonicalDive, ParseResult, ParserModule (JSDoc typedefs)
  export-uddf.js    // canonical dives → UDDF document
  store.js          // store interface + IndexedDBStore + MemoryStore
  dedupe.js         // duplicate detection
  pipeline.js       // detect → parse → preview → commit
  xml.js            // hardened XML parse shim (DOCTYPE rejection, size caps)
  units.js          // metric ↔ imperial display conversion
```

```js
// ParserModule
{
  id: 'uddf',                          // 'uddf', 'suunto-sml', ...
  displayName: 'UDDF',                 // 'Suunto DM5 (SML)'
  extensions: ['.uddf'],
  sniff(bytes, text): boolean,         // content-based detection
  parse(bytes, text, options): ParseResult  // never throws; returns errors[]
}

// ParseResult
{
  dives: CanonicalDive[],
  warnings: string[],   // per-dive salvage notes ("dive 12: no temperature")
  errors: string[]      // file-level failures
}
```

A malformed dive inside a file must never abort the whole import — salvage what
parses, report the rest in `warnings`.

## 7. Canonical data model

UDDF-shaped, stored as one record per dive in IndexedDB (the equivalent of the
original draft's "samples as JSONB on dives" decision — samples live inline on
the dive record; a 60-min dive at 10 s sampling ≈ 360 points, trivially fine).
All units metric internally (meters, °C, bar, kg); convert at the display layer
via a metric/imperial toggle remembered in the store's settings.

```
CanonicalDive {
  id
  number            // diver's own sequence number, editable
  startedAt         // ISO 8601 — store UTC + tz offset if source has it
  durationSec
  maxDepthM, avgDepthM?
  waterTempC?, airTempC?
  site? { name, lat?, lon?, country? }
  buddy?, diveMaster?, notes?
  tanks[]? { volumeL?, startBar?, endBar?, gasO2Pct?, gasHePct? }
  equipment?        // free text v1
  diveType          // 'scuba' | 'freedive' | 'other'  (data field only —
                    //  site copy stays scuba-only per editorial rules)
  visibility        // 'private' (default) | 'public' — future-proofing only
  source { importId?, parserId?, computerModel?, externalId? }
  samples[]? { tSec, depthM, tempC?, pressureBar? }   // profile points
}
```

Object stores: `dives` (keyPath `id`, index on `startedAt`), `imports` (file
metadata, status, counts), `settings` (unit preference, remembered CSV column
mapping). `userId` from the original draft is dropped until Phase 2 — the
browser profile *is* the user.

**Duplicate detection (P0):** two dives are duplicates when `startedAt` is
within ±3 minutes and duration within ±2 minutes. On import preview, flag
duplicates; default action = skip, user can override per dive.

## 8. Import pipeline & UI flow

1. **Upload** — drag-and-drop, max 20 MB, accepted extensions listed. Client
   shows file name + size.
2. **Detect & parse** (in-browser) — registry sniffs format, runs parser,
   returns `ParseResult`.
3. **Preview** — table of parsed dives (date, site, depth, duration), with
   badges: `new` / `duplicate` / `warning`. CSV path inserts a column-mapping
   step here (user maps their columns to canonical fields; mapping remembered).
4. **Commit** — user confirms; dives write to the store; import record saved
   with counts.
5. **Done** — link to logbook; summary "142 imported, 3 skipped as duplicates,
   1 warning".

Empty, error, and partial states are P0, not polish: unparseable file → clear
message naming the detected format and what to try instead; zero dives found →
say so; parser warnings → visible before commit.

## 9. Security & privacy requirements (non-negotiable)

- **XML parsing hardened against XXE:** any input containing `<!DOCTYPE` /
  `<!ENTITY` is rejected before parsing (the supported formats never
  legitimately use DTDs), which neutralises both external-entity resolution
  and entity-expansion (billion-laughs) attacks in one move; the vendored
  parser additionally never fetches external entities. This remains the #1
  attack surface of the feature even client-side — a hostile file must not be
  able to break or corrupt the logbook.
- **File size limit** (20 MB) enforced at the parse boundary and parse
  time-boxed; sample counts per dive capped. Zip-container formats (SDE) stay
  out of P0; when added, cap decompressed size.
- **No exfiltration by design:** the dive log page makes no network requests
  with user data; files are read locally and dives stay in IndexedDB.
- **Dives are private by default** (`visibility: 'private'`), and in v1 private
  by construction.
- **GDPR-friendly:** the "Delete all my dives" button wipes all dives, import
  records and remembered CSV column mappings from IndexedDB (the metric/imperial
  preference is not personal data and survives); nothing is stored server-side.
  (DiveSZN is UK/EU-facing.) State this plainly on the page and in the privacy
  policy.
- Phase 2 (accounts/sync) re-inherits the original draft's server rules:
  auth on every route, queries scoped by session `userId`, parameterized
  queries only, originals stored privately, secrets in env vars.

## 10. Testing

- `test-fixtures/` directory with at least one realistic sample file per
  supported format (structures cross-checked against Subsurface's reference
  implementation and format documentation) plus deliberately broken variants:
  truncated file, wrong extension, XXE payload, billion-laughs, empty file,
  1-dive file, 500-dive file.
- Unit tests per parser (`node --test`, zero test dependencies): correct dive
  count, spot-check first/last dive fields, samples length.
- One integration test of the full pipeline: parse fixture → preview → commit
  (MemoryStore) → dive appears in list → export UDDF → re-import exported
  file → duplicate detection catches 100%. (This round-trip test is the single
  best guard for the whole feature.)

## 11. Acceptance criteria (v1 ships when all true)

- [ ] User can open the Dive Log page, upload a UDDF, Subsurface XML, Suunto
      SML, or CSV file, preview, and commit — no sign-up required
- [ ] Dive list shows all dives with stats header; dive detail renders depth
      profile chart when samples exist and degrades gracefully when not
- [ ] Duplicate upload of the same file results in 0 new dives by default
- [ ] Manual dive add + edit + delete works
- [ ] Full logbook exports as valid UDDF that re-imports cleanly (round-trip
      test passes)
- [ ] Malformed/hostile files (fixtures) are rejected or salvaged with clear
      messages; XXE fixture does not resolve
- [ ] Works on ~390 px mobile viewport; empty/error/loading states present; no
      console errors
- [ ] CLAUDE.md updated with the feature's architecture, decisions, and how to
      add a parser

## 12. Success metrics

- **Leading (first 30 days):** visits to the Dive Log page from site nav;
  % of visitors who complete ≥1 import; import success rate (commits ÷ upload
  attempts) ≥ 80%; formats requested that we don't support (the rejection
  message invites divers to say which app produced the file — this is the P2
  roadmap, for free).
- **Lagging (90 days):** returning-visitor rate of logbook users vs. anonymous
  readers; organic search landings on "transfer dive log from [brand]" content
  pages that link to the tool (write these articles — the feature is also an
  SEO magnet).
- *(Account-creation metrics from the original draft move to Phase 2.)*

## 13. Open questions — resolved 2026-07-15

1. **Samples inline vs separate table** → inline on the dive record (IndexedDB
   equivalent of the JSONB call; ~360 points/dive is trivial).
2. **Does DiveSZN already have auth/accounts?** → No; the site is static with
   no backend. Owner chose client-side v1; accounts/sync deferred to Phase 2.
3. **Supabase region** → deferred with Phase 2 (EU — Frankfurt/London — when it
   happens).

## 14. Build order (single-session plan, adapted)

Work one step at a time, commit after each working increment, verify the app
runs before and after (per repo build discipline). All work on branch
`claude/dive-log-import-yc69au`; merge to `main` only on explicit owner
instruction (repo working agreement).

1. **Foundations** — this PRD; vendored XML parser; `lib/divelog/` core
   (types, hardened XML shim, store interface + IndexedDB/Memory stores,
   dedupe, pipeline, units); unit tests. Update CLAUDE.md at the end.
2. **Canonical model + UDDF** — UDDF parser + UDDF exporter, fixtures,
   round-trip test. (Building import and export of the canonical format first
   means every later parser can be validated by exporting what it parsed.)
3. **Subsurface XML parser** + duplicate detection tests.
4. **CSV with column mapping.**
5. **Suunto SML.**
6. **Pipeline + UI** — `divelog.html`, upload/preview/commit flow, dive list +
   detail + profile chart, manual add/edit/delete, UDDF export, unit toggle.
7. **Hardening pass** — hostile fixtures, mobile, empty states; adversarial
   review; browser verification. Ship v1 (= push branch; owner merges).

Later: Garmin FIT (with Suunto-FIT vendor branching), Shearwater XML, DL7 —
one parser per increment, each starting from Subsurface's reference
implementation for that format.

## 15. Analysis — deviations from the original "Fathom" draft, and why

The original draft was written for a product ("Fathom") assumed to be an
existing Next.js 15 / React 19 app on Vercel. DiveSZN is not that: it is a
fully static site served by GitHub Pages (`index.html` + generated pages +
Python build scripts; CLAUDE.md: "No backend"). Beyond the name swap, that
mismatch forces the following changes — **decided with the owner on
2026-07-15 (client-side, static-first chosen over scaffolding the full
Next.js/Supabase stack):**

| # | Original draft | DiveSZN v1 | Why |
|---|---|---|---|
| 1 | Next.js 15 app, Vercel serverless routes | Static page + ES modules on GitHub Pages | The Next.js app doesn't exist; GitHub Pages can't host serverless routes; Vercel/Supabase/OAuth accounts would need owner-created services before anything could deploy. Client-side v1 ships the day it merges. |
| 2 | Auth.js accounts, feature requires login | No login; anonymous, device-local logbook | No auth exists on the site. Requiring accounts requires a backend. The conversion goal (readers → registered users) moves to Phase 2; v1 still creates the return-visit habit. |
| 3 | Supabase Postgres (`dives`, `imports`, `dive_sites` tables) | IndexedDB behind the same thin store interface | Same "swappable store" principle the draft mandated — the swap target changed. Parsers, dedupe, pipeline and UI never touch the store directly, so Phase 2 replaces one module. |
| 4 | Store originals in Supabase Storage for re-parsing | Not stored (nothing leaves the browser) | No storage service. Mitigation: UDDF export is the durable copy; re-import is cheap. |
| 5 | Parsers in TypeScript | Plain ES modules + JSDoc types | The repo has no npm/build toolchain (it's Python + static files). Adding one for this feature would break the "maintainable by one person, no build step" property of the site. Contracts are documented as JSDoc typedefs. |
| 6 | Recharts for depth profiles | Hand-rolled inline SVG chart | Recharts requires React; the site has none. SVG keeps zero dependencies and matches the brand's monospace data-readout style. |
| 7 | Server-side size limits & validation | Same limits enforced at the browser parse boundary | There is no server; the threat model shifts from "protect the server" to "protect the user's logbook + browser session" — XXE/DTD rejection, size caps and time-boxing still apply and are tested. |
| 8 | `/api/divelog/export` UDDF endpoint | Client-generated UDDF file download | Same deliverable, no endpoint needed. |
| 9 | GDPR: account deletion removes rows + files | "Delete all my dives" wipes IndexedDB; no server data at all | Strictly stronger privacy position; also simpler to state honestly in site copy. |
| 10 | 6-session build plan | Single-session plan (§14) with the same increments and commit discipline | Executed by Claude Code on the feature branch. |

**What survives unchanged (the durable core):** the canonical UDDF-shaped
model, the parser-module contract and registry with content sniffing, the
per-file salvage rule, duplicate-detection thresholds, the import
upload→preview→commit UX, UDDF export + round-trip test, the hostile-fixture
test suite, and the format roadmap. If/when Phase 2 adds accounts + Supabase,
the parsers and pipeline move server-side (or stay client-side feeding a
synced store) without rewrites — exactly the modularity the original draft
asked for.

**Editorial-fit notes (DiveSZN CLAUDE.md rules):** page copy stays scuba-only
(the `diveType` field still records what files contain); no third-party names
in *site copy* — brand names live in the importer UI only as format labels
("Suunto DM5 (SML)"), which is product labelling, not editorial copy; prices/
coral-CTA rules don't apply (no commerce on this page); tonal palette and
light theme apply to the new page.
