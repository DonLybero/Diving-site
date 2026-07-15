import { test } from 'node:test';
import assert from 'node:assert/strict';
import { decodeText, looksBinary, bytesMatch } from '../../lib/divelog/encoding.js';

const utf8 = (s) => new TextEncoder().encode(s);

test('plain utf-8 and BOM stripping', () => {
  assert.equal(decodeText(utf8('<uddf/>')), '<uddf/>');
  assert.equal(decodeText(new Uint8Array([0xef, 0xbb, 0xbf, ...utf8('<a/>')])), '<a/>');
});

test('utf-16 little-endian with BOM', () => {
  const src = '<sml>ä</sml>';
  const bytes = new Uint8Array(2 + src.length * 2);
  bytes[0] = 0xff; bytes[1] = 0xfe;
  for (let i = 0; i < src.length; i++) {
    bytes[2 + i * 2] = src.charCodeAt(i) & 0xff;
    bytes[3 + i * 2] = src.charCodeAt(i) >> 8;
  }
  assert.equal(decodeText(bytes), src);
  assert.equal(looksBinary(bytes), false); // NUL-heavy but BOM says text
});

test('binary detection and magic matching', () => {
  assert.equal(looksBinary(utf8('Date,Depth\n1,18')), false);
  assert.equal(looksBinary(new Uint8Array([0x0e, 0x10, 0x00, 0x07, 0x2e, 0x46, 0x49, 0x54])), true);
  const fit = new Uint8Array(16);
  fit.set([0x2e, 0x46, 0x49, 0x54], 8); // '.FIT' at offset 8
  assert.ok(bytesMatch(fit, 8, '.FIT'));
  assert.ok(!bytesMatch(fit, 0, 'PK\x03\x04'));
});
