// Suunto SML parser (.sml — DM4/DM5 desktop exports, one dive per file).
// Field mapping verified against libdivecomputer's suunto_eonsteel_parser.c
// data model and real DM5 exports: pure SI with no unit attributes —
// temperatures in Kelvin, pressures in Pascals, gas fractions 0..1, times in
// seconds, depths in metres (with raw float32 noise). The same <sml> shell
// carries Ambit sports logs — a dive file is gated on Header/Diving or
// Header/Depth. Samples are heterogeneous: event-only samples have no depth.

import { makeParseResult } from '../types.js';
import { parseXml, arrayTags, asArray, tagText, rootTag } from '../xml.js';
import { num, pascalToBar } from '../values.js';

const REPEATED = ['DeviceLog', 'Gas', 'Sample', 'Cylinder'];

/** Kelvin → °C; tolerate already-Celsius values from exotic exports. */
function smlTemp(v) {
  const n = num(tagText(v));
  if (n === undefined) return undefined;
  return n > 200 ? n - 273.15 : n;
}

function parseGases(diving, warnings) {
  const tanks = [];
  for (const gas of asArray(diving && diving.Gases && diving.Gases.Gas)) {
    if (tagText(gas.State) === 'Off') continue; // unused fixed slots
    const tank = {};
    const o2 = num(tagText(gas.Oxygen));
    if (o2 !== undefined && o2 > 0) tank.gasO2Pct = o2 <= 1 ? o2 * 100 : o2;
    const he = num(tagText(gas.Helium));
    if (he !== undefined && he > 0) tank.gasHePct = he <= 1 ? he * 100 : he;
    const size = num(tagText(gas.TankSize));
    if (size !== undefined && size > 0) tank.volumeL = size;
    const start = pascalToBar(tagText(gas.StartPressure));
    if (start !== undefined && start > 0) tank.startBar = start;
    const end = pascalToBar(tagText(gas.EndPressure));
    if (end !== undefined && end > 0) tank.endBar = end;
    if (Object.keys(tank).length) tanks.push(tank);
  }
  return tanks;
}

function parseDeviceLog(log, result, index) {
  const label = `dive ${index}`;
  const header = log.Header;
  if (!header) {
    result.warnings.push(`${label}: skipped — no <Header>`);
    return;
  }
  const diving = header.Diving;
  if (!diving && !header.Depth) {
    result.warnings.push(`${label}: skipped — not a dive log (no Diving/Depth section; Suunto sports logs share this format)`);
    return;
  }

  const startedAt = tagText(header.DateTime);
  if (!startedAt) {
    result.warnings.push(`${label}: skipped — no date/time`);
    return;
  }

  const dive = { startedAt, diveType: 'scuba', source: { parserId: 'suunto-sml' } };
  const mode = diving ? tagText(diving.DiveMode) : undefined;
  if (mode && /free/i.test(mode)) dive.diveType = 'freedive';

  dive.durationSec = num(tagText(header.Duration));
  if (header.Depth) {
    const max = num(tagText(header.Depth.Max));
    if (max !== undefined) dive.maxDepthM = max;
    const avg = num(tagText(header.Depth.Avg));
    if (avg !== undefined) dive.avgDepthM = avg;
  }
  if (diving) {
    const water = smlTemp(diving.TempAtMaxDepth);
    if (water !== undefined) dive.waterTempC = water;
    const air = smlTemp(diving.TempAtStart);
    if (air !== undefined) dive.airTempC = air;
    const tanks = parseGases(diving, result.warnings);
    if (tanks.length) dive.tanks = tanks;
  }

  const device = log.Device;
  if (device) {
    const name = tagText(device.Name);
    if (name) dive.source.computerModel = name;
    const serial = tagText(device.SerialNumber);
    if (serial) dive.source.externalId = `${serial}:${startedAt}`;
  }

  const samples = [];
  for (const s of asArray(log.Samples && log.Samples.Sample)) {
    if (!s || typeof s !== 'object') continue;
    const tSec = num(tagText(s.Time));
    const depthM = num(tagText(s.Depth));
    if (tSec === undefined || depthM === undefined) continue; // event-only samples
    const point = { tSec, depthM };
    const temp = smlTemp(s.Temperature);
    if (temp !== undefined) point.tempC = temp;
    const cyl = asArray(s.Cylinders && s.Cylinders.Cylinder)[0];
    if (cyl) {
      const p = pascalToBar(tagText(cyl.Pressure));
      if (p !== undefined && p > 0) point.pressureBar = p;
    }
    samples.push(point);
  }
  if (samples.length) dive.samples = samples;

  result.dives.push(dive);
}

/** @type {import('../types.js').ParserModule} */
export const suuntoSmlParser = {
  id: 'suunto-sml',
  displayName: 'Suunto DM4/DM5 (SML)',
  extensions: ['.sml'],

  sniff(bytes, text) {
    return rootTag(text) === 'sml' && /suunto\.com\/schemas\/sml/i.test(text.slice(0, 2048));
  },

  parse(bytes, text) {
    const result = makeParseResult();
    const { doc, error } = parseXml(text, { isArray: arrayTags(REPEATED), removeNSPrefix: true });
    if (error) {
      result.errors.push(error);
      return result;
    }
    const sml = doc && doc.sml;
    if (!sml) {
      result.errors.push('not a Suunto SML file (no <sml> root element)');
      return result;
    }
    const logs = asArray(sml.DeviceLog);
    if (!logs.length) {
      result.errors.push('no <DeviceLog> in this file');
      return result;
    }
    logs.forEach((log, i) => {
      try {
        parseDeviceLog(log, result, i + 1);
      } catch (e) {
        result.warnings.push(`dive ${i + 1}: skipped — ${e.message}`);
      }
    });
    if (!result.dives.length && result.warnings.length && !result.errors.length) {
      // a file full of non-dive logs is a file-level condition worth naming
      result.errors.push('no dives found — this Suunto file contains no diving logs');
    }
    return result;
  },
};
