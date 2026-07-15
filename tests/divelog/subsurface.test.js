import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { subsurfaceParser } from '../../lib/divelog/parsers/subsurface.js';
import { exportUddf } from '../../lib/divelog/export-uddf.js';
import { uddfParser } from '../../lib/divelog/parsers/uddf.js';
import { detectFormat } from '../../lib/divelog/parsers/index.js';
import { decodeText } from '../../lib/divelog/encoding.js';

const FIXTURE = new URL('../../test-fixtures/subsurface-two-dives.ssrf', import.meta.url);
const bytes = () => new Uint8Array(readFileSync(FIXTURE));
const text = () => decodeText(bytes());

test('sniffs .ssrf/.xml and requires the subsurface program marker', () => {
  assert.ok(subsurfaceParser.sniff(bytes(), text()));
  assert.equal(detectFormat(bytes(), 'logbook.ssrf').parser.id, 'subsurface');
  assert.equal(detectFormat(bytes(), 'logbook.xml').parser.id, 'subsurface');
  const notSubsurface = `<divelog program='other' version='3'><dives/></divelog>`;
  assert.ok(!subsurfaceParser.sniff(new TextEncoder().encode(notSubsurface), notSubsurface));
});

test('parses the two-dive fixture with unit-suffixed attributes', () => {
  const res = subsurfaceParser.parse(bytes(), text());
  assert.deepEqual(res.errors, []);
  assert.equal(res.dives.length, 2);

  const [d1, d2] = res.dives;
  assert.equal(d1.number, 94);
  assert.equal(d1.startedAt, '2011-10-21T12:58:49');
  assert.equal(d1.durationSec, 65 * 60 + 36); // '65:36 min' — minutes past 59
  assert.equal(d1.maxDepthM, 36.01);
  assert.equal(d1.avgDepthM, 20.217);
  assert.equal(d1.waterTempC, 25.2); // from divecomputer <temperature>
  assert.equal(d1.airTempC, 27.5);
  assert.equal(d1.site.name, 'Zenobia, Larnaca, Cyprus');
  assert.equal(d1.site.lat, 34.897333);
  assert.equal(d1.buddy, 'Linus, Scott');
  assert.equal(d1.diveMaster, 'Jason');
  assert.equal(d1.equipment, 'wet, 5mm');
  assert.equal(d1.tanks.length, 2);
  assert.deepEqual(d1.tanks[0], { volumeL: 24, startBar: 200, endBar: 68, gasO2Pct: 32 });
  assert.equal(d1.tanks[1].gasO2Pct, 51);
  assert.equal(d1.source.computerModel, 'Shearwater Petrel');
  assert.equal(d1.samples.length, 8);
  assert.deepEqual(d1.samples[0], { tSec: 6, depthM: 2.38, tempC: 27.5, pressureBar: 196.14 });
  assert.equal(d1.samples[2].tempC, undefined); // delta-encoded: only present on change
  assert.equal(d1.samples[7].tSec, 65 * 60 + 36);

  assert.equal(d2.waterTempC, 11); // dive-level <divetemperature> wins
  assert.equal(d2.airTempC, 18);
  assert.equal(d2.site.name, 'Sund Rock, Hoodsport, WA, USA');
  assert.equal(d2.site.lon, -123.142299);
  assert.equal(d2.samples.length, 6);
});

test('cylinder without o2 attribute means air', () => {
  const xml = `<divelog program='subsurface' version='3'><dives>
    <dive number='1' date='2020-01-05' time='10:00:00' duration='40:00 min'>
      <cylinder size='11.1 l' start='200.0 bar' end='60.0 bar'/>
      <divecomputer model='X'><depth max='18.0 m'/></divecomputer>
    </dive></dives></divelog>`;
  const res = subsurfaceParser.parse(new TextEncoder().encode(xml), xml);
  assert.equal(res.dives[0].tanks[0].gasO2Pct, 21);
});

test('dives wrapped in trips are found', () => {
  const xml = `<divelog program='subsurface' version='3'><dives>
    <trip date='2020-01-05' location='Red Sea'>
      <dive number='1' date='2020-01-05' time='10:00:00' duration='40:00 min'><divecomputer model='X'><depth max='18.0 m'/></divecomputer></dive>
      <dive number='2' date='2020-01-05' time='14:00:00' duration='50:00 min'><divecomputer model='X'><depth max='22.0 m'/></divecomputer></dive>
    </trip>
    <dive number='3' date='2020-01-07' time='09:00:00' duration='45:00 min'><divecomputer model='X'><depth max='30.0 m'/></divecomputer></dive>
  </dives></divelog>`;
  const res = subsurfaceParser.parse(new TextEncoder().encode(xml), xml);
  assert.equal(res.dives.length, 3);
  assert.deepEqual(res.dives.map((d) => d.number), [1, 2, 3]);
});

test('legacy pressure spelling pressure0 and dctype freedive', () => {
  const xml = `<divelog program='subsurface' version='3'><dives>
    <dive number='1' date='2020-01-05' time='10:00:00' duration='2:00 min'>
      <divecomputer model='X' dctype='Freedive'>
      <sample time='0:30 min' depth='12.0 m' pressure0='180.0 bar'/>
      <sample time='120' depth='0.5 m'/>
      </divecomputer>
    </dive></dives></divelog>`;
  const res = subsurfaceParser.parse(new TextEncoder().encode(xml), xml);
  assert.equal(res.dives[0].diveType, 'freedive');
  assert.equal(res.dives[0].samples[0].pressureBar, 180);
  assert.equal(res.dives[0].samples[1].tSec, 120); // bare number = seconds
});

test('a dive without a date is salvaged around', () => {
  const broken = text().replace(`date='2011-10-22' `, '');
  const res = subsurfaceParser.parse(new TextEncoder().encode(broken), broken);
  assert.equal(res.dives.length, 1);
  assert.ok(res.warnings.some((w) => /no date/.test(w)));
});

test('subsurface dives survive UDDF export → re-import', () => {
  const dives = subsurfaceParser.parse(bytes(), text()).dives;
  const xml = exportUddf(dives, { generatedAt: '2026-07-15T12:00:00' });
  const rt = uddfParser.parse(new TextEncoder().encode(xml), xml);
  assert.deepEqual(rt.errors, []);
  assert.equal(rt.dives.length, 2);
  assert.equal(rt.dives[0].startedAt, '2011-10-21T12:58:49');
  assert.equal(rt.dives[0].maxDepthM, 36.01);
  assert.equal(rt.dives[0].samples.length, 8);
  assert.equal(rt.dives[0].tanks.length, 2);
});
