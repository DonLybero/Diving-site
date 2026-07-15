// Garmin FIT parser (.fit — Descent dive computers via Garmin Connect/Express).
// Binary format read with the vendored official FIT SDK, which is ~400 KB and
// therefore loaded on demand (dynamic import) only when a FIT file is actually
// detected — parse() is async and the pipeline awaits it. Field semantics from
// the FIT profile: depths in metres, temps in °C, times in seconds (the SDK
// applies scale/offset and converts timestamps to Date), gas contents in
// percent, activity.localTimestamp carries the local-time offset.
//
// Suunto's phone app also emits FIT but encodes dive data differently; when a
// Suunto-manufactured FIT yields no usable dive, we point the diver at the
// Suunto DM5 .sml export instead (PRD §5).

import { makeParseResult } from '../types.js';
import { bytesMatch } from '../encoding.js';

const FIT_EPOCH_MS = 631065600000; // 1989-12-31T00:00:00Z

let sdkPromise;
function loadSdk() {
  sdkPromise = sdkPromise || import('../../../vendor/fitsdk.esm.min.js');
  return sdkPromise;
}

/** Date + offset seconds → 'YYYY-MM-DDTHH:MM:SS±HH:MM' (or naive when offset unknown). */
function isoWithOffset(date, offsetSec) {
  if (offsetSec === undefined) return date.toISOString().slice(0, 19) + 'Z';
  const shifted = new Date(date.getTime() + offsetSec * 1000);
  const base = shifted.toISOString().slice(0, 19);
  if (offsetSec === 0) return base + 'Z';
  const sign = offsetSec < 0 ? '-' : '+';
  const abs = Math.abs(offsetSec);
  const hh = String(Math.floor(abs / 3600)).padStart(2, '0');
  const mm = String(Math.floor((abs % 3600) / 60)).padStart(2, '0');
  return `${base}${sign}${hh}:${mm}`;
}

const APNEA = /apnea/i;

function prettyProduct(fileId) {
  if (!fileId) return undefined;
  const name = fileId.garminProduct || fileId.product;
  if (name === undefined) return undefined;
  const spaced = String(name).replace(/([a-z])([A-Z0-9])/g, '$1 $2');
  return `Garmin ${spaced.charAt(0).toUpperCase()}${spaced.slice(1)}`;
}

function buildDive({ startTime, durationSec, summary, records, offsetSec, tanks, fileId, diveType }) {
  const dive = { diveType, source: { parserId: 'garmin-fit' } };
  dive.startedAt = isoWithOffset(startTime, offsetSec);
  if (durationSec !== undefined) dive.durationSec = Math.round(durationSec);
  if (summary) {
    if (typeof summary.maxDepth === 'number') dive.maxDepthM = summary.maxDepth;
    if (typeof summary.avgDepth === 'number') dive.avgDepthM = summary.avgDepth;
    if (typeof summary.diveNumber === 'number') dive.diveNumber = summary.diveNumber;
    if (dive.diveNumber !== undefined) dive.number = dive.diveNumber;
    delete dive.diveNumber;
    if (summary.bottomTime !== undefined && dive.durationSec === undefined) dive.durationSec = Math.round(summary.bottomTime);
  }
  const samples = [];
  let waterTemp;
  for (const r of records) {
    if (!(r.timestamp instanceof Date) || typeof r.depth !== 'number') continue;
    const tSec = Math.round((r.timestamp.getTime() - startTime.getTime()) / 1000);
    if (tSec < 0) continue;
    const s = { tSec, depthM: r.depth };
    if (typeof r.temperature === 'number') {
      s.tempC = r.temperature;
      if (r.depth > 1 && (waterTemp === undefined || r.temperature < waterTemp)) waterTemp = r.temperature;
    }
    samples.push(s);
  }
  if (samples.length) dive.samples = samples;
  if (waterTemp !== undefined) dive.waterTempC = waterTemp;
  if (tanks.length) dive.tanks = tanks;
  const model = prettyProduct(fileId);
  if (model) dive.source.computerModel = model;
  if (fileId && fileId.serialNumber !== undefined) dive.source.externalId = `${fileId.serialNumber}:${dive.startedAt}`;
  return dive;
}

/** @type {import('../types.js').ParserModule} */
export const garminFitParser = {
  id: 'garmin-fit',
  displayName: 'Garmin FIT',
  extensions: ['.fit'],

  sniff(bytes) {
    return bytesMatch(bytes, 8, '.FIT');
  },

  async parse(bytes) {
    const result = makeParseResult();
    let sdk;
    try {
      sdk = await loadSdk();
    } catch {
      result.errors.push('the FIT reader could not be loaded — check your connection and try again');
      return result;
    }
    const { Decoder, Stream } = sdk;

    let messages, decodeErrors;
    try {
      const decoder = new Decoder(Stream.fromByteArray(bytes));
      if (!decoder.isFIT()) {
        result.errors.push('not a FIT file (bad header)');
        return result;
      }
      ({ messages, errors: decodeErrors } = decoder.read({ includeUnknownData: false }));
    } catch (e) {
      result.errors.push(`FIT decode failed: ${e.message}`);
      return result;
    }

    const fileId = (messages.fileIdMesgs || [])[0];
    const manufacturer = fileId && String(fileId.manufacturer || '').toLowerCase();
    const sessions = (messages.sessionMesgs || []).filter((s) => s && s.startTime instanceof Date);
    const records = messages.recordMesgs || [];
    const summaries = messages.diveSummaryMesgs || [];
    const gases = messages.diveGasMesgs || [];
    const laps = messages.lapMesgs || [];
    const activity = (messages.activityMesgs || [])[0];

    for (const e of decodeErrors || []) {
      result.warnings.push(`FIT decode: ${e.message || e}`);
    }

    // local-time offset from activity.localTimestamp (raw FIT seconds)
    let offsetSec;
    if (activity && typeof activity.localTimestamp === 'number' && activity.timestamp instanceof Date) {
      offsetSec = Math.round(activity.localTimestamp - (activity.timestamp.getTime() - FIT_EPOCH_MS) / 1000);
      if (Math.abs(offsetSec) > 18 * 3600) offsetSec = undefined; // implausible
    }

    const tanks = gases
      .filter((g) => g && g.status !== 'disabled' && typeof g.oxygenContent === 'number' && g.oxygenContent > 0)
      .map((g) => {
        const t = { gasO2Pct: g.oxygenContent };
        if (typeof g.heliumContent === 'number' && g.heliumContent > 0) t.gasHePct = g.heliumContent;
        return t;
      });

    const hasDepth = records.some((r) => typeof r.depth === 'number');
    const diveSessions = sessions.filter((s) => String(s.sport || '').toLowerCase() === 'diving');

    if (!hasDepth || (!diveSessions.length && !summaries.length)) {
      if (manufacturer === 'suunto') {
        result.errors.push('this FIT file comes from the Suunto app, which stores dives differently — export the dive from Suunto DM5 as .sml instead, or tell us which app made it and we\'ll add support');
      } else if (!hasDepth) {
        const sport = sessions.length ? sessions[0].sport : undefined;
        result.errors.push(sport && String(sport).toLowerCase() !== 'diving'
          ? `this FIT file is a ${sport} activity, not a dive`
          : 'no depth data found in this FIT file — it doesn\'t look like a dive log');
      } else {
        result.errors.push('no dive session found in this FIT file');
      }
      return result;
    }

    // apnea files log one dive per lap; everything else is one dive per session
    const session = diveSessions[0] || sessions[0];
    const subSport = session && String(session.subSport || '');
    const diveType = APNEA.test(subSport) ? 'freedive' : 'scuba';
    const lapSummaries = summaries.filter((s) => s.referenceMesg === 'lap');

    try {
      if (diveType === 'freedive' && lapSummaries.length && laps.length) {
        lapSummaries.forEach((summary, i) => {
          const lap = laps[summary.referenceIndex] || laps[i];
          if (!lap || !(lap.startTime instanceof Date)) return;
          const startTime = lap.startTime;
          const endMs = startTime.getTime() + (lap.totalElapsedTime || 0) * 1000;
          const lapRecords = records.filter((r) => r.timestamp instanceof Date && r.timestamp.getTime() >= startTime.getTime() && r.timestamp.getTime() <= endMs);
          result.dives.push(buildDive({
            startTime,
            durationSec: summary.bottomTime !== undefined ? summary.bottomTime : lap.totalElapsedTime,
            summary, records: lapRecords, offsetSec, tanks: [], fileId, diveType,
          }));
        });
      } else {
        const startTime = (session && session.startTime) || (records[0] && records[0].timestamp);
        const summary = summaries.find((s) => s.referenceMesg === 'session') || summaries[0];
        result.dives.push(buildDive({
          startTime,
          durationSec: (summary && summary.bottomTime) !== undefined ? summary.bottomTime
            : session && (session.totalTimerTime || session.totalElapsedTime),
          summary, records, offsetSec, tanks, fileId, diveType,
        }));
      }
    } catch (e) {
      result.errors.push(`could not read the dive out of this FIT file: ${e.message}`);
      return result;
    }

    if (!result.dives.length) result.errors.push('no dives found in this FIT file');
    return result;
  },
};
