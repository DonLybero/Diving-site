import { test } from 'node:test';
import assert from 'node:assert/strict';
import { num, kelvinToC, pascalToBar, parseDuration, parseDateTime } from '../../lib/divelog/values.js';

test('num handles unit suffixes, decimal comma, junk', () => {
  assert.equal(num('18.2 m'), 18.2);
  assert.equal(num('32,0'), 32);
  assert.equal(num('200.0 bar'), 200);
  assert.equal(num('-1.5'), -1.5);
  assert.equal(num(7), 7);
  assert.equal(num('1,234.5'), 1); // ambiguous thousands separators are not guessed
  assert.equal(num(''), undefined);
  assert.equal(num('abc'), undefined);
  assert.equal(num(undefined), undefined);
});

test('kelvin and pascal conversions', () => {
  assert.equal(Math.round(kelvinToC('297.15') * 10) / 10, 24);
  assert.equal(kelvinToC('0'), undefined); // 0 K = not recorded
  assert.equal(pascalToBar('20000000'), 200);
});

test('parseDuration formats', () => {
  assert.equal(parseDuration('48:30 min'), 48 * 60 + 30);
  assert.equal(parseDuration('1:02:30'), 3750);
  assert.equal(parseDuration('48 min'), 2880);
  assert.equal(parseDuration('2880 s'), 2880);
  assert.equal(parseDuration('48', 'min'), 2880);
  assert.equal(parseDuration('2880', 'sec'), 2880);
  assert.equal(parseDuration(48), 2880);   // bare small number → minutes
  assert.equal(parseDuration(2880), 2880); // bare large number → seconds
  assert.equal(parseDuration('junk'), undefined);
});

test('parseDateTime ISO with and without offset', () => {
  assert.equal(parseDateTime('2025-03-12T09:30:00+02:00'), '2025-03-12T09:30:00+02:00');
  assert.equal(parseDateTime('2025-03-12T09:30:00Z'), '2025-03-12T09:30:00Z');
  assert.equal(parseDateTime('2025-03-12 09:30:00'), '2025-03-12T09:30:00');
  assert.equal(parseDateTime('2025-03-12T09:30'), '2025-03-12T09:30:00'); // seconds optional
});

test('parseDateTime separate date + time, regional formats', () => {
  assert.equal(parseDateTime('2025-03-12', '09:30'), '2025-03-12T09:30:00');
  assert.equal(parseDateTime('12.03.2025', '9:30:15'), '2025-03-12T09:30:15');
  assert.equal(parseDateTime('12/03/2025', '09:30'), '2025-03-12T09:30:00'); // dayFirst default
  assert.equal(parseDateTime('03/12/2025', '09:30', { dayFirst: false }), '2025-03-12T09:30:00');
  assert.equal(parseDateTime('25/03/2025'), '2025-03-25T00:00:00'); // >12 disambiguates
  assert.equal(parseDateTime('12 Mar 2025', '2:05 pm'), '2025-03-12T14:05:00');
  assert.equal(parseDateTime('Mar 12, 2025'), '2025-03-12T00:00:00');
  assert.equal(parseDateTime('not a date'), undefined);
});
