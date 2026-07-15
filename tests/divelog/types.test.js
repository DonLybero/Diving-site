import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateDive, LIMITS } from '../../lib/divelog/types.js';

test('normalizes a complete dive', () => {
  const { dive, problems } = validateDive({
    number: 42,
    startedAt: '2025-03-12T09:30:00',
    durationSec: 2880,
    maxDepthM: 18.234,
    waterTempC: 24.05,
    site: { name: ' Blue Hole ', lat: 28.572, lon: 34.537, country: 'Egypt' },
    buddy: 'Sam',
    tanks: [{ volumeL: 11.1, startBar: 200, endBar: 50, gasO2Pct: 32 }],
    samples: [
      { tSec: 10, depthM: 2.5 },
      { tSec: 0, depthM: 0 },
      { tSec: 20, depthM: 5.1, tempC: 24, pressureBar: 195 },
    ],
  });
  assert.equal(problems.length, 0);
  assert.equal(dive.number, 42);
  assert.equal(dive.maxDepthM, 18.23);
  assert.equal(dive.site.name, 'Blue Hole');
  assert.equal(dive.diveType, 'scuba');
  assert.equal(dive.visibility, 'private');
  assert.deepEqual(dive.samples.map((s) => s.tSec), [0, 10, 20]); // sorted
});

test('rejects a dive with no usable date', () => {
  assert.equal(validateDive({ durationSec: 2880 }).dive, null);
  assert.equal(validateDive({ startedAt: 'yesterday-ish', durationSec: 2880 }).dive, null);
});

test('derives duration and max depth from samples when missing', () => {
  const { dive, problems } = validateDive({
    startedAt: '2025-03-12T09:30:00',
    samples: [{ tSec: 0, depthM: 0 }, { tSec: 1200, depthM: 17.8 }, { tSec: 2400, depthM: 4 }],
  });
  assert.equal(dive.durationSec, 2400);
  assert.equal(dive.maxDepthM, 17.8);
  assert.equal(problems.length, 2);
});

test('keeps a sparse manual dive but records what is missing', () => {
  const { dive, problems } = validateDive({ startedAt: '2020-07-01T10:00:00', durationSec: 3000 });
  assert.ok(dive);
  assert.ok(problems.some((p) => /max depth/.test(p)));
});

test('drops junk fields instead of failing the dive', () => {
  const { dive } = validateDive({
    startedAt: '2025-03-12T09:30:00',
    durationSec: 2880,
    maxDepthM: 18,
    waterTempC: 400,           // implausible → dropped
    site: { name: 'X', lat: 999, lon: 34 }, // bad coords → name kept, coords dropped
    tanks: [{}, { startBar: 5000 }],        // junk tanks → dropped
  });
  assert.equal(dive.waterTempC, undefined);
  assert.equal(dive.site.lat, undefined);
  assert.equal(dive.tanks, undefined);
});

test('caps oversized inputs', () => {
  const samples = Array.from({ length: LIMITS.maxSamplesPerDive + 50 }, (_, i) => ({ tSec: i, depthM: 10 }));
  const { dive, problems } = validateDive({ startedAt: '2025-03-12T09:30:00', durationSec: 2880, maxDepthM: 10, samples });
  assert.equal(dive.samples.length, LIMITS.maxSamplesPerDive);
  assert.ok(problems.some((p) => /truncated/.test(p)));
  const { dive: d2 } = validateDive({ startedAt: '2025-03-12T09:30:00', durationSec: 60, notes: 'x'.repeat(LIMITS.maxStringLen + 500) });
  assert.equal(d2.notes.length, LIMITS.maxStringLen);
});
