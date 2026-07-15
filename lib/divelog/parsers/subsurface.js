// Subsurface XML parser (.xml/.ssrf — identical formats). Verified against
// core/save-xml.c and real repo logbooks: always metric with the unit inside
// the attribute string ('18.2 m', '24.0 C', '200.0 bar'); durations and
// sample times are 'MIN:SS min' with unbounded minutes (65:36 = 65 min 36 s)
// while a BARE number in a sample @time is seconds; samples delta-encode
// temp/pressure (values appear only on change); tank pressure is spelled
// @pressure (legacy) or @pressure0..6 (current); cylinder @o2 absent = air;
// dives may be wrapped in <trip> elements; legacy v1 files root at <dives>.

import { makeParseResult } from '../types.js';
import { parseXml, arrayTags, asArray, tagText, rootTag } from '../xml.js';
import { num, parseDateTime } from '../values.js';

const REPEATED = ['site', 'dive', 'trip', 'cylinder', 'weightsystem', 'divecomputer', 'sample', 'event'];

/** 'MIN:SS min' / 'H:M:S' → seconds; bare number → seconds (Subsurface sampletime()). */
function sampleTime(v) {
  if (v === undefined) return undefined;
  const s = String(v).trim();
  const m = /^(\d+):(\d{1,2})(?::(\d{1,2}))?/.exec(s);
  if (m) {
    return m[3] === undefined
      ? (+m[1]) * 60 + (+m[2])
      : (+m[1]) * 3600 + (+m[2]) * 60 + (+m[3]);
  }
  return num(s);
}

/** 'MIN:SS min' → seconds; bare '44.00' (DivingLog vintage) → minutes. */
function duration(v) {
  if (v === undefined) return undefined;
  const s = String(v).trim();
  const m = /^(\d+):(\d{1,2})/.exec(s);
  if (m) return (+m[1]) * 60 + (+m[2]);
  const n = num(s);
  return n === undefined ? undefined : Math.round(n * 60);
}

function parseGps(gps) {
  if (!gps) return undefined;
  const m = /^\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*$/.exec(String(gps));
  if (!m) return undefined;
  return { lat: parseFloat(m[1]), lon: parseFloat(m[2]) };
}

function attr(node, name) {
  const v = node && node['@_' + name];
  return v === undefined || v === '' ? undefined : String(v);
}

function collectDives(container, out) {
  for (const d of asArray(container && container.dive)) out.push(d);
  for (const t of asArray(container && container.trip)) collectDives(t, out);
}

function parseCylinder(cyl) {
  const tank = {};
  const size = num(attr(cyl, 'size'));
  if (size !== undefined) tank.volumeL = size;
  const start = num(attr(cyl, 'start'));
  if (start !== undefined) tank.startBar = start;
  const end = num(attr(cyl, 'end'));
  if (end !== undefined) tank.endBar = end;
  const o2 = num(attr(cyl, 'o2'));
  tank.gasO2Pct = o2 === undefined ? 21 : o2; // absent o2 means air
  const he = num(attr(cyl, 'he'));
  if (he !== undefined && he > 0) tank.gasHePct = he;
  return tank;
}

function bestComputer(dcs) {
  let best;
  let bestSamples = -1;
  for (const dc of dcs) {
    const n = asArray(dc && dc.sample).length;
    if (n > bestSamples) { best = dc; bestSamples = n; }
  }
  return best;
}

function parseDive(node, sites, result, index) {
  const label = `dive ${attr(node, 'number') || index}`;
  const startedAt = parseDateTime(attr(node, 'date'), attr(node, 'time'));
  if (!startedAt) {
    result.warnings.push(`${label}: skipped — no date`);
    return;
  }
  const dive = { startedAt, diveType: 'scuba' };

  const number = num(attr(node, 'number'));
  if (number !== undefined) dive.number = number;
  dive.durationSec = duration(attr(node, 'duration'));

  const siteId = attr(node, 'divesiteid');
  if (siteId && sites.has(siteId.trim().toLowerCase())) {
    dive.site = sites.get(siteId.trim().toLowerCase());
  } else if (node.location) {
    // legacy v2: inline <location gps='lat lon'>Name</location>
    const name = tagText(node.location);
    if (name) {
      dive.site = { name, ...(parseGps(attr(node.location, 'gps')) || {}) };
    }
  }

  for (const [key, field] of [['buddy', 'buddy'], ['divemaster', 'diveMaster'], ['notes', 'notes'], ['suit', 'equipment']]) {
    const v = tagText(node[key]);
    if (v) dive[field] = v;
  }

  const tanks = asArray(node.cylinder).map(parseCylinder).filter((t) => Object.keys(t).length);
  if (tanks.length) dive.tanks = tanks;

  const dcs = asArray(node.divecomputer);
  const dc = bestComputer(dcs);

  // user-entered <divetemperature> wins over the computer's <temperature>
  const diveTemp = node.divetemperature || {};
  const dcTemp = (dc && dc.temperature) || {};
  const water = num(attr(diveTemp, 'water')) ?? num(attr(dcTemp, 'water'));
  if (water !== undefined) dive.waterTempC = water;
  const air = num(attr(diveTemp, 'air')) ?? num(attr(dcTemp, 'air'));
  if (air !== undefined) dive.airTempC = air;

  // depth lives inside <divecomputer>; legacy v1 had it directly on <dive>
  const depthNode = (dc && dc.depth) || node.depth;
  if (depthNode) {
    const max = num(attr(depthNode, 'max'));
    if (max !== undefined) dive.maxDepthM = max;
    const mean = num(attr(depthNode, 'mean'));
    if (mean !== undefined) dive.avgDepthM = mean;
  }

  if (dc) {
    const dctype = (attr(dc, 'dctype') || '').toLowerCase();
    if (dctype === 'freedive') dive.diveType = 'freedive';
    const samples = [];
    for (const s of asArray(dc.sample)) {
      const tSec = sampleTime(attr(s, 'time'));
      const depthM = num(attr(s, 'depth'));
      if (tSec === undefined || depthM === undefined) continue;
      const point = { tSec, depthM };
      const temp = num(attr(s, 'temp'));
      if (temp !== undefined) point.tempC = temp;
      // pressure spellings across vintages: pressure, then pressure0..pressure6
      let pressure = num(attr(s, 'pressure'));
      for (let i = 0; pressure === undefined && i <= 6; i++) pressure = num(attr(s, 'pressure' + i));
      if (pressure !== undefined) point.pressureBar = pressure;
      samples.push(point);
    }
    if (samples.length) dive.samples = samples;
    dive.source = { parserId: 'subsurface' };
    const model = attr(dc, 'model');
    if (model && model !== 'manually added dive') dive.source.computerModel = model;
    const diveid = attr(dc, 'diveid');
    if (diveid) dive.source.externalId = diveid;
  } else {
    dive.source = { parserId: 'subsurface' };
  }

  result.dives.push(dive);
}

/** @type {import('../types.js').ParserModule} */
export const subsurfaceParser = {
  id: 'subsurface',
  displayName: 'Subsurface XML',
  extensions: ['.ssrf', '.xml'],

  sniff(bytes, text) {
    const root = rootTag(text);
    if (root === 'divelog') return /program=["']subsurface["']/i.test(text.slice(0, 2048));
    if (root === 'dives') return /<program\s+name=["']subsurface["']/i.test(text.slice(0, 4096));
    return false;
  },

  parse(bytes, text) {
    const result = makeParseResult();
    const { doc, error } = parseXml(text, { isArray: arrayTags(REPEATED) });
    if (error) {
      result.errors.push(error);
      return result;
    }
    // v2/v3 root is <divelog><dives>…; legacy v1 roots directly at <dives>
    const divelog = doc.divelog || doc;
    const divesEl = divelog.dives;
    if (!divesEl) {
      result.errors.push('not a Subsurface logbook (no <dives> section)');
      return result;
    }

    const sites = new Map();
    for (const s of asArray(divelog.divesites && divelog.divesites.site)) {
      const uuid = attr(s, 'uuid');
      const name = attr(s, 'name');
      if (!uuid || !name) continue;
      const site = { name, ...(parseGps(attr(s, 'gps')) || {}) };
      sites.set(uuid.trim().toLowerCase(), site);
    }

    const diveNodes = [];
    collectDives(divesEl, diveNodes);

    diveNodes.forEach((d, i) => {
      try {
        parseDive(d, sites, result, i + 1);
      } catch (e) {
        result.warnings.push(`dive ${i + 1}: skipped — ${e.message}`);
      }
    });

    if (!diveNodes.length) result.errors.push('no dives found in this logbook');
    // trip-wrapped and loose dives lose interleaved document order in the
    // object mapping — restore chronological order
    result.dives.sort((a, b) => new Date(a.startedAt) - new Date(b.startedAt));
    return result;
  },
};
