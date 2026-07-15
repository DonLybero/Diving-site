import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isDuplicate, findDuplicates } from '../../lib/divelog/dedupe.js';

const dive = (startedAt, durationSec, extra = {}) => ({ startedAt, durationSec, ...extra });

test('duplicate within ±3 min start and ±2 min duration', () => {
  const a = dive('2025-03-12T09:30:00', 2880);
  assert.ok(isDuplicate(a, dive('2025-03-12T09:30:00', 2880)));
  assert.ok(isDuplicate(a, dive('2025-03-12T09:32:59', 2880)));
  assert.ok(isDuplicate(a, dive('2025-03-12T09:27:01', 2999)));
  assert.ok(!isDuplicate(a, dive('2025-03-12T09:33:01', 2880))); // start 181 s off
  assert.ok(!isDuplicate(a, dive('2025-03-12T09:30:00', 3001))); // duration 121 s off
});

test('findDuplicates against existing logbook', () => {
  const existing = [dive('2025-03-12T09:30:00', 2880, { id: 'e1' }), dive('2025-03-13T10:00:00', 3000, { id: 'e2' })];
  const candidates = [
    dive('2025-03-12T09:31:00', 2900), // dup of e1
    dive('2025-03-14T09:30:00', 2880), // new
    dive('2025-03-13T10:02:00', 2940), // dup of e2
  ];
  const flags = findDuplicates(candidates, existing);
  assert.equal(flags[0].kind, 'existing');
  assert.equal(flags[0].match.id, 'e1');
  assert.equal(flags[1], null);
  assert.equal(flags[2].kind, 'existing');
  assert.equal(flags[2].match.id, 'e2');
});

test('findDuplicates flags repeats within the same batch', () => {
  const candidates = [
    dive('2025-03-12T09:30:00', 2880),
    dive('2025-03-12T09:30:30', 2880), // same dive listed twice in one file
    dive('2025-03-12T14:00:00', 2400),
  ];
  const flags = findDuplicates(candidates, []);
  assert.equal(flags[0], null);
  assert.deepEqual(flags[1], { kind: 'batch', index: 0 });
  assert.equal(flags[2], null);
});

test('invalid dates never match', () => {
  const flags = findDuplicates([dive('garbage', 2880)], [dive('2025-03-12T09:30:00', 2880)]);
  assert.equal(flags[0], null);
});

test('same dive with UTC offset vs naive wall time still matches', () => {
  // Shearwater UDDF writes offsets, Subsurface writes naive local — same dive
  const offset = dive('2025-03-12T09:30:00+07:00', 2880);
  const naive = dive('2025-03-12T09:30:00', 2880);
  assert.ok(isDuplicate(offset, naive));
  const flags = findDuplicates([naive], [offset]);
  assert.equal(flags[0].kind, 'existing');
});

test('date-only (midnight) dives need exact duration + depth to be duplicates', () => {
  const a = dive('2024-05-05T00:00:00', 45 * 60, { maxDepthM: 18 });
  const b = dive('2024-05-05T00:00:00', 46 * 60, { maxDepthM: 22 }); // distinct same-day dive
  assert.ok(!isDuplicate(a, b));
  const rerun = dive('2024-05-05T00:00:00', 45 * 60, { maxDepthM: 18 }); // true re-import
  assert.ok(isDuplicate(a, rerun));
  const flags = findDuplicates([b, rerun], [a]);
  assert.equal(flags[0], null);
  assert.equal(flags[1].kind, 'existing');
});

test('scales: 500 candidates against 1000 existing', () => {
  const existing = Array.from({ length: 1000 }, (_, i) => dive(new Date(Date.UTC(2020, 0, 1 + i, 10)).toISOString(), 3000));
  const candidates = Array.from({ length: 500 }, (_, i) => dive(new Date(Date.UTC(2020, 0, 1 + i * 2, 10)).toISOString(), 3000));
  const flags = findDuplicates(candidates, existing);
  assert.ok(flags.every((f) => f && f.kind === 'existing'));
});
