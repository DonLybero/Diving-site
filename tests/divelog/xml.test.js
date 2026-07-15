import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseXml, xmlThreat, rootTag, asArray, tagText, arrayTags } from '../../lib/divelog/xml.js';

test('parses well-formed XML with attributes', () => {
  const { doc, error } = parseXml('<a x="1"><b>hi</b><b>ho</b></a>', { isArray: arrayTags(['b']) });
  assert.equal(error, null);
  assert.equal(doc.a['@_x'], '1');
  assert.deepEqual(doc.a.b, ['hi', 'ho']);
});

test('rejects DOCTYPE (XXE) before parsing', () => {
  const evil = '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><uddf>&xxe;</uddf>';
  assert.ok(xmlThreat(evil));
  const { doc, error } = parseXml(evil);
  assert.equal(doc, null);
  assert.match(error, /DTD\/ENTITY/);
});

test('rejects lowercase doctype and billion-laughs style input', () => {
  const bomb = '<!doctype lolz [<!entity lol "lol"><!entity lol2 "&lol;&lol;">]><x>&lol2;</x>';
  const { doc, error } = parseXml(bomb);
  assert.equal(doc, null);
  assert.ok(error);
});

test('undeclared entity references stay literal (no resolution)', () => {
  const { doc, error } = parseXml('<a>&mystery;</a>');
  assert.equal(error, null);
  assert.equal(doc.a, '&mystery;');
});

test('malformed XML returns an error with a line number, never throws', () => {
  const { doc, error } = parseXml('<a><b></a>');
  assert.equal(doc, null);
  assert.match(error, /malformed XML/);
  assert.match(error, /line 1/);
});

test('truncated XML is malformed', () => {
  const { error } = parseXml('<uddf><profiledata><repetitiongroup><dive><informationbefo');
  assert.match(error, /malformed XML/);
});

test('rootTag skips declaration and comments, strips namespace prefix', () => {
  assert.equal(rootTag('<?xml version="1.0" encoding="utf-8"?>\n<!-- hi -->\n<uddf version="3.2.1">'), 'uddf');
  assert.equal(rootTag('<sml xmlns="http://www.suunto.com/schemas/sml">'), 'sml');
  assert.equal(rootTag('<u:uddf xmlns:u="x">'), 'uddf');
  assert.equal(rootTag('just text'), null);
});

test('asArray and tagText helpers', () => {
  assert.deepEqual(asArray(undefined), []);
  assert.deepEqual(asArray('x'), ['x']);
  assert.deepEqual(asArray(['x']), ['x']);
  assert.equal(tagText('hello'), 'hello');
  assert.equal(tagText({ '#text': 'hi', '@_a': '1' }), 'hi');
  assert.equal(tagText(undefined), undefined);
  assert.equal(tagText(''), undefined);
});
