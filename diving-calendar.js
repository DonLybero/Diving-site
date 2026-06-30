/*
 * diving-calendar.js — scoring + query engine for the World Diving Calendar.
 *
 * Works in the browser (attaches `window.DivingCalendar`) and in Node
 * (`module.exports`). Pure functions — pass in the destinations array loaded
 * from diving-destinations.json.
 *
 * Scoring (keep in sync with build_rankings.py):
 *   score = ratingBase + min(sum(matched marine weights), BONUS_CAP)
 *   'Closed' months are excluded from rankings.
 */
(function (root) {
  "use strict";

  var MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

  // 24 bi-monthly periods (each month split into early/late halves).
  var PERIODS = [];
  for (var mi = 0; mi < MONTHS.length; mi++) {
    PERIODS.push({ period_no: mi * 2 + 1, month: MONTHS[mi], half: "early", label: MONTHS[mi] + " (early)" });
    PERIODS.push({ period_no: mi * 2 + 2, month: MONTHS[mi], half: "late",  label: MONTHS[mi] + " (late)"  });
  }

  var RATING_BASE = { Peak: 100, Good: 72, Shoulder: 48, Low: 22, Closed: null };
  var BONUS_CAP = 25;
  var COMFORT_TARGET = 27; // deg C, tie-breaker only

  // Headline marine-life keywords -> bonus weight (presence-based, once each).
  var MARINE_WEIGHTS = [
    ["whale shark", 12], ["sardine run", 12],
    ["hammerhead", 10],
    ["manta", 9], ["minke", 9], ["tiger shark", 9],
    ["thresher", 9], ["oceanic whitetip", 9],
    ["mola", 8], ["mobula", 8], ["wall of shark", 8], ["shark wall", 8],
    ["humpback", 7], ["devil ray", 7], ["bull shark", 7],
    ["grouper spawn", 7], ["coral spawn", 7],
    ["barracuda tornado", 6], ["spawning", 6],
    ["sea lion", 5], ["aggregation", 5],
    ["grey reef shark", 4], ["silvertip", 4], ["turtle nesting", 4],
    ["dolphin", 3], ["nesting", 3],
    ["reef shark", 2], ["eagle ray", 2], ["seahorse", 2],
    ["frogfish", 2], ["mandarinfish", 2]
  ];

  function marineBonus(text) {
    var t = (text || "").toLowerCase();
    var total = 0;
    for (var i = 0; i < MARINE_WEIGHTS.length; i++) {
      if (t.indexOf(MARINE_WEIGHTS[i][0]) !== -1) total += MARINE_WEIGHTS[i][1];
    }
    return Math.min(total, BONUS_CAP);
  }

  // Resolve a month name or 1..24 period number to {month, half, label}.
  function resolvePeriod(p) {
    if (typeof p === "number") return PERIODS[(p - 1 + 24) % 24];
    for (var i = 0; i < MONTHS.length; i++) if (MONTHS[i] === p) return { month: p, half: "", label: p };
    // accept "Aug (early)" style
    var m = String(p).slice(0, 3);
    for (var j = 0; j < MONTHS.length; j++) if (MONTHS[j] === m) return { month: m, half: "", label: p };
    return null;
  }

  // Score one destination for one month. Returns null if Closed.
  function scoreMonth(dest, month) {
    var mm = dest.monthly[month];
    if (!mm) return null;
    var base = RATING_BASE[mm.rating];
    if (base === null || base === undefined) return null; // Closed
    return base + marineBonus(mm.marine_life);
  }

  function matchFilters(dest, month, f) {
    if (!f) return true;
    if (f.region && dest.region.toLowerCase().indexOf(f.region.toLowerCase()) === -1) return false;
    if (f.difficulty && dest.difficulty.toLowerCase().indexOf(f.difficulty.toLowerCase()) === -1) return false;
    if (f.water_type && dest.water_type.toLowerCase().indexOf(f.water_type.toLowerCase()) === -1) return false;
    if (f.access && dest.access.toLowerCase().indexOf(f.access.toLowerCase()) === -1) return false;
    var temp = dest.monthly_temp_c[month];
    if (f.minTemp != null && temp != null && temp < f.minTemp) return false;
    if (f.maxTemp != null && temp != null && temp > f.maxTemp) return false;
    return true;
  }

  /* Rank destinations for a period (month name or 1..24). Returns a sorted
     array of result objects, best first. filters is optional. */
  function rankPeriod(destinations, period, filters) {
    var rp = resolvePeriod(period);
    if (!rp) return [];
    var month = rp.month;
    var out = [];
    for (var i = 0; i < destinations.length; i++) {
      var d = destinations[i];
      var s = scoreMonth(d, month);
      if (s === null) continue;                 // Closed -> excluded
      if (!matchFilters(d, month, filters)) continue;
      out.push({
        name: d.name, country: d.country, region: d.region,
        difficulty: d.difficulty, access: d.access, wetsuit: d.wetsuit,
        water_temp_c: d.monthly_temp_c[month],
        rating: d.monthly[month].rating,
        highlight: d.monthly[month].marine_life,
        conditions: d.monthly[month].conditions,
        score: s
      });
    }
    out.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      var ca = Math.abs((a.water_temp_c == null ? 99 : a.water_temp_c) - COMFORT_TARGET);
      var cb = Math.abs((b.water_temp_c == null ? 99 : b.water_temp_c) - COMFORT_TARGET);
      if (ca !== cb) return ca - cb;
      return a.name < b.name ? -1 : 1;
    });
    for (var r = 0; r < out.length; r++) out[r].rank = r + 1;
    if (filters && filters.limit) return out.slice(0, filters.limit);
    return out;
  }

  /* Exact-ish destination lookup by name (case-insensitive, trims). */
  function getDestination(destinations, name) {
    if (!name) return null;
    var q = String(name).trim().toLowerCase();
    for (var i = 0; i < destinations.length; i++) {
      if (destinations[i].name.toLowerCase() === q) return destinations[i];
    }
    // fall back to startsWith / includes
    for (var j = 0; j < destinations.length; j++) {
      if (destinations[j].name.toLowerCase().indexOf(q) !== -1) return destinations[j];
    }
    return null;
  }

  /* Fuzzy search across name, country, region and signature species.
     Returns destinations ranked by match relevance. */
  function searchDestinations(destinations, query) {
    var q = String(query || "").trim().toLowerCase();
    if (!q) return [];
    var scored = [];
    for (var i = 0; i < destinations.length; i++) {
      var d = destinations[i], s = 0;
      var name = d.name.toLowerCase();
      if (name === q) s += 100;
      else if (name.indexOf(q) === 0) s += 60;
      else if (name.indexOf(q) !== -1) s += 40;
      if (d.country.toLowerCase().indexOf(q) !== -1) s += 20;
      if (d.region.toLowerCase().indexOf(q) !== -1) s += 15;
      if ((d.highlights || "").toLowerCase().indexOf(q) !== -1) s += 10;
      var sp = (d.signature_species || []).join(", ").toLowerCase();
      if (sp.indexOf(q) !== -1) s += 12;
      if (s > 0) scored.push({ dest: d, score: s });
    }
    scored.sort(function (a, b) { return b.score - a.score || (a.dest.name < b.dest.name ? -1 : 1); });
    return scored.map(function (x) { return x.dest; });
  }

  /* Per-destination season summary: which months are Peak/Good/etc + best score period. */
  function destinationSeasonSummary(dest) {
    var byRating = { Peak: [], Good: [], Shoulder: [], Low: [], Closed: [] };
    var best = null;
    for (var i = 0; i < MONTHS.length; i++) {
      var m = MONTHS[i], rating = dest.monthly[m].rating;
      if (byRating[rating]) byRating[rating].push(m);
      var s = scoreMonth(dest, m);
      if (s !== null && (best === null || s > best.score)) best = { month: m, score: s };
    }
    return { byRating: byRating, bestMonth: best };
  }

  var api = {
    MONTHS: MONTHS, PERIODS: PERIODS,
    RATING_BASE: RATING_BASE, MARINE_WEIGHTS: MARINE_WEIGHTS, BONUS_CAP: BONUS_CAP,
    marineBonus: marineBonus, scoreMonth: scoreMonth, resolvePeriod: resolvePeriod,
    rankPeriod: rankPeriod, getDestination: getDestination,
    searchDestinations: searchDestinations, destinationSeasonSummary: destinationSeasonSummary
  };

  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.DivingCalendar = api;
})(typeof self !== "undefined" ? self : this);
