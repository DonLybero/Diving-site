import { test } from 'node:test';
import assert from 'node:assert/strict';
import { detectFormat } from '../../lib/divelog/parsers/index.js';
import { preparePreview } from '../../lib/divelog/pipeline.js';
import { MemoryStore } from '../../lib/divelog/store.js';
import { LIMITS } from '../../lib/divelog/types.js';

const utf8 = (s) => new TextEncoder().encode(s);

test('empty file is rejected with a clear message', () => {
  assert.match(detectFormat(new Uint8Array(0), 'log.uddf').error, /empty/);
});

test('Garmin FIT magic routes to the garmin-fit parser', () => {
  const fit = new Uint8Array(32);
  fit.set([0x0e, 0x10, 0x8b, 0x07], 0);
  fit.set([0x2e, 0x46, 0x49, 0x54], 8); // '.FIT'
  const det = detectFormat(fit, 'activity.fit');
  assert.equal(det.parser.id, 'garmin-fit');
});

test('zip (SDE) and SQLite files get pointed to the right export', () => {
  const zip = utf8('PK\x03\x04rest-of-zip\x00\x00');
  assert.match(detectFormat(zip, 'backup.sde').error, /zip archive/i);
  const db = utf8('SQLite format 3\x00more');
  assert.match(detectFormat(db, 'shearwater.db').error, /Shearwater/);
});

test('unknown XML names its root element', () => {
  const { error } = detectFormat(utf8('<?xml version="1.0"?><gpx creator="x"><trk/></gpx>'), 'hike.xml');
  assert.match(error, /<gpx>/);
});

test('pipeline enforces the 20 MB limit before parsing', async () => {
  const big = new Uint8Array(LIMITS.maxFileBytes + 1);
  big.fill(97);
  const res = await preparePreview({ bytes: big, fileName: 'huge.csv', store: new MemoryStore() });
  assert.equal(res.ok, false);
  assert.match(res.error, /limit is 20 MB/);
});

test('pipeline surfaces empty-file error', async () => {
  const res = await preparePreview({ bytes: new Uint8Array(0), fileName: 'log.uddf', store: new MemoryStore() });
  assert.equal(res.ok, false);
  assert.match(res.error, /empty/);
});
