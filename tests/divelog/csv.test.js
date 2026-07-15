import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { csvParser, csvIntrospect, parseGasMix, tokenizeCsv, NEEDS_MAPPING } from '../../lib/divelog/parsers/csv.js';
import { detectFormat } from '../../lib/divelog/parsers/index.js';
import { decodeText } from '../../lib/divelog/encoding.js';

const load = (name) => {
  const bytes = new Uint8Array(readFileSync(new URL(`../../test-fixtures/${name}`, import.meta.url)));
  return { bytes, text: decodeText(bytes) };
};

test('tokenizer: quotes, embedded delimiters and newlines, doubled quotes', () => {
  const rows = tokenizeCsv('a,"b,c","d\ne","f""g"\n1,2,3,4', ',');
  assert.deepEqual(rows[0], ['a', 'b,c', 'd\ne', 'f"g']);
  assert.deepEqual(rows[1], ['1', '2', '3', '4']);
});

test('sniffs the Subsurface summary CSV; detection prefers XML parsers for XML', () => {
  const { bytes, text } = load('subsurface-summary.csv');
  assert.ok(csvParser.sniff(bytes, text));
  assert.equal(detectFormat(bytes, 'dives.csv').parser.id, 'csv');
  assert.ok(!csvParser.sniff(new TextEncoder().encode('<uddf/>'), '<uddf/>'));
});

test('parses the Subsurface summary export (auto-map, phantom trailing column)', () => {
  const { bytes, text } = load('subsurface-summary.csv');
  const res = csvParser.parse(bytes, text);
  assert.deepEqual(res.errors, []);
  assert.equal(res.dives.length, 3);

  const [d1, , d3] = res.dives;
  assert.equal(d1.number, 41);
  assert.equal(d1.startedAt, '2024-03-14T09:42:00');
  assert.equal(d1.durationSec, 46 * 60 + 15); // '46:15' under a [min] header
  assert.equal(d1.maxDepthM, 18.4);
  assert.equal(d1.avgDepthM, 12.1);
  assert.equal(d1.waterTempC, 24);
  assert.equal(d1.airTempC, 26);
  assert.equal(d1.site.name, 'Illovo Beach');
  assert.equal(d1.site.lat, -30.1043);
  assert.equal(d1.site.lon, 30.8516);
  assert.equal(d1.buddy, 'John Smith');
  assert.equal(d1.diveMaster, 'Sipho Dlamini');
  assert.match(d1.notes, /two turtles/);
  assert.deepEqual(d1.tanks, [{ volumeL: 12, startBar: 200, endBar: 70, gasO2Pct: 32 }]);
  assert.equal(d3.tanks[0].gasO2Pct, 36);
  assert.equal(d3.site.lat, undefined); // empty gps cell
});

test('semicolon + decimal comma + DD.MM.YYYY (German locale)', () => {
  const { bytes, text } = load('german-logbook.csv');
  const res = csvParser.parse(bytes, text);
  assert.deepEqual(res.errors, []);
  assert.equal(res.dives.length, 3);
  assert.equal(res.dives[0].startedAt, '2024-09-05T10:15:00');
  assert.equal(res.dives[0].maxDepthM, 18.4);   // '18,4'
  assert.equal(res.dives[0].waterTempC, 16.5);  // '16,5'
  assert.equal(res.dives[0].durationSec, 48 * 60);
  assert.equal(res.dives[0].site.name, 'Kreidesee Hemmoor');
});

test('unmappable headers → needs-mapping error; explicit mapping fixes it', () => {
  const { bytes, text } = load('spreadsheet-odd-headers.csv');
  const res = csvParser.parse(bytes, text);
  assert.equal(res.dives.length, 0);
  assert.ok(res.errors[0].startsWith(NEEDS_MAPPING));

  const mapping = { When: 'date', 'How Long': 'duration', 'How Deep (ft)': 'maxDepth', Where: 'site', 'Who With': 'buddy', Story: 'notes' };
  const mapped = csvParser.parse(bytes, text, { mapping, dayFirst: false });
  assert.deepEqual(mapped.errors, []);
  assert.equal(mapped.dives.length, 2);
  assert.equal(mapped.dives[0].startedAt, '2018-07-31T00:00:00'); // M/D/YY, two-digit year
  assert.equal(Math.round(mapped.dives[0].maxDepthM * 10) / 10, 18.3); // 60 ft → m via header unit
  assert.equal(mapped.dives[0].durationSec, 45 * 60);
  assert.equal(mapped.dives[0].site.name, 'Casino Point');
});

test('mapping by column index and ignore', () => {
  const text = 'a,b,c\n2024-03-14,40,junk\n';
  const res = csvParser.parse(new TextEncoder().encode(text), text, { mapping: { '#0': 'date', '#1': 'duration', '#2': 'ignore' } });
  assert.deepEqual(res.errors, []);
  assert.equal(res.dives[0].durationSec, 2400);
});

test('day-first is decided from the data when rows disambiguate', () => {
  const text = 'Date,Duration\n01/02/2024,40\n25/02/2024,45\n'; // 25 in first slot → day-first
  const res = csvParser.parse(new TextEncoder().encode(text), text, { dayFirst: false });
  assert.equal(res.dives[0].startedAt, '2024-02-01T00:00:00');
});

test('imperial + psi heuristics', () => {
  const text = 'Date,Duration,Max Depth (ft),Water Temp,Start Pressure\n2024-03-14,40,60,75,3000\n';
  const res = csvParser.parse(new TextEncoder().encode(text), text);
  const d = res.dives[0];
  assert.equal(Math.round(d.maxDepthM * 10) / 10, 18.3);
  assert.ok(res.warnings.some((w) => /°F/.test(w)));
  assert.equal(Math.round(d.waterTempC * 10) / 10, 23.9); // 75°F
  assert.ok(res.warnings.some((w) => /psi/.test(w)));
  assert.equal(Math.round(d.tanks[0].startBar), 207);      // 3000 psi
});

test('gas mix spellings', () => {
  assert.deepEqual(parseGasMix('EAN32'), { o2Pct: 32 });
  assert.deepEqual(parseGasMix('Nitrox 36'), { o2Pct: 36 });
  assert.deepEqual(parseGasMix('21/35'), { o2Pct: 21, hePct: 35 });
  assert.deepEqual(parseGasMix('Air'), { o2Pct: 21 });
  assert.deepEqual(parseGasMix('32%'), { o2Pct: 32 });
  assert.equal(parseGasMix(''), undefined);
  assert.equal(parseGasMix('scooter'), undefined);
});

test('profile CSV (one sample per row) groups into dives with samples', () => {
  const text = [
    '"dive number","date","time","sample time (min)","sample depth (m)","sample temperature (C)","sample pressure (bar)"',
    '"1","2024-03-14","09:42","0:10","2.5","24.0","198.0"',
    '"1","2024-03-14","09:42","1:00","8.2","23.5","195.0"',
    '"1","2024-03-14","09:42","46:00","0.0","","70.0"',
    '"2","2024-03-14","13:10","0:10","3.0","24.0","205.0"',
    '"2","2024-03-14","13:10","38:00","0.0","","82.0"',
  ].join('\n');
  const res = csvParser.parse(new TextEncoder().encode(text), text);
  assert.deepEqual(res.errors, []);
  assert.equal(res.dives.length, 2);
  assert.equal(res.dives[0].samples.length, 3);
  assert.equal(res.dives[0].samples[1].tSec, 60);
  assert.equal(res.dives[0].samples[1].depthM, 8.2);
  assert.equal(res.dives[1].samples.length, 2);
});

test('rows with broken dates are salvaged around', () => {
  const text = 'Date,Duration\n2024-03-14,40\nnot-a-date,45\n2024-03-15,50\n';
  const res = csvParser.parse(new TextEncoder().encode(text), text);
  assert.equal(res.dives.length, 2);
  assert.ok(res.warnings.some((w) => /row 3/.test(w)));
});

test('csvIntrospect exposes headers, auto-map and preview for the mapping UI', () => {
  const { text } = load('spreadsheet-odd-headers.csv');
  const intro = csvIntrospect(text);
  assert.deepEqual(intro.headers, ['When', 'How Long', 'How Deep (ft)', 'Where', 'Who With', 'Story']);
  assert.equal(intro.autoMap[2], null); // 'How Deep' is not an alias
  assert.equal(intro.units[2], 'ft');
  assert.equal(intro.rows.length, 2);
});
