# DiveSZN — homepage redesign concept

An interactive, animated concept for the DiveSZN homepage. **Not merged to
`main`** and not part of the deployed site — it lives only here on the
`claude/website-redesign-ai-agents-fmwv9t` branch and as a private hosted
preview.

## What it is

A single-file, self-contained redesign of the homepage built around the
product's core promise — *know when to dive where*:

- **Animated ocean hero** — a generative Canvas caustics / light-shaft /
  bubble field (pure code, no photos), with a live "in season now" panel that
  ranks the best destinations for the current real-world month.
- **Month scrubber planner** — pick any month and destinations re-rank live by
  the real season score (rating base + visibility bonus + marine-life bonus).
- **Flagship destinations** — cards with the canonical 12-bar tonal season
  calendar and an on-hover water-temp / visibility read-out.
- **Marine-life encounter pulse** — scrub the year to see when each species is
  most reliably in the water.
- **Scuba gear guides**, **how-we-score** trust band, and a footer link tree.
- A right-edge **depth gauge** tracks the scroll as a descent through the water
  column, all within the brand's light/white identity and tonal palette.

Everything honours the brand system and the non-negotiable editorial rules
(scuba-only, no banned vocabulary, tonal rating palette, no prices on the
homepage, coral reserved for buy/booking CTAs). Fully responsive and
reduced-motion aware.

## How it was built

A small "studio team" of agents: a creative director (motion / scroll
choreography), a copywriter (all homepage copy under the editorial rules), the
build (this file), then a QA pass (brand + editorial compliance, and
accessibility + responsive + reduced-motion).

## Files

- **`index.html`** — the full standalone page (open directly or serve). Real
  destination / season data is inlined, so it works over `file://` too.
- **`artifact.html`** — the same page as body-only content for the hosted
  private preview (CSP-safe: all CSS/JS inline, generated visuals only). Derived
  from `index.html` — regenerate by copying everything between `<body>…</body>`
  and prefixing a `<title>`.

## View locally

```bash
python3 -m http.server        # then open http://localhost:8000/redesign/
```

Or just open `redesign/index.html` in a browser.
