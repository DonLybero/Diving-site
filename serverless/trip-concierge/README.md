# Trip Concierge worker (optional AI layer)

The Trip Planner works entirely without a backend: the survey, itinerary,
season logic and booking links are all client-side. This worker adds one
optional extra — a short, personalised "Concierge notes" panel written by the
Claude API — and the site degrades gracefully whenever it is absent, slow or
over budget.

## What it costs
Each plan generates one Claude API call (~700 output tokens). On the default
model (Haiku) that is a fraction of a cent per plan; switch `MODEL` to a
Sonnet model for richer prose at a higher rate. You pay Anthropic directly
through your API key; Cloudflare's free Workers tier covers the hosting.

## Deploy (once)
1. Install wrangler and log in: `npm i -g wrangler && wrangler login`
2. From this folder:
   ```bash
   wrangler secret put ANTHROPIC_API_KEY   # paste your key from console.anthropic.com
   wrangler deploy                          # prints https://diveszn-trip-concierge.<you>.workers.dev
   ```
3. Paste the printed URL into `TRIP_AI.endpoint` in `index.html`
   (search for `var TRIP_AI`), rebuild the standalone
   (`python3 scripts/build_standalone.py`) and push.

## Protecting the endpoint
- `ALLOWED_ORIGIN` in `wrangler.toml` restricts CORS to the site.
- The worker has a soft per-IP limit (6 plans/minute), but for a real
  ceiling add a **rate-limiting rule** on the workers.dev route in the
  Cloudflare dashboard (Security → WAF → Rate limiting rules) — that is the
  layer that actually caps your API spend.
- Rotate the API key from console.anthropic.com if it ever leaks; the key
  lives only as a Worker secret, never in the repo.

## Request / response contract
`POST /` with the survey JSON the site sends (origin, adults, start,
prefs, legs[]) → `200 {"text": "…paragraphs…"}`. Any non-200 makes the
site silently drop the panel.
