// Canonical dive model (UDDF-shaped) + validation. All values metric:
// metres, °C, bar, litres, seconds. Display conversion lives in units.js.
// Contract details: docs/divelog-prd.md §6–§7.

/**
 * @typedef {Object} DiveSample
 * @property {number} tSec         seconds since dive start
 * @property {number} depthM
 * @property {number} [tempC]
 * @property {number} [pressureBar]
 *
 * @typedef {Object} DiveTank
 * @property {number} [volumeL]
 * @property {number} [startBar]
 * @property {number} [endBar]
 * @property {number} [gasO2Pct]   21 = air
 * @property {number} [gasHePct]
 *
 * @typedef {Object} DiveSite
 * @property {string} name
 * @property {number} [lat]
 * @property {number} [lon]
 * @property {string} [country]
 *
 * @typedef {Object} DiveSource
 * @property {string} [importId]
 * @property {string} [parserId]
 * @property {string} [computerModel]
 * @property {string} [externalId]
 *
 * @typedef {Object} CanonicalDive
 * @property {string} [id]         assigned at commit
 * @property {number} [number]     diver's own sequence number, editable
 * @property {string} startedAt    ISO 8601; offset kept when the source had one,
 *                                 otherwise naive local time (no suffix)
 * @property {number} durationSec
 * @property {number} [maxDepthM]
 * @property {number} [avgDepthM]
 * @property {number} [waterTempC]
 * @property {number} [airTempC]
 * @property {DiveSite} [site]
 * @property {string} [buddy]
 * @property {string} [diveMaster]
 * @property {string} [notes]
 * @property {DiveTank[]} [tanks]
 * @property {string} [equipment]  free text v1
 * @property {'scuba'|'freedive'|'other'} diveType
 * @property {'private'|'public'} visibility
 * @property {DiveSource} [source]
 * @property {DiveSample[]} [samples]
 *
 * @typedef {Object} ParseResult
 * @property {CanonicalDive[]} dives
 * @property {string[]} warnings  per-dive salvage notes ("dive 12: no temperature")
 * @property {string[]} errors    file-level failures
 *
 * @typedef {Object} ParserModule
 * @property {string} id
 * @property {string} displayName
 * @property {string[]} extensions             lowercase, with dot
 * @property {(bytes: Uint8Array, text: string) => boolean} sniff
 * @property {(bytes: Uint8Array, text: string, options?: Object) => ParseResult} parse  never throws
 */

export const DIVE_TYPES = ['scuba', 'freedive', 'other'];

export const LIMITS = {
  maxFileBytes: 20 * 1024 * 1024,
  maxDivesPerFile: 5000,
  maxSamplesPerDive: 100000,
  maxTanksPerDive: 10,
  maxStringLen: 20000,
};

/** @returns {ParseResult} */
export function makeParseResult() {
  return { dives: [], warnings: [], errors: [] };
}

const fin = (v) => typeof v === 'number' && Number.isFinite(v);

function clampStr(v) {
  if (v === undefined || v === null) return undefined;
  // strip XML-illegal control characters (keep \t \n \r) so stored text
  // always survives the UDDF export as well-formed XML
  const s = String(v).replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/g, '').trim();
  if (!s) return undefined;
  return s.length > LIMITS.maxStringLen ? s.slice(0, LIMITS.maxStringLen) : s;
}

function round2(v) { return Math.round(v * 100) / 100; }

/**
 * Normalize + validate one parsed dive. Never throws.
 * @param {Partial<CanonicalDive>} raw
 * @returns {{dive: CanonicalDive|null, problems: string[]}}
 *   dive is null only when the record is unusable (no valid start time).
 */
export function validateDive(raw) {
  const problems = [];
  if (!raw || typeof raw !== 'object') return { dive: null, problems: ['not a dive record'] };

  const startedAt = clampStr(raw.startedAt);
  if (!startedAt || Number.isNaN(new Date(startedAt).getTime())) {
    return { dive: null, problems: ['missing or invalid date/time'] };
  }

  /** @type {CanonicalDive} */
  const dive = {
    startedAt,
    durationSec: 0,
    diveType: DIVE_TYPES.includes(raw.diveType) ? raw.diveType : 'scuba',
    visibility: raw.visibility === 'public' ? 'public' : 'private',
  };
  if (raw.id) dive.id = String(raw.id);
  if (fin(raw.number) && raw.number > 0) dive.number = Math.round(raw.number);

  // samples first — duration and max depth can be derived from them
  let samples;
  if (Array.isArray(raw.samples) && raw.samples.length) {
    const plausible = raw.samples.filter((s) => s && fin(s.tSec) && s.tSec >= 0 && fin(s.depthM));
    samples = plausible.filter((s) => s.tSec <= 48 * 3600);
    if (samples.length < plausible.length) problems.push('samples beyond 48 h dropped as implausible');
    samples = samples
      .map((s) => {
        const out = { tSec: Math.round(s.tSec), depthM: round2(Math.max(0, s.depthM)) };
        if (fin(s.tempC)) out.tempC = round2(s.tempC);
        if (fin(s.pressureBar) && s.pressureBar >= 0) out.pressureBar = round2(s.pressureBar);
        return out;
      })
      .sort((a, b) => a.tSec - b.tSec);
    if (samples.length > LIMITS.maxSamplesPerDive) {
      problems.push(`profile truncated to ${LIMITS.maxSamplesPerDive} samples`);
      samples = samples.slice(0, LIMITS.maxSamplesPerDive);
    }
    if (samples.length) dive.samples = samples;
  }

  if (fin(raw.durationSec) && raw.durationSec > 0) {
    dive.durationSec = Math.round(raw.durationSec);
  } else if (dive.samples) {
    dive.durationSec = dive.samples[dive.samples.length - 1].tSec;
    problems.push('duration taken from profile samples');
  } else {
    problems.push('no duration in source');
  }

  if (fin(raw.maxDepthM) && raw.maxDepthM >= 0) {
    dive.maxDepthM = round2(raw.maxDepthM);
  } else if (dive.samples) {
    dive.maxDepthM = round2(Math.max(...dive.samples.map((s) => s.depthM)));
    problems.push('max depth taken from profile samples');
  } else {
    problems.push('no max depth in source');
  }
  if (fin(raw.avgDepthM) && raw.avgDepthM >= 0) dive.avgDepthM = round2(raw.avgDepthM);
  if (dive.avgDepthM !== undefined && dive.maxDepthM !== undefined && dive.avgDepthM > dive.maxDepthM) {
    problems.push('average depth exceeds max depth — dropped');
    delete dive.avgDepthM;
  }
  if (fin(raw.waterTempC) && raw.waterTempC > -10 && raw.waterTempC < 60) dive.waterTempC = round2(raw.waterTempC);
  if (fin(raw.airTempC) && raw.airTempC > -60 && raw.airTempC < 70) dive.airTempC = round2(raw.airTempC);
  if (dive.maxDepthM !== undefined && dive.maxDepthM > 350) problems.push(`implausible max depth ${dive.maxDepthM} m`);

  if (raw.site && clampStr(raw.site.name)) {
    const site = { name: clampStr(raw.site.name) };
    if (fin(raw.site.lat) && Math.abs(raw.site.lat) <= 90 && fin(raw.site.lon) && Math.abs(raw.site.lon) <= 180) {
      site.lat = raw.site.lat;
      site.lon = raw.site.lon;
    }
    if (clampStr(raw.site.country)) site.country = clampStr(raw.site.country);
    dive.site = site;
  }

  for (const k of ['buddy', 'diveMaster', 'notes', 'equipment']) {
    const v = clampStr(raw[k]);
    if (v) dive[k] = v;
  }

  if (Array.isArray(raw.tanks) && raw.tanks.length) {
    const tanks = raw.tanks
      .filter((t) => t && (fin(t.volumeL) || fin(t.startBar) || fin(t.endBar) || fin(t.gasO2Pct) || fin(t.gasHePct)))
      .slice(0, LIMITS.maxTanksPerDive)
      .map((t) => {
        const out = {};
        if (fin(t.volumeL) && t.volumeL > 0 && t.volumeL < 100) out.volumeL = round2(t.volumeL);
        if (fin(t.startBar) && t.startBar >= 0 && t.startBar < 500) out.startBar = round2(t.startBar);
        if (fin(t.endBar) && t.endBar >= 0 && t.endBar < 500) out.endBar = round2(t.endBar);
        if (fin(t.gasO2Pct) && t.gasO2Pct > 0 && t.gasO2Pct <= 100) out.gasO2Pct = round2(t.gasO2Pct);
        if (fin(t.gasHePct) && t.gasHePct > 0 && t.gasHePct <= 100) out.gasHePct = round2(t.gasHePct);
        return out;
      })
      .filter((t) => Object.keys(t).length);
    if (tanks.length) dive.tanks = tanks;
  }

  if (raw.source && typeof raw.source === 'object') {
    const src = {};
    for (const k of ['importId', 'parserId', 'computerModel', 'externalId']) {
      const v = clampStr(raw.source[k]);
      if (v) src[k] = v;
    }
    if (Object.keys(src).length) dive.source = src;
  }

  return { dive, problems };
}
