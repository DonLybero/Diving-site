// Hostile-input acceptance tests (PRD §9–§11): every fixture here must be
// rejected or salvaged with a clear message, fast, and with zero entity
// resolution — through the same pipeline the UI calls.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { preparePreview, commitImport } from '../../lib/divelog/pipeline.js';
import { MemoryStore } from '../../lib/divelog/store.js';
import { exportUddf } from '../../lib/divelog/export-uddf.js';

const hostile = (name) => new Uint8Array(readFileSync(new URL(`../../test-fixtures/hostile/${name}`, import.meta.url)));
const store = () => new MemoryStore();

test('XXE payload is rejected before parsing; entities never resolve', async () => {
  const res = await preparePreview({ bytes: hostile('xxe.uddf'), fileName: 'xxe.uddf', store: store() });
  assert.equal(res.ok, false);
  assert.match(res.error, /DTD\/ENTITY/);
  assert.doesNotMatch(res.error, /passwd/);
});

test('billion-laughs is rejected instantly by the same guard', async () => {
  const t0 = performance.now();
  const res = await preparePreview({ bytes: hostile('billion-laughs.xml'), fileName: 'divelog.xml', store: store() });
  assert.equal(res.ok, false);
  assert.match(res.error, /DTD\/ENTITY/);
  assert.ok(performance.now() - t0 < 200, 'rejection must not expand entities');
});

test('truncated file names the format and the malformation', async () => {
  const res = await preparePreview({ bytes: hostile('truncated.uddf'), fileName: 'truncated.uddf', store: store() });
  assert.equal(res.ok, false);
  assert.match(res.error, /malformed XML/);
});

test('CSV content behind a .uddf extension: sniffing wins over the extension', async () => {
  const res = await preparePreview({ bytes: hostile('actually-csv.uddf'), fileName: 'actually-csv.uddf', store: store() });
  assert.equal(res.ok, true);
  assert.equal(res.parser.id, 'csv');
  assert.equal(res.counts.new, 2);
});

test('random binary garbage gets the generic guidance message', async () => {
  const bytes = new Uint8Array(512).map((_, i) => (i * 37 + 11) % 251);
  bytes[3] = 0; // ensure a NUL
  const res = await preparePreview({ bytes, fileName: 'mystery.log', store: store() });
  assert.equal(res.ok, false);
  assert.match(res.error, /Export from your dive app/);
});

test('deeply nested XML does not crash the parser', async () => {
  const depth = 5000;
  const xml = '<uddf version="3.2.1">' + '<a>'.repeat(depth) + '<b/>' + '</a>'.repeat(depth) + '</uddf>';
  const res = await preparePreview({ bytes: new TextEncoder().encode(xml), fileName: 'deep.uddf', store: store() });
  assert.equal(res.ok, false); // no dives — but no crash, and a real message
  assert.ok(res.error);
});

test('500-dive logbook round-trips through export/import at speed', async () => {
  const dives = Array.from({ length: 500 }, (_, i) => {
    const day = new Date(Date.UTC(2020, 0, 1 + Math.floor(i / 2), 9 + (i % 2) * 5));
    return {
      id: `d${i}`,
      number: i + 1,
      startedAt: day.toISOString().slice(0, 19),
      durationSec: 2400 + (i % 30) * 60,
      maxDepthM: 10 + (i % 25),
      diveType: 'scuba',
      visibility: 'private',
      site: { name: `Site ${i % 40}` },
      samples: Array.from({ length: 120 }, (_, t) => ({ tSec: t * 20, depthM: Math.max(0, Math.sin(t / 20) * (10 + (i % 25))) })),
    };
  });
  const t0 = performance.now();
  const xml = exportUddf(dives, { generatedAt: '2026-07-15T12:00:00' });
  const st = store();
  const preview = await preparePreview({ bytes: new TextEncoder().encode(xml), fileName: 'big.uddf', store: st });
  const elapsed = performance.now() - t0;
  assert.equal(preview.ok, true);
  assert.equal(preview.counts.new, 500);
  assert.ok(elapsed < 10000, `500-dive export+import took ${Math.round(elapsed)}ms`);

  await commitImport({ entries: preview.entries, store: st, fileName: 'big.uddf', parserId: 'uddf' });
  const again = await preparePreview({ bytes: new TextEncoder().encode(xml), fileName: 'big.uddf', store: st });
  assert.equal(again.counts.duplicates, 500);
});

test('a file with more dives than the cap is truncated with a warning', async () => {
  const header = 'Date,Duration\n';
  const rows = Array.from({ length: 5010 }, (_, i) => `2020-01-01,${30 + (i % 60)}\n`).join('');
  const res = await preparePreview({ bytes: new TextEncoder().encode(header + rows), fileName: 'huge.csv', store: store() });
  assert.equal(res.ok, true);
  assert.ok(res.warnings.some((w) => /only the first 5000/.test(w)));
  assert.equal(res.entries.length <= 5000, true);
});

test('single-dive minimal UDDF imports', async () => {
  const xml = `<uddf version="3.2.1"><profiledata><repetitiongroup><dive id="x">
    <informationbeforedive><datetime>2025-01-01T10:00:00</datetime></informationbeforedive>
    <informationafterdive><greatestdepth>10</greatestdepth><diveduration>1200</diveduration></informationafterdive>
  </dive></repetitiongroup></profiledata></uddf>`;
  const res = await preparePreview({ bytes: new TextEncoder().encode(xml), fileName: 'one.uddf', store: store() });
  assert.equal(res.ok, true);
  assert.equal(res.counts.new, 1);
});

test('zero-dive UDDF says so plainly', async () => {
  const xml = '<uddf version="3.2.1"><profiledata><repetitiongroup></repetitiongroup></profiledata></uddf>';
  const res = await preparePreview({ bytes: new TextEncoder().encode(xml), fileName: 'empty-log.uddf', store: store() });
  assert.equal(res.ok, false);
  assert.match(res.error, /no dives found/);
});
