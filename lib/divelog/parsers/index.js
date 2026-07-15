// Parser registry + format detection (PRD §5): extension narrows the order,
// content sniffing decides — never trust extension alone. Known-but-unsupported
// binary formats get a specific, actionable rejection message (each one is a
// roadmap request — the UI invites the diver to tell us the app it came from).

import { decodeText, looksBinary, bytesMatch } from '../encoding.js';
import { rootTag } from '../xml.js';
import { uddfParser } from './uddf.js';
import { subsurfaceParser } from './subsurface.js';
import { suuntoSmlParser } from './suunto-sml.js';
import { csvParser } from './csv.js';

/** @type {import('../types.js').ParserModule[]} — csv last: weakest sniff. */
export const PARSERS = [uddfParser, subsurfaceParser, suuntoSmlParser, csvParser];

export function parserById(id) {
  return PARSERS.find((p) => p.id === id);
}

export function describeSupported() {
  return PARSERS.map((p) => `${p.displayName} (${p.extensions.join(', ')})`).join('; ');
}

export function acceptedExtensions() {
  return [...new Set(PARSERS.flatMap((p) => p.extensions))];
}

function unsupportedBinary(bytes) {
  if (bytesMatch(bytes, 8, '.FIT')) {
    return 'This is a Garmin FIT file — not supported yet, but planned. If it came from the Suunto app, export your dives from Suunto DM5 as .sml instead.';
  }
  if (bytesMatch(bytes, 0, 'PK\x03\x04')) {
    return 'This is a zip archive (e.g. a Suunto DM4/DM5 .SDE backup) — not supported yet. In DM5, export the dives themselves as .sml and upload that.';
  }
  if (bytesMatch(bytes, 0, 'SQLite format 3')) {
    return 'This is a database file (e.g. Shearwater Desktop) — not supported yet. Export your dives from Shearwater Cloud as XML and upload that.';
  }
  return 'This looks like a binary file, not a dive log export we can read. Export from your dive app as UDDF, Subsurface XML, Suunto .sml, or CSV.';
}

/**
 * @param {Uint8Array} bytes
 * @param {string} fileName
 * @returns {{parser?: import('../types.js').ParserModule, text?: string, via?: 'sniff'|'extension', error?: string}}
 */
export function detectFormat(bytes, fileName) {
  if (!bytes || bytes.length === 0) return { error: 'The file is empty.' };
  if (looksBinary(bytes)) return { error: unsupportedBinary(bytes) };

  const text = decodeText(bytes);
  const ext = (/\.[^.]+$/.exec(String(fileName || '').toLowerCase()) || [''])[0];

  const byExt = PARSERS.filter((p) => p.extensions.includes(ext));
  const rest = PARSERS.filter((p) => !p.extensions.includes(ext));

  for (const p of [...byExt, ...rest]) {
    try {
      if (p.sniff(bytes, text)) return { parser: p, text, via: 'sniff' };
    } catch { /* sniffers must not break detection */ }
  }

  const root = rootTag(text);
  if (root) {
    return { error: `This XML (root element <${root}>) isn't a format we recognise yet. Supported: ${describeSupported() || 'none'}. Tell us which app produced it and we'll add it.` };
  }
  return { error: `We couldn't recognise this file's format. Supported: ${describeSupported() || 'none'}. Tell us which app produced it and we'll add it.` };
}
