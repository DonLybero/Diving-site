// UDDF 3.x parser (the canonical format, PRD §5 P0). Unit semantics verified
// against the 3.2.1/3.2.3 XSDs and Subsurface's importer: strict SI — Kelvin,
// Pascals, cubic metres, seconds, fractions 0..1. Parses namespace-agnostically
// (3.1/3.2/no-namespace files all exist in the wild); ids are opaque strings
// (real exports violate xs:ID rules). 273.15 K is the "no reading" sentinel.

import { makeParseResult } from '../types.js';
import { parseXml, arrayTags, asArray, tagText, rootTag } from '../xml.js';
import { num, kelvinToC, pascalToBar } from '../values.js';

const REPEATED = ['repetitiongroup', 'dive', 'waypoint', 'tankdata', 'link', 'mix', 'site', 'buddy', 'para', 'divesite', 'alarm', 'tankpressure'];

function kTemp(v) {
  const c = kelvinToC(v);
  if (c === undefined) return undefined;
  if (Math.abs(c) < 1e-9) return undefined; // exactly 273.15 K = not recorded
  return c;
}

function personName(personal) {
  if (!personal) return undefined;
  const parts = [tagText(personal.firstname), tagText(personal.middlename), tagText(personal.lastname)]
    .filter(Boolean);
  return parts.length ? parts.join(' ') : undefined;
}

function indexById(items, build) {
  const map = new Map();
  for (const item of items) {
    const id = item && item['@_id'];
    if (id === undefined || id === null) continue;
    const value = build(item);
    if (value !== undefined) map.set(String(id).trim(), value);
  }
  return map;
}

function parseTank(td, mixes, warnings, label) {
  const tank = {};
  const ref = asArray(td.link).map((l) => l && l['@_ref']).find((r) => r !== undefined);
  const mix = ref !== undefined ? mixes.get(String(ref).trim()) : undefined;
  const startBar = pascalToBar(tagText(td.tankpressurebegin));
  const endBar = pascalToBar(tagText(td.tankpressureend));
  // Shearwater emits unused tank slots: no mix link and zero pressures — skip silently
  if (!mix && !(startBar > 0) && !(endBar > 0)) return undefined;
  if (mix) {
    if (mix.o2 !== undefined) tank.gasO2Pct = mix.o2 * 100;
    if (mix.he !== undefined && mix.he > 0) tank.gasHePct = mix.he * 100;
  } else if (ref !== undefined) {
    warnings.push(`${label}: gas mix '${ref}' not found in file`);
  }
  let vol = num(tagText(td.tankvolume));
  if (vol !== undefined) {
    if (vol <= 0.5) vol *= 1000; // spec: cubic metres; some exporters wrongly write litres
    tank.volumeL = vol;
  }
  if (startBar !== undefined && startBar > 0) tank.startBar = startBar;
  if (endBar !== undefined && endBar > 0) tank.endBar = endBar;
  return Object.keys(tank).length ? tank : undefined;
}

function parseDive(node, ctx, result, groupIndex, diveIndex) {
  const label = `dive ${diveIndex}`;
  const before = node.informationbeforedive || {};
  const after = node.informationafterdive || {};

  const dive = { diveType: 'scuba' };
  const startedAt = tagText(before.datetime);
  if (!startedAt) {
    result.warnings.push(`${label}: skipped — no date/time`);
    return;
  }
  dive.startedAt = startedAt;

  const number = num(tagText(before.divenumber));
  if (number !== undefined) dive.number = number;
  const airTempC = kTemp(tagText(before.airtemperature));
  if (airTempC !== undefined) dive.airTempC = airTempC;

  // polymorphic <link ref>: classify by which id table the ref lives in
  const buddies = [];
  for (const l of asArray(before.link)) {
    const ref = l && l['@_ref'] !== undefined ? String(l['@_ref']).trim() : undefined;
    if (!ref) continue;
    if (ctx.sites.has(ref)) dive.site = ctx.sites.get(ref);
    else if (ctx.buddies.has(ref)) buddies.push(ctx.buddies.get(ref));
  }
  if (buddies.length) dive.buddy = buddies.join(', ');

  dive.durationSec = num(tagText(after.diveduration));
  dive.maxDepthM = num(tagText(after.greatestdepth));
  const avg = num(tagText(after.averagedepth));
  if (avg !== undefined) dive.avgDepthM = avg;
  const waterTempC = kTemp(tagText(after.lowesttemperature));
  if (waterTempC !== undefined) dive.waterTempC = waterTempC;
  if (after.notes) {
    const paras = asArray(after.notes.para).map(tagText).filter(Boolean);
    if (paras.length) dive.notes = paras.join('\n\n');
  }

  const tanks = asArray(node.tankdata)
    .map((td) => parseTank(td, ctx.mixes, result.warnings, label))
    .filter(Boolean);
  if (tanks.length) dive.tanks = tanks;

  if (node.samples) {
    const samples = [];
    for (const wp of asArray(node.samples.waypoint)) {
      if (!wp || typeof wp !== 'object') continue;
      const tSec = num(tagText(wp.divetime));
      const depthM = num(tagText(wp.depth));
      if (tSec === undefined || depthM === undefined) continue;
      const s = { tSec, depthM };
      const tempC = kTemp(tagText(wp.temperature));
      if (tempC !== undefined) s.tempC = tempC;
      // multi-cylinder dives log one <tankpressure ref=…> per tank — take the first
      const pressureBar = pascalToBar(tagText(asArray(wp.tankpressure)[0]));
      if (pressureBar !== undefined && pressureBar > 0) s.pressureBar = pressureBar;
      samples.push(s);
    }
    if (samples.length) dive.samples = samples;
  }

  const id = node['@_id'];
  dive.source = { parserId: 'uddf' };
  if (id !== undefined) dive.source.externalId = String(id);
  const generatorName = ctx.generatorName;
  if (generatorName) dive.source.computerModel = generatorName;

  result.dives.push(dive);
}

/** @type {import('../types.js').ParserModule} */
export const uddfParser = {
  id: 'uddf',
  displayName: 'UDDF',
  extensions: ['.uddf'],

  sniff(bytes, text) {
    return rootTag(text) === 'uddf';
  },

  parse(bytes, text) {
    const result = makeParseResult();
    const { doc, error } = parseXml(text, { isArray: arrayTags(REPEATED), removeNSPrefix: true });
    if (error) {
      result.errors.push(error);
      return result;
    }
    const uddf = doc && doc.uddf;
    if (!uddf) {
      result.errors.push('not a UDDF document (no <uddf> root element)');
      return result;
    }

    const ctx = {
      generatorName: uddf.generator ? tagText(uddf.generator.name) : undefined,
      sites: indexById(asArray(uddf.divesite).flatMap((ds) => asArray(ds && ds.site)), (site) => {
        const name = tagText(site.name) || (site.geography && tagText(site.geography.location));
        if (!name) return undefined;
        const out = { name };
        if (site.geography) {
          const lat = num(tagText(site.geography.latitude));
          const lon = num(tagText(site.geography.longitude));
          if (lat !== undefined && lon !== undefined) { out.lat = lat; out.lon = lon; }
        }
        return out;
      }),
      buddies: indexById(asArray(uddf.diver && uddf.diver.buddy), (b) => personName(b.personal) || (b['@_id'] ? String(b['@_id']) : undefined)),
      mixes: indexById(asArray(uddf.gasdefinitions && uddf.gasdefinitions.mix), (m) => {
        const o2 = num(tagText(m.o2));
        const he = num(tagText(m.he));
        // tolerate percent-style mixes some exporters write (32 instead of 0.32)
        return {
          o2: o2 === undefined ? undefined : (o2 > 1 ? o2 / 100 : o2),
          he: he === undefined ? undefined : (he > 1 ? he / 100 : he),
        };
      }),
    };

    const groups = asArray(uddf.profiledata && uddf.profiledata.repetitiongroup);
    let diveIndex = 0;
    groups.forEach((group, gi) => {
      for (const d of asArray(group && group.dive)) {
        diveIndex += 1;
        try {
          parseDive(d, ctx, result, gi, diveIndex);
        } catch (e) {
          result.warnings.push(`dive ${diveIndex}: skipped — ${e.message}`);
        }
      }
    });

    if (!groups.length) result.errors.push('no dive profiles found (missing <profiledata>)');
    return result;
  },
};
