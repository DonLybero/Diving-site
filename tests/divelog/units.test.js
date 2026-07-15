import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatDepth, formatTemp, formatPressure, formatVolume, formatDuration, formatHours } from '../../lib/divelog/units.js';

test('metric formatting', () => {
  assert.equal(formatDepth(18.24), '18.2 m');
  assert.equal(formatTemp(24.06), '24.1°C');
  assert.equal(formatPressure(200.4), '200 bar');
  assert.equal(formatVolume(11.1), '11.1 L');
});

test('imperial formatting', () => {
  assert.equal(formatDepth(18.2, 'imperial'), '60 ft');
  assert.equal(formatTemp(24, 'imperial'), '75°F');
  assert.equal(formatPressure(200, 'imperial'), '2901 psi');
  assert.equal(formatVolume(11.1, 'imperial'), '0.4 cuft');
});

test('duration and hours', () => {
  assert.equal(formatDuration(2880), '48 min');
  assert.equal(formatDuration(4380), '1 h 13 min');
  assert.equal(formatDuration(0), '—');
  assert.equal(formatHours(315000), '87.5 h');
  assert.equal(formatHours(0), '0 h');
});

test('missing values render an em dash', () => {
  assert.equal(formatDepth(undefined), '—');
  assert.equal(formatTemp(NaN), '—');
  assert.equal(formatPressure(undefined, 'imperial'), '—');
});
