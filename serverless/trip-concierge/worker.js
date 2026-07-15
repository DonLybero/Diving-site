/* DiveSZN Trip Concierge — Cloudflare Worker
 *
 * Receives the Trip Planner survey (origin, dates, legs, preferences) and
 * returns short personal itinerary notes written by the Claude API.
 * The static site works fully without this worker; when TRIP_AI.endpoint in
 * index.html points here, a "Concierge notes" panel appears on the plan.
 *
 * Deploy (see README.md):
 *   wrangler secret put ANTHROPIC_API_KEY
 *   wrangler deploy
 *
 * Env vars (wrangler.toml):
 *   ALLOWED_ORIGIN  e.g. "https://donlybero.github.io"  (CORS allow-list)
 *   MODEL           optional, defaults to claude-haiku-4-5-20251001
 */

const DEFAULT_MODEL = 'claude-haiku-4-5-20251001';
const MAX_LEGS = 8;

// per-isolate soft limiter: not a security boundary, just a cost brake.
// For real protection add a Cloudflare WAF rate-limiting rule on this route.
const hits = new Map();
function rateLimited(ip) {
  const now = Date.now();
  const rec = hits.get(ip) || { n: 0, t: now };
  if (now - rec.t > 60_000) { rec.n = 0; rec.t = now; }
  rec.n++;
  hits.set(ip, rec);
  return rec.n > 6; // 6 plans/minute/IP
}

function cors(env) {
  return {
    'Access-Control-Allow-Origin': env.ALLOWED_ORIGIN || '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

function bad(status, msg, env) {
  return new Response(JSON.stringify({ error: msg }), {
    status, headers: { 'Content-Type': 'application/json', ...cors(env) },
  });
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS')
      return new Response(null, { status: 204, headers: cors(env) });
    if (request.method !== 'POST') return bad(405, 'POST only', env);

    const origin = request.headers.get('Origin') || '';
    if (env.ALLOWED_ORIGIN && origin && origin !== env.ALLOWED_ORIGIN)
      return bad(403, 'origin not allowed', env);

    const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
    if (rateLimited(ip)) return bad(429, 'slow down', env);

    let survey;
    try { survey = await request.json(); } catch { return bad(400, 'invalid JSON', env); }
    const legs = Array.isArray(survey.legs) ? survey.legs.slice(0, MAX_LEGS) : [];
    if (!legs.length) return bad(400, 'no legs', env);

    // Only pass through the fields the prompt needs — never echo raw input.
    const clean = {
      origin: survey.origin && String(survey.origin.city || survey.origin.iata || '').slice(0, 60),
      adults: Math.min(9, Math.max(1, Number(survey.adults) || 1)),
      start: String(survey.start || '').slice(0, 10),
      pace: ['light', 'balanced', 'max'].includes(survey.prefs && survey.prefs.pace) ? survey.prefs.pace : 'balanced',
      interests: ((survey.prefs && survey.prefs.tags) || []).slice(0, 9).map(t => String(t).slice(0, 20)),
      legs: legs.map(l => ({
        name: String(l.name || '').slice(0, 60),
        nights: Math.min(30, Math.max(1, Number(l.nights) || 1)),
        arrive: String(l.arrive || '').slice(0, 10),
        depart: String(l.depart || '').slice(0, 10),
        rating: String(l.rating || '').slice(0, 12),
      })),
    };

    const system = [
      'You write short, useful trip notes for DiveSZN, a scuba trip-planning site.',
      'Style rules (non-negotiable): no clichés (never "paradise", "gem", "bucket list", "breathtaking", "stunning", "world-class", "nestled", "boasts"); ',
      'never name dive-certification agencies, tour operators, magazines or booking platforms; scuba only, never pitch snorkelling or freediving as the trip; ',
      'concrete nouns and numbers over adjectives; metric units; straight apostrophes.',
      'Safety: never suggest diving on the traveller\'s last day before a flight; respect the season rating you are given (a Low/Closed month deserves an honest caveat).',
      'Output: plain text, 2-4 short paragraphs total, no markdown, no headings, no lists. Speak to the traveller as "you".',
    ].join(' ');

    const user = 'Write personal concierge notes for this dive trip. Focus on pacing advice, what to book early, month-specific caveats, and one insider suggestion per destination. Trip: '
      + JSON.stringify(clean);

    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        model: env.MODEL || DEFAULT_MODEL,
        max_tokens: 700,
        system,
        messages: [{ role: 'user', content: user }],
      }),
    });

    if (!resp.ok) return bad(502, 'model unavailable', env);
    const data = await resp.json();
    const text = (data.content || []).filter(b => b.type === 'text').map(b => b.text).join('\n\n');

    return new Response(JSON.stringify({ text }), {
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store',
        ...cors(env),
      },
    });
  },
};
