import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { suuntoSmlParser } from '../../lib/divelog/parsers/suunto-sml.js';
import { detectFormat } from '../../lib/divelog/parsers/index.js';
import { exportUddf } from '../../lib/divelog/export-uddf.js';
import { uddfParser } from '../../lib/divelog/parsers/uddf.js';
import { decodeText } from '../../lib/divelog/encoding.js';

const FIXTURE = new URL('../../test-fixtures/suunto-dm5.sml', import.meta.url);
const bytes = () => new Uint8Array(readFileSync(FIXTURE));
const text = () => decodeText(bytes());

test('sniffs .sml by root element + Suunto namespace', () => {
  assert.ok(suuntoSmlParser.sniff(bytes(), text()));
  assert.equal(detectFormat(bytes(), '3602896-2023-06-18T09_41_07-0.sml').parser.id, 'suunto-sml');
  const notSuunto = '<sml><DeviceLog/></sml>';
  assert.ok(!suuntoSmlParser.sniff(new TextEncoder().encode(notSuunto), notSuunto));
});

test('parses the DM5 fixture with Kelvin/Pascal/fraction conversions', () => {
  const res = suuntoSmlParser.parse(bytes(), text());
  assert.deepEqual(res.errors, []);
  assert.equal(res.dives.length, 1);

  const d = res.dives[0];
  assert.equal(d.startedAt, '2023-06-18T09:41:07');
  assert.equal(d.durationSec, 100);
  assert.equal(Math.round(d.maxDepthM * 100) / 100, 18.44); // float32 noise rounded
  assert.equal(d.avgDepthM, 11.83);
  assert.equal(Math.round(d.waterTempC), 14);  // 287.15 K at max depth
  assert.equal(Math.round(d.airTempC), 20);    // 293.15 K at start
  assert.equal(d.diveType, 'scuba');
  assert.equal(d.source.computerModel, 'Suunto D6i');
  assert.match(d.source.externalId, /^01234567:/);

  // the 'Off' gas slot is dropped; the primary keeps SI conversions
  assert.equal(d.tanks.length, 1);
  assert.equal(Math.round(d.tanks[0].gasO2Pct), 21);
  assert.equal(d.tanks[0].volumeL, 12);
  assert.equal(d.tanks[0].startBar, 200);
  assert.equal(d.tanks[0].endBar, 155);

  // event-only samples (no Depth) are skipped: 8 Samples → 6 profile points
  assert.equal(d.samples.length, 6);
  assert.equal(d.samples[0].depthM, 1.51);
  assert.equal(Math.round(d.samples[0].tempC), 20);
  assert.equal(d.samples[1].tempC, undefined); // sparse temps stay sparse
  assert.equal(d.samples[5].tSec, 100);
});

test('an Ambit sports log (no Diving/Depth) is not a dive', () => {
  const sports = `<?xml version="1.0"?><sml xmlns="http://www.suunto.com/schemas/sml" SdkVersion="2.1.1">
    <DeviceLog><Header><DateTime>2023-06-18T09:41:07</DateTime><Duration>849.7</Duration><Activity>Running</Activity></Header>
    <Samples><Sample><Time>0</Time></Sample></Samples></DeviceLog></sml>`;
  const res = suuntoSmlParser.parse(new TextEncoder().encode(sports), sports);
  assert.equal(res.dives.length, 0);
  assert.match(res.errors[0], /no dives found/);
  assert.ok(res.warnings.some((w) => /sports logs/.test(w)));
});

test('tolerates per-sample cylinder pressure when present', () => {
  const xml = `<?xml version="1.0"?><sml xmlns="http://www.suunto.com/schemas/sml"><DeviceLog>
    <Header><DateTime>2023-06-18T09:41:07</DateTime><Duration>60</Duration><Depth><Max>10</Max></Depth>
    <Diving><DiveMode>Air</DiveMode></Diving></Header>
    <Samples>
      <Sample><Time>0</Time><Depth>2.0</Depth><Cylinders><Cylinder><GasNumber>1</GasNumber><Pressure>19500000</Pressure></Cylinder></Cylinders></Sample>
      <Sample><Time>60</Time><Depth>0.5</Depth></Sample>
    </Samples></DeviceLog></sml>`;
  const res = suuntoSmlParser.parse(new TextEncoder().encode(xml), xml);
  assert.equal(res.dives[0].samples[0].pressureBar, 195);
  assert.equal(res.dives[0].samples[1].pressureBar, undefined);
});

test('freedive mode maps to diveType freedive', () => {
  const xml = `<?xml version="1.0"?><sml xmlns="http://www.suunto.com/schemas/sml"><DeviceLog>
    <Header><DateTime>2023-06-18T09:41:07</DateTime><Duration>90</Duration><Depth><Max>22</Max></Depth>
    <Diving><DiveMode>FreeDive</DiveMode></Diving></Header></DeviceLog></sml>`;
  const res = suuntoSmlParser.parse(new TextEncoder().encode(xml), xml);
  assert.equal(res.dives[0].diveType, 'freedive');
});

test('SML dive survives UDDF export → re-import', () => {
  const dives = suuntoSmlParser.parse(bytes(), text()).dives;
  const xml = exportUddf(dives, { generatedAt: '2026-07-15T12:00:00' });
  const rt = uddfParser.parse(new TextEncoder().encode(xml), xml);
  assert.deepEqual(rt.errors, []);
  assert.equal(rt.dives.length, 1);
  assert.equal(rt.dives[0].startedAt, '2023-06-18T09:41:07');
  assert.equal(rt.dives[0].samples.length, 6);
  assert.equal(Math.round(rt.dives[0].tanks[0].startBar), 200);
});
