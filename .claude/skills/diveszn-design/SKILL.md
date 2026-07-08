---
name: diveszn-design
description: DiveSZN's design system, brand rules, editorial voice and QA workflow. Use whenever changing the look, layout, copy, imagery or interactions of index.html, the static pages (scripts/build_pages.py) or any new page — before writing the first line of CSS/HTML/copy.
---

# DiveSZN design system

DiveSZN is a seasonal dive-trip planner and dive hub. Every visual and copy
decision should feel like a confident, research-driven dive publication —
light, precise, a little nautical — never like a generic AI-generated travel
template. `HANDOFF.md` holds the full project map; this skill is the design
contract.

## Brand

- Name **DiveSZN** ("dive season"). Wordmark: `Dive<b>SZN</b>`. Logo is a
  whale **fluke** — never helmets, bubbles-in-circles or generic waves.
- **Light/white theme.** Teal ink (`--ink` deep blue-green) for text, teal
  accents for interaction. **Coral is reserved strictly for buy/booking CTAs**
  (buttons and booking links). Prices are NOT coral (owner ruling, July 2026):
  set them as quiet data — ink mono with tabular numerals (`.score`); a
  best-price flag may use `--accent-deep`, never coral.
- Serif display faces for headings, monospace for data readouts (temps, viz,
  scores, kickers, uppercase micro-labels with letter-spacing), sans for body.
  This three-voice typography IS the brand — keep the roles pure.
- The header is brand-only (the owner removed the ad slot in July 2026); keep
  it slim and don't reintroduce ad placements without an owner decision.

## Layout & component language

- Rounded 12–14px cards on white or very light teal-tinted gradients
  (`linear-gradient(165deg,#ffffff,#f2f9f9)`), 1px `var(--line)` borders,
  soft glow shadows on hover. No hard drop shadows, no dark panels.
- Data chips (Peak/water °C/viz/current) are monospace pills; rating colors:
  Peak green, Good blue, Shoulder amber, Low/Closed muted. Never invent new
  rating colors.
- Season ribbons (12 month cells) and score bars visualize numbers — prefer
  adding to these existing devices over introducing new chart types.
- Photos: `object-fit:cover` in rounded containers with the photographer
  credit in monospace small print. Every destination/marine image must carry
  its credit.
- Icons are the inline SVG set in index.html (`ico(name,size)` / `data-ico`);
  extend that set rather than importing icon fonts or emoji.
- Mobile: single column at ~390px; tables scroll horizontally inside their
  container; tap targets ≥40px. Hover-only affordances must have a tap
  equivalent.

## Editorial voice (owner-mandated, non-negotiable)

- **Scuba only.** Never write snorkelling/freediving/glass-bottom copy except
  in the explicitly labelled "beyond scuba" marine-life sections.
- **Never name third parties** in site copy: no PADI/SSI, magazines, testers,
  photographers, brands-as-endorsement. (Gear product names and retailer
  names in the gear guide are the only exception.)
- No aphorism or cliché intros. Banned vocabulary: nestled, boasts, paradise,
  gem, bucket list, breathtaking, stunning, world-class, mecca, "like nowhere
  else", "diver's playground", "whether you're a beginner or…".
- Taglines never cite destination counts. Specs never say "Both" — spell the
  options out.
- Prose is concrete and grounded in the destination's own data (dive sites,
  species, temps, currents). If the data is thin, write shorter — never
  invent a site, species or number. Straight apostrophes, metric units
  ("30 m", "26°C").

## Data & engine constraints

- `diving-destinations.json` is canonical. Editorial fields (`description`,
  `underwater`, `encounters`) are free text; the `monthly` strings feed the
  scoring engine — **changing wording there can change scores.** The scoring
  formula must stay identical in `diving-calendar.js` and
  `scripts/build_rankings.py`; after any monthly-string edit, rebuild
  rankings and confirm a zero diff unless a scoring change is intended.
- After editing `index.html` or data: run `python3 scripts/build_pages.py`
  and `python3 scripts/build_standalone.py` so the static pages and the
  single-file build stay in sync. `scripts/build_master.py` preserves baked
  images and editorial fields — keep it that way when touching it.

## Imagery standard

- Sources are Wikimedia Commons via `scripts/fetch_images.py` /
  `fetch_marine_images.py`. Owner-approved picks are **pinned**
  (`DEST_PINNED`/`PINNED`) — never replace a pinned photo without an owner
  review. New photos must survive the BAD_HINT/REQUIRE/BLOCK filters, and
  block patterns must match spaces AND underscores (`[_ ]`).
- Use baked image URLs exactly as stored — Wikimedia rejects rewritten thumb
  widths (requests get ORB-blocked). Lazy-load anything below the fold.
- The bar: a photo must look like *diving at that destination* — no maps,
  scans, museum specimens, dead catch, captive animals, watermarks, pools or
  unrelated landmarks. When in doubt, run the owner A/B/C review flow
  (`scripts/photo_candidates.py` → contact sheets → owner picks → pin).

## Making it feel alive (apply with restraint)

- Transitions 150–250ms ease on hover/expand; hover states change border +
  glow, not size jumps that reflow layout.
- One orchestrated moment per view beats scattered effects. Prefer purposeful
  reveals (e.g. filter change smooth-scrolls to results) over decorative
  animation; skip anything that reads as AI-generated flourish.
- Empty and loading states must not flash broken images — placeholders keep
  the tinted background; `onerror` hides only the `<img>`.

## Verification (required before merge)

- Serve locally (`python3 -m http.server`) — `index.html` needs HTTP, not
  `file://`. Validate inline JS per `<script>` block (node vm) and JSON-LD
  separately.
- Local Chromium is unreliable in the dev sandbox: dispatch
  `.github/workflows/ui-audit.yml` and review the pushed screenshots on the
  `ui-audit` orphan branch at BOTH 1280px and 390px. The audit logs failed
  image requests — check them when adding imagery.
- Every finished change merges to `main` (auto-deploys via
  `deploy-pages.yml`); confirm the run is green.
