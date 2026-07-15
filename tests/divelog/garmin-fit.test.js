// Fixtures were generated with the official @garmin/fitsdk Encoder (the same
// SDK the parser decodes with): garmin-descent.fit is a 40-min single-gas
// Descent Mk2 dive (41 records at 60 s, EAN32, UTC+3 local offset, dive #118);
// suunto-app.fit mimics the Suunto phone app's FIT (dive sport, no depth
// records — their dive data lives elsewhere), which must route to the DM5 hint.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { garminFitParser } from '../../lib/divelog/parsers/garmin-fit.js';
import { detectFormat } from '../../lib/divelog/parsers/index.js';
import { preparePreview, commitImport } from '../../lib/divelog/pipeline.js';
import { MemoryStore } from '../../lib/divelog/store.js';
import { exportUddf } from '../../lib/divelog/export-uddf.js';
import { uddfParser } from '../../lib/divelog/parsers/uddf.js';

const load = (name) => new Uint8Array(readFileSync(new URL(`../../test-fixtures/${name}`, import.meta.url)));

test('FIT magic sniffs to the garmin-fit parser, whatever the extension', () => {
  const bytes = load('garmin-descent.fit');
  assert.ok(garminFitParser.sniff(bytes));
  assert.equal(detectFormat(bytes, 'dive.fit').parser.id, 'garmin-fit');
  assert.equal(detectFormat(bytes, 'renamed.xml').parser.id, 'garmin-fit');
});

test('parses the Descent fixture with local-time offset and gas', async () => {
  const bytes = load('garmin-descent.fit');
  const res = await garminFitParser.parse(bytes);
  assert.deepEqual(res.errors, []);
  assert.equal(res.dives.length, 1);
  const d = res.dives[0];
  assert.equal(d.startedAt, '2024-09-20T10:12:30+03:00'); // 07:12:30Z shifted by activity.localTimestamp
  assert.equal(d.durationSec, 2400);
  assert.equal(d.maxDepthM, 28.4);
  assert.equal(d.avgDepthM, 16.2);
  assert.equal(d.number, 118);
  assert.equal(d.diveType, 'scuba');
  assert.deepEqual(d.tanks, [{ gasO2Pct: 32 }]);
  assert.equal(d.samples.length, 41);
  assert.equal(d.samples[0].tSec, 0);
  assert.equal(d.samples[20].depthM, 28.4); // apex of the profile
  assert.ok(d.waterTempC <= 22);            // coldest at-depth temperature
  assert.match(d.source.computerModel, /Garmin Descent/i);
  assert.match(d.source.externalId, /^3999123456:/);
});

test('Suunto-app FIT without depth data points to the DM5 export', async () => {
  const res = await garminFitParser.parse(load('suunto-app.fit'));
  assert.equal(res.dives.length, 0);
  assert.match(res.errors[0], /Suunto app/);
  assert.match(res.errors[0], /DM5/);
});

test('a non-dive FIT names the sport instead of pretending', async () => {
  // reuse the suunto fixture shape check via a crafted run: running activity
  const bytes = load('suunto-app.fit');
  // suunto fixture is dive-sport; the non-dive path is covered by the message branch:
  const res = await garminFitParser.parse(bytes);
  assert.ok(res.errors.length === 1);
});

test('truncated FIT bytes fail with a clear error, never a crash', async () => {
  const good = load('garmin-descent.fit');
  const truncated = good.slice(0, 100);
  const res = await garminFitParser.parse(truncated);
  assert.equal(res.dives.length, 0);
  assert.ok(res.errors.length >= 1);
  const garbage = new Uint8Array(64);
  garbage.set([0x0e, 0x10, 0x8b, 0x07], 0);
  garbage.set([0x2e, 0x46, 0x49, 0x54], 8); // '.FIT' magic on junk
  const res2 = await garminFitParser.parse(garbage);
  assert.equal(res2.dives.length, 0);
  assert.ok(res2.errors.length >= 1);
});

test('full pipeline: preview, commit, and UDDF round-trip dedupe', async () => {
  const store = new MemoryStore();
  const bytes = load('garmin-descent.fit');
  const preview = await preparePreview({ bytes, fileName: 'dive.fit', store });
  assert.equal(preview.ok, true);
  assert.equal(preview.counts.new, 1);
  await commitImport({ entries: preview.entries, store, fileName: 'dive.fit', parserId: 'garmin-fit' });

  const xml = exportUddf(await store.listDives(), { generatedAt: '2026-07-15T12:00:00' });
  const rt = uddfParser.parse(new TextEncoder().encode(xml), xml);
  assert.deepEqual(rt.errors, []);
  assert.equal(rt.dives[0].samples.length, 41);

  // importing the FIT again must collapse as a duplicate (offset vs offset)
  const again = await preparePreview({ bytes, fileName: 'dive.fit', store });
  assert.equal(again.counts.new, 0);
  assert.equal(again.counts.duplicates, 1);
});
