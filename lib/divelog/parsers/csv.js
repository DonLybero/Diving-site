// Generic CSV dive-log parser (PRD §5 P0): auto-maps common column layouts
// (Subsurface summary + profile exports, Diving Log, MacDive, hand-rolled
// spreadsheets) and accepts an explicit mapping from the column-mapping UI.
// Conventions verified against Subsurface's importer: delimiter = most
// frequent of TAB , ; | in the header; ';' files pair with decimal commas;
// units live in header markers ('[m]', '(ft)', '[psi]'); 'duration [min]'
// actually holds MM:SS; header normalization folds O₂→o2 and strips markers.
//
// The mapping UI talks to this module via csvIntrospect() (headers + auto-map
// + preview rows) and passes its result back as options.mapping. A parse that
// can't find the required fields returns the NEEDS_MAPPING error marker.

import { makeParseResult } from '../types.js';
import { num, parseDuration, parseDateTime } from '../values.js';

export const NEEDS_MAPPING = 'needs-mapping';

/** Fields a CSV column can map to (drives the mapping UI). */
export const CSV_FIELDS = [
  { key: 'number', label: 'Dive number' },
  { key: 'date', label: 'Date' },
  { key: 'time', label: 'Start time' },
  { key: 'datetime', label: 'Date & time (combined)' },
  { key: 'duration', label: 'Duration' },
  { key: 'maxDepth', label: 'Max depth' },
  { key: 'avgDepth', label: 'Avg depth' },
  { key: 'waterTemp', label: 'Water temp' },
  { key: 'airTemp', label: 'Air temp' },
  { key: 'site', label: 'Dive site' },
  { key: 'gps', label: 'GPS (lat lon)' },
  { key: 'lat', label: 'Latitude' },
  { key: 'lon', label: 'Longitude' },
  { key: 'buddy', label: 'Buddy' },
  { key: 'diveMaster', label: 'Divemaster / guide' },
  { key: 'notes', label: 'Notes' },
  { key: 'equipment', label: 'Suit / equipment' },
  { key: 'tankSize', label: 'Tank size' },
  { key: 'startPressure', label: 'Start pressure' },
  { key: 'endPressure', label: 'End pressure' },
  { key: 'o2', label: 'O₂ % / gas mix' },
  { key: 'he', label: 'He %' },
  { key: 'sampleTime', label: 'Profile: sample time' },
  { key: 'sampleDepth', label: 'Profile: sample depth' },
  { key: 'sampleTemp', label: 'Profile: sample temp' },
  { key: 'samplePressure', label: 'Profile: sample pressure' },
  { key: 'ignore', label: '— ignore —' },
];

// alias → field, keyed by normalized header text
const ALIASES = new Map();
function alias(field, names) {
  for (const n of names) ALIASES.set(normHeader(n), field);
}

/** Lowercase, fold ₂→2, strip [unit]/(unit) markers, dots, underscores. */
export function normHeader(h) {
  return String(h || '')
    .replace(/^﻿/, '')
    .replace(/₂/g, '2')
    .toLowerCase()
    .replace(/\[[^\]]*\]/g, ' ')
    .replace(/\(([^)]*)\)/g, ' ')
    .replace(/[._]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

alias('number', ['dive number', 'dive #', 'dive no', 'number', '#', 'diveno', 'divenumber', 'no']);
alias('date', ['date', 'divedate', 'dive date']);
alias('time', ['time', 'entrytime', 'entry time', 'start time', 'starttime', 'time in']);
alias('datetime', ['date/time', 'datetime', 'date time', 'start']);
alias('duration', ['duration', 'divetime', 'dive time', 'bottom time', 'total time', 'total duration', 'dive duration', 'runtime', 'run time']);
alias('maxDepth', ['maxdepth', 'max depth', 'max  depth', 'depth', 'dive depth', 'maximum depth', 'max']);
alias('avgDepth', ['avgdepth', 'avg depth', 'average depth', 'mean depth', 'meandepth', 'depthavg', 'averagedepth']);
alias('waterTemp', ['watertemp', 'water temp', 'water temperature', 'bottom temp', 'temp', 'templow', 'water']);
alias('airTemp', ['airtemp', 'air temp', 'air temperature', 'surface temp', 'tempair']);
alias('site', ['location', 'place', 'site', 'dive site', 'divesite', 'dive location', 'site name']);
alias('gps', ['gps', 'position', 'coordinates']);
alias('lat', ['lat', 'latitude', 'sitelat']);
alias('lon', ['lon', 'lng', 'longitude', 'sitelon']);
alias('buddy', ['buddy', 'buddies', 'dive buddy', 'dive partner', 'partner']);
alias('diveMaster', ['divemaster', 'dive master', 'dive guide', 'diveguide', 'guide']);
alias('notes', ['notes', 'comments', 'comment', 'remarks', 'description']);
alias('equipment', ['suit', 'exposure suit', 'equipment', 'gear']);
alias('tankSize', ['cylinder size', 'cyl size', 'tanksize', 'tank size', 'tankvolume', 'tank volume', 'tank', 'tank type', 'cylinder']);
alias('startPressure', ['startpressure', 'start pressure', 'press', 'pres s', 'pstart', 'pressurestart', 'psi start', 'pressure in', 'pressure start']);
alias('endPressure', ['endpressure', 'end pressure', 'prese', 'pres e', 'pend', 'pressureend', 'psi end', 'pressure out', 'pressure end']);
alias('o2', ['o2', 'o2 %', 'o2percent', 'oxygen', 'gas mixture', 'gas', 'air/nitrox', 'nitrox', 'gasmix', 'mix']);
alias('he', ['he', 'he %', 'helium']);
alias('sampleTime', ['sample time', 'sampletime']);
alias('sampleDepth', ['sample depth', 'sampledepth']);
alias('sampleTemp', ['sample temperature', 'sample temp', 'ambient temp']);
alias('samplePressure', ['sample pressure', 'samplepressure']);
// common German logbook headers (the site is UK/EU-facing)
alias('number', ['nr', 'tg nr', 'tauchgang']);
alias('date', ['datum']);
alias('time', ['zeit', 'uhrzeit', 'startzeit']);
alias('duration', ['dauer', 'tauchzeit', 'grundzeit']);
alias('maxDepth', ['tiefe', 'max tiefe', 'maximale tiefe']);
alias('waterTemp', ['wassertemperatur', 'wassertemp', 'temperatur']);
alias('site', ['ort', 'tauchplatz', 'platz']);
alias('notes', ['bemerkungen', 'notizen', 'kommentar']);

const UNIT_TOKENS = /\[([^\]]+)\]|\(([^)]+)\)/g;
const KNOWN_UNITS = new Set(['m', 'ft', 'feet', 'c', 'f', '°c', '°f', 'celsius', 'fahrenheit', 'bar', 'psi', 'l', 'liters', 'litres', 'cuft', 'min', 'mins', 'minutes', 's', 'sec', 'seconds', 'kg', 'lbs']);

function unitHint(rawHeader) {
  let m;
  UNIT_TOKENS.lastIndex = 0;
  while ((m = UNIT_TOKENS.exec(String(rawHeader)))) {
    const token = (m[1] || m[2] || '').trim().toLowerCase();
    if (KNOWN_UNITS.has(token)) return token.replace(/^°/, '').replace('feet', 'ft').replace(/^liters$|^litres$/, 'l').replace(/^mins$|^minutes$/, 'min').replace(/^seconds$|^sec$/, 's');
  }
  return undefined;
}

/** RFC 4180-ish tokenizer: quoted fields, doubled quotes, embedded delimiters/newlines. */
export function tokenizeCsv(text, delimiter) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else inQuotes = false;
      } else field += ch;
    } else if (ch === '"' && field === '') {
      inQuotes = true;
    } else if (ch === delimiter) {
      row.push(field); field = '';
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.length > 1 || row[0] !== '') rows.push(row);
      row = [];
    } else field += ch;
  }
  row.push(field);
  if (row.length > 1 || row[0] !== '') rows.push(row);
  return rows;
}

export function sniffDelimiter(headerLine) {
  let best = ',', bestCount = -1;
  for (const d of ['\t', ',', ';', '|']) {
    const count = headerLine.split(d).length - 1;
    if (count > bestCount) { best = d; bestCount = count; }
  }
  return best;
}

/**
 * Inspect a CSV for the mapping UI: headers, auto-mapped fields, preview rows.
 * @param {string} text
 * @returns {{delimiter: string, headers: string[], autoMap: (string|null)[],
 *            units: (string|undefined)[], rows: string[][]} | {error: string}}
 */
export function csvIntrospect(text) {
  const firstLine = (text.match(/^[^\n\r]*/) || [''])[0];
  const delimiter = sniffDelimiter(firstLine);
  const rows = tokenizeCsv(text, delimiter);
  if (rows.length < 2) return { error: 'file needs a header row and at least one dive row' };
  const headers = rows[0];
  const autoMap = headers.map((h) => ALIASES.get(normHeader(h)) || null);
  const units = headers.map((h) => unitHint(h));
  return { delimiter, headers, autoMap, units, rows: rows.slice(1, 6) };
}

const ftToM = (v) => v * 0.3048;
const fToC = (v) => ((v - 32) * 5) / 9;
const psiToBar = (v) => v / 14.503773773;

function convert(value, kind, unit, warnings, label) {
  if (value === undefined) return undefined;
  if (kind === 'depth') return unit === 'ft' ? ftToM(value) : value;
  if (kind === 'temp' || kind === 'airTemp') {
    if (unit === 'f' || unit === 'fahrenheit') return fToC(value);
    if (unit === 'c' || unit === 'celsius') return value;
    // water above 45 is impossible; air runs hotter in real logbooks (desert boats)
    const threshold = kind === 'airTemp' ? 57 : 45;
    if (value > threshold) { warnings.push(`${label}: temperature ${value} looks like °F — converted`); return fToC(value); }
    return value;
  }
  if (kind === 'pressure') {
    if (unit === 'psi') return psiToBar(value);
    if (unit === 'bar') return value;
    if (value > 400) { warnings.push(`${label}: pressure ${value} looks like psi — converted`); return psiToBar(value); }
    return value;
  }
  if (kind === 'volume') {
    if (unit === 'cuft') { warnings.push(`${label}: tank size in cuft not converted (needs working pressure)`); return undefined; }
    return value;
  }
  return value;
}

/** 'EAN32' / 'Nitrox 32' / '32' / '32%' / '21/35' / 'Air' → {o2Pct, hePct} */
export function parseGasMix(cell) {
  if (cell === undefined || cell === null) return undefined;
  const s = String(cell).trim().toLowerCase();
  if (!s) return undefined;
  if (s === 'air') return { o2Pct: 21 };
  let m = /^(?:ean|nitrox|nx)\s*x?\s*(\d{2})$/.exec(s);
  if (m) return { o2Pct: +m[1] };
  m = /^(?:tmx|trimix)?\s*(\d{1,3})\s*\/\s*(\d{1,3})$/.exec(s);
  if (m) return { o2Pct: +m[1], hePct: +m[2] };
  const n = num(s);
  if (n !== undefined && n > 0 && n <= 100) return { o2Pct: n };
  return undefined;
}

function decideDayFirst(rows, col, fallback) {
  let sawDayFirst = false, sawMonthFirst = false;
  for (const row of rows) {
    const m = /^(\d{1,2})[/.-](\d{1,2})[/.-]\d{2,4}$/.exec(String(row[col] || '').trim());
    if (!m) continue;
    if (+m[1] > 12) sawDayFirst = true;
    if (+m[2] > 12) sawMonthFirst = true;
  }
  if (sawDayFirst && !sawMonthFirst) return true;
  if (sawMonthFirst && !sawDayFirst) return false;
  return fallback;
}

function buildDive(cells, cols, ctx, warnings, rowNo) {
  const label = `row ${rowNo}`;
  // decimal commas in numeric cells are handled inside num() — free text
  // (notes, sites, buddies) passes through untouched
  const get = (field) => {
    const idx = cols[field];
    if (idx === undefined) return undefined;
    const v = cells[idx];
    return v === undefined || String(v).trim() === '' ? undefined : String(v).trim();
  };

  let startedAt;
  if (cols.datetime !== undefined) startedAt = parseDateTime(get('datetime'), undefined, { dayFirst: ctx.dayFirst });
  if (!startedAt) startedAt = parseDateTime(get('date'), get('time'), { dayFirst: ctx.dayFirst });
  if (!startedAt) return { error: `${label}: no usable date` };

  const dive = { startedAt, diveType: 'scuba', source: { parserId: 'csv' } };
  const number = num(get('number'));
  if (number !== undefined) dive.number = number;

  const dur = get('duration');
  if (dur !== undefined) {
    const unit = ctx.units[cols.duration] === 's' ? 'sec' : ctx.units[cols.duration] === 'min' ? 'min' : undefined;
    // Subsurface writes MM:SS under a '[min]' header — colon form wins over the hint
    dive.durationSec = /:/.test(dur) ? parseDuration(dur) : parseDuration(dur, unit || 'min');
  }

  const md = convert(num(get('maxDepth')), 'depth', ctx.units[cols.maxDepth], warnings, label);
  if (md !== undefined) dive.maxDepthM = md;
  const ad = convert(num(get('avgDepth')), 'depth', ctx.units[cols.avgDepth], warnings, label);
  if (ad !== undefined) dive.avgDepthM = ad;
  const wt = convert(num(get('waterTemp')), 'temp', ctx.units[cols.waterTemp], warnings, label);
  if (wt !== undefined) dive.waterTempC = wt;
  const at = convert(num(get('airTemp')), 'airTemp', ctx.units[cols.airTemp], warnings, label);
  if (at !== undefined) dive.airTempC = at;

  const siteName = get('site');
  if (siteName) {
    const site = { name: siteName };
    const gps = get('gps');
    if (gps) {
      const g = /^(-?\d+(?:\.\d+)?)[,;\s]+(-?\d+(?:\.\d+)?)$/.exec(gps.replace(/(\d),(\d)/g, '$1.$2'));
      if (g) { site.lat = parseFloat(g[1]); site.lon = parseFloat(g[2]); }
    }
    const lat = num(get('lat')), lon = num(get('lon'));
    if (lat !== undefined && lon !== undefined) { site.lat = lat; site.lon = lon; }
    dive.site = site;
  }

  for (const [field, key] of [['buddy', 'buddy'], ['diveMaster', 'diveMaster'], ['notes', 'notes'], ['equipment', 'equipment']]) {
    const v = get(field);
    if (v) dive[key] = v;
  }

  const tank = {};
  const size = convert(num(get('tankSize')), 'volume', ctx.units[cols.tankSize], warnings, label);
  if (size !== undefined) tank.volumeL = size;
  const sp = convert(num(get('startPressure')), 'pressure', ctx.units[cols.startPressure], warnings, label);
  if (sp !== undefined) tank.startBar = sp;
  const ep = convert(num(get('endPressure')), 'pressure', ctx.units[cols.endPressure], warnings, label);
  if (ep !== undefined) tank.endBar = ep;
  const gas = parseGasMix(get('o2'));
  if (gas) {
    tank.gasO2Pct = gas.o2Pct;
    if (gas.hePct) tank.gasHePct = gas.hePct;
  }
  const he = num(get('he'));
  if (he !== undefined && he > 0) tank.gasHePct = he;
  if (Object.keys(tank).length) dive.tanks = [tank];

  return { dive };
}

function parseProfileCsv(rows, cols, ctx, result) {
  // Subsurface profile export: one SAMPLE per row, grouped by dive number/date
  const groups = new Map();
  rows.forEach((cells, i) => {
    const key = [cols.number !== undefined ? cells[cols.number] : '', cols.date !== undefined ? cells[cols.date] : '', cols.time !== undefined ? cells[cols.time] : ''].join('|');
    if (!groups.has(key)) groups.set(key, { cells, samples: [] });
    const g = groups.get(key);
    const rawT = cells[cols.sampleTime];
    const unit = ctx.units[cols.sampleTime];
    let tSec;
    if (rawT !== undefined && /:/.test(rawT)) tSec = parseDuration(rawT);
    else tSec = parseDuration(rawT, unit === 's' ? 'sec' : 'min');
    const depthM = convert(num(cells[cols.sampleDepth]), 'depth', ctx.units[cols.sampleDepth], result.warnings, `row ${i + 2}`);
    if (tSec === undefined || depthM === undefined) return;
    const s = { tSec, depthM };
    if (cols.sampleTemp !== undefined) {
      const t = convert(num(cells[cols.sampleTemp]), 'temp', ctx.units[cols.sampleTemp], result.warnings, `row ${i + 2}`);
      if (t !== undefined) s.tempC = t;
    }
    if (cols.samplePressure !== undefined) {
      const p = convert(num(cells[cols.samplePressure]), 'pressure', ctx.units[cols.samplePressure], result.warnings, `row ${i + 2}`);
      if (p !== undefined) s.pressureBar = p;
    }
    g.samples.push(s);
  });

  for (const [, g] of groups) {
    const built = buildDive(g.cells, cols, ctx, result.warnings, 1);
    if (built.error) { result.warnings.push(built.error); continue; }
    if (g.samples.length) built.dive.samples = g.samples;
    result.dives.push(built.dive);
  }
}

/** @type {import('../types.js').ParserModule} */
export const csvParser = {
  id: 'csv',
  displayName: 'CSV',
  extensions: ['.csv', '.tsv', '.txt'],

  sniff(bytes, text) {
    if (/^\s*</.test(text)) return false;
    const head = text.slice(0, 65536);
    const firstLine = (head.match(/^[^\n\r]*/) || [''])[0];
    const d = sniffDelimiter(firstLine);
    const rows = tokenizeCsv(head, d).slice(0, 4); // real tokenizer: quoted delimiters don't skew counts
    if (rows.length < 2 || rows[0].length < 2) return false;
    // at least two recognizable headers, or a plausible consistent grid
    const hits = rows[0].filter((h) => ALIASES.has(normHeader(h))).length;
    const consistent = Math.abs(rows[1].length - rows[0].length) <= 1;
    return consistent && (hits >= 2 || rows[0].length >= 4);
  },

  /**
   * @param {Object} [options]
   * @param {Object<string,string>} [options.mapping]  header name (or #index) → CSV_FIELDS key
   * @param {boolean} [options.dayFirst]  ambiguous-date order (default true, UK/EU)
   */
  parse(bytes, text, options = {}) {
    const result = makeParseResult();
    const intro = csvIntrospect(text);
    if (intro.error) {
      result.errors.push(intro.error);
      return result;
    }
    const { delimiter, headers, autoMap, units } = intro;
    const allRows = tokenizeCsv(text, delimiter).slice(1);

    // column index per field: explicit mapping (by header name or '#index') wins
    const cols = {};
    headers.forEach((h, i) => {
      let field = autoMap[i];
      if (options.mapping) {
        const explicit = options.mapping[h] ?? options.mapping['#' + i];
        if (explicit !== undefined) field = explicit;
      }
      if (field && field !== 'ignore' && cols[field] === undefined) cols[field] = i;
    });

    const isProfile = cols.sampleTime !== undefined && cols.sampleDepth !== undefined;
    const hasDate = cols.date !== undefined || cols.datetime !== undefined;
    if (!hasDate || (!isProfile && cols.duration === undefined && cols.maxDepth === undefined)) {
      result.errors.push(`${NEEDS_MAPPING}: couldn't identify the required columns (date plus duration or max depth) — map them manually`);
      return result;
    }

    const dateCol = cols.date !== undefined ? cols.date : cols.datetime;
    const ctx = {
      delimiter,
      units,
      dayFirst: decideDayFirst(allRows, dateCol, options.dayFirst !== false),
    };

    if (isProfile) {
      parseProfileCsv(allRows, cols, ctx, result);
    } else {
      allRows.forEach((cells, i) => {
        if (cells.every((c) => String(c).trim() === '')) return;
        try {
          const built = buildDive(cells, cols, ctx, result.warnings, i + 2);
          if (built.error) result.warnings.push(built.error);
          else result.dives.push(built.dive);
        } catch (e) {
          result.warnings.push(`row ${i + 2}: skipped — ${e.message}`);
        }
      });
    }

    if (!result.dives.length && !result.errors.length) {
      result.errors.push('no dives could be read from this CSV — check the column mapping');
    }
    return result;
  },
};
