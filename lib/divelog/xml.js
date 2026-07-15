// Hardened XML boundary — every byte of user XML goes through here.
// Two layers: (1) any DTD/ENTITY markup is rejected outright (the dive log
// formats we support never legitimately use one, and this closes both XXE
// and entity-expansion attacks in one move); (2) the vendored parser itself
// refuses external entities. Strict well-formedness comes from XMLValidator,
// because XMLParser alone is lenient about mismatched tags.

import { XMLParser, XMLValidator } from '../../vendor/fxp.esm.min.js';

const DTD_RE = /<!(?:DOCTYPE|ENTITY)/i;

/** Non-null = human-readable reason this XML must not be parsed. */
export function xmlThreat(text) {
  if (DTD_RE.test(text)) {
    return 'file contains DTD/ENTITY markup, which dive log exports never use — rejected for safety';
  }
  return null;
}

/** Root element name (lowercase, namespace prefix stripped), or null. Sniff helper. */
export function rootTag(text) {
  const head = text.slice(0, 4096).replace(/<\?[\s\S]*?\?>|<!--[\s\S]*?-->/g, ' ');
  const m = /<([A-Za-z_][\w.:-]*)[\s/>]/.exec(head);
  if (!m) return null;
  return m[1].toLowerCase().replace(/^.*:/, '');
}

/** Build an fxp isArray callback from tag names that must always parse as arrays. */
export function arrayTags(names) {
  const set = new Set(names);
  return (tagName) => set.has(tagName);
}

/**
 * Parse untrusted XML text. Never throws.
 * @param {string} text
 * @param {{isArray?: Function, removeNSPrefix?: boolean}} [opts]
 * @returns {{doc: Object|null, error: string|null}}
 */
export function parseXml(text, opts = {}) {
  const threat = xmlThreat(text);
  if (threat) return { doc: null, error: threat };
  const v = XMLValidator.validate(text);
  if (v !== true) {
    return { doc: null, error: `malformed XML: ${v.err.msg} (line ${v.err.line})` };
  }
  try {
    const parser = new XMLParser({
      ignoreAttributes: false,
      attributeNamePrefix: '@_',
      ignoreDeclaration: true,
      ignorePiTags: true,
      parseTagValue: false, // parsers convert numbers explicitly
      parseAttributeValue: false,
      trimValues: true,
      removeNSPrefix: opts.removeNSPrefix === true,
      isArray: opts.isArray || (() => false),
    });
    return { doc: parser.parse(text), error: null };
  } catch (e) {
    return { doc: null, error: `XML parse failed: ${e.message}` };
  }
}

/** Coerce a maybe-missing, maybe-array node to an array. */
export function asArray(node) {
  if (node === undefined || node === null) return [];
  return Array.isArray(node) ? node : [node];
}

/** Text content of a parsed node: plain string, or the #text of an element with attributes. */
export function tagText(node) {
  if (node === undefined || node === null) return undefined;
  if (typeof node === 'string') return node || undefined;
  if (typeof node === 'object' && typeof node['#text'] === 'string') return node['#text'] || undefined;
  return undefined;
}
