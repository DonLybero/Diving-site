import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { uddfParser } from '../../lib/divelog/parsers/uddf.js';
import { exportUddf } from '../../lib/divelog/export-uddf.js';
import { detectFormat } from '../../lib/divelog/parsers/index.js';
import { preparePreview, commitImport } from '../../lib/divelog/pipeline.js';
import { MemoryStore } from '../../lib/divelog/store.js';
import { decodeText } from '../../lib/divelog/encoding.js';

const FIXTURE = new URL('../../test-fixtures/uddf-two-dives.uddf', import.meta.url);
const bytes = () => new Uint8Array(readFileSync(FIXTURE));
const text = () => decodeText(bytes());

test('sniffs and detects .uddf', () => {
  assert.ok(uddfParser.sniff(bytes(), text()));
  const det = detectFormat(bytes(), 'log.uddf');
  assert.equal(det.parser.id, 'uddf');
  // extension lies, content wins
  assert.equal(detectFormat(bytes(), 'log.csv').parser.id, 'uddf');
});

test('parses the two-dive fixture with SI conversions', () => {
  const res = uddfParser.parse(bytes(), text());
  assert.deepEqual(res.errors, []);
  assert.equal(res.dives.length, 2);

  const [d1, d2] = res.dives;
  assert.equal(d1.number, 42);
  assert.equal(d1.startedAt, '2026-03-14T09:30:00');
  assert.equal(d1.durationSec, 2700);
  assert.equal(d1.maxDepthM, 24.6);
  assert.equal(d1.avgDepthM, 14.3);
  assert.equal(Math.round(d1.waterTempC), 27);          // 300.15 K
  assert.equal(Math.round(d1.airTempC), 28);            // 301.15 K
  assert.equal(d1.site.name, 'Blue Corner');
  assert.equal(d1.site.lat, 7.1345);
  assert.equal(d1.buddy, 'Maria Santos');
  assert.match(d1.notes, /grey reef sharks/);
  assert.equal(d1.tanks.length, 1);
  assert.equal(d1.tanks[0].gasO2Pct, 32);               // 0.32 fraction
  assert.equal(d1.tanks[0].volumeL, 12);                // 0.012 m³
  assert.equal(d1.tanks[0].startBar, 200);              // 20 MPa
  assert.equal(d1.tanks[0].endBar, 65);
  assert.equal(d1.samples.length, 5);
  assert.equal(d1.samples[2].depthM, 24.6);
  assert.equal(d1.samples[2].pressureBar, 154);
  assert.equal(Math.round(d1.samples[2].tempC), 27);
  assert.equal(d1.source.externalId, 'dive_1');

  assert.equal(d2.number, 43);
  assert.equal(d2.tanks[0].gasO2Pct, 21);
  assert.equal(d2.samples.length, 3);
});

test('a malformed dive is salvaged around, not fatal', () => {
  const broken = text().replace('<datetime>2026-03-14T14:05:00</datetime>', '');
  const res = uddfParser.parse(new TextEncoder().encode(broken), broken);
  assert.equal(res.dives.length, 1);
  assert.ok(res.warnings.some((w) => /no date\/time/.test(w)));
  assert.deepEqual(res.errors, []);
});

test('empty profiledata reports a file-level error', () => {
  const empty = '<?xml version="1.0"?><uddf xmlns="http://www.streit.cc/uddf/3.2/" version="3.2.1"><profiledata/></uddf>';
  const res = uddfParser.parse(new TextEncoder().encode(empty), empty);
  assert.equal(res.dives.length, 0);
});

test('round trip: export → re-parse preserves the data that matters', () => {
  const parsed = uddfParser.parse(bytes(), text()).dives;
  const xml = exportUddf(parsed, { generatedAt: '2026-07-15T12:00:00' });
  const rt = uddfParser.parse(new TextEncoder().encode(xml), xml);
  assert.deepEqual(rt.errors, []);
  assert.equal(rt.dives.length, 2);
  for (let i = 0; i < 2; i++) {
    const a = parsed[i], b = rt.dives[i];
    assert.equal(b.startedAt, a.startedAt);
    assert.equal(b.durationSec, a.durationSec);
    assert.equal(b.maxDepthM, a.maxDepthM);
    assert.equal(b.number, a.number);
    assert.equal(b.site?.name, a.site?.name);
    assert.equal(b.buddy, a.buddy);
    assert.equal(b.notes, a.notes);
    assert.equal((b.samples || []).length, (a.samples || []).length);
    assert.equal(b.tanks?.[0]?.gasO2Pct, a.tanks?.[0]?.gasO2Pct);
    assert.ok(Math.abs((b.waterTempC ?? -999) - (a.waterTempC ?? -999)) < 0.01);
  }
});

test('full pipeline round trip: import, export, re-import → 100% duplicates', async () => {
  const store = new MemoryStore();
  const preview = await preparePreview({ bytes: bytes(), fileName: 'log.uddf', store });
  assert.equal(preview.ok, true);
  assert.equal(preview.counts.new, 2);
  await commitImport({ entries: preview.entries, store, fileName: 'log.uddf', parserId: 'uddf' });
  assert.equal((await store.listDives()).length, 2);

  // exporting the logbook and importing the export must yield zero new dives
  const xml = exportUddf(await store.listDives(), { generatedAt: '2026-07-15T12:00:00' });
  const again = await preparePreview({ bytes: new TextEncoder().encode(xml), fileName: 'diveszn-export.uddf', store });
  assert.equal(again.ok, true);
  assert.equal(again.counts.new, 0);
  assert.equal(again.counts.duplicates, 2);
  assert.ok(again.entries.every((e) => e.include === false));

  // committing the default preview adds nothing
  await commitImport({ entries: again.entries, store, fileName: 'diveszn-export.uddf', parserId: 'uddf' });
  assert.equal((await store.listDives()).length, 2);
});

test('exported document is well-formed, escaped, and DTD-free', () => {
  const nasty = [{
    startedAt: '2025-01-01T10:00:00',
    durationSec: 1800,
    maxDepthM: 10,
    diveType: 'scuba',
    visibility: 'private',
    site: { name: `Jake's <Plane> & "Wreck"` },
    notes: 'a < b & c > d',
    buddy: 'O’Neil',
  }];
  const xml = exportUddf(nasty, { generatedAt: '2026-07-15T12:00:00' });
  assert.ok(!/<!DOCTYPE/i.test(xml));
  const rt = uddfParser.parse(new TextEncoder().encode(xml), xml);
  assert.deepEqual(rt.errors, []);
  assert.equal(rt.dives[0].site.name, `Jake's <Plane> & "Wreck"`);
  assert.equal(rt.dives[0].notes, 'a < b & c > d');
});
