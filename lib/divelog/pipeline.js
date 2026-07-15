// Import pipeline (PRD §8): detect → parse → validate → dedupe → preview,
// then commit on user confirmation. Pure orchestration — parsers do format
// work, the store does persistence, this file glues them and never throws.

import { LIMITS, validateDive } from './types.js';
import { detectFormat, parserById } from './parsers/index.js';
import { findDuplicates } from './dedupe.js';

function newId() {
  if (globalThis.crypto && crypto.randomUUID) return crypto.randomUUID();
  return 'id-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
}

/**
 * Parse an uploaded file and build the preview the user confirms.
 * @param {{bytes: Uint8Array, fileName: string, store: Object,
 *          parserId?: string, parserOptions?: Object}} args
 *   parserId forces a parser (e.g. re-parse CSV after column mapping);
 *   parserOptions is passed to the parser (CSV mapping, date order...).
 * @returns {Promise<{ok: boolean, error?: string,
 *   parser?: {id: string, displayName: string},
 *   entries?: {dive: Object, status: 'new'|'duplicate', dupNote?: string, include: boolean}[],
 *   warnings?: string[], counts?: {total: number, new: number, duplicates: number}}>}
 */
export async function preparePreview({ bytes, fileName, store, parserId, parserOptions }) {
  if (!bytes || bytes.length === 0) return { ok: false, error: 'The file is empty.' };
  if (bytes.length > LIMITS.maxFileBytes) {
    return { ok: false, error: `File is ${(bytes.length / 1048576).toFixed(1)} MB — the limit is ${LIMITS.maxFileBytes / 1048576} MB.` };
  }

  let parser, text;
  if (parserId) {
    parser = parserById(parserId);
    if (!parser) return { ok: false, error: `Unknown parser '${parserId}'.` };
    const det = detectFormat(bytes, fileName); // reuse decode + binary guard
    if (det.error && !det.text) return { ok: false, error: det.error };
    text = det.text;
  } else {
    const det = detectFormat(bytes, fileName);
    if (det.error) return { ok: false, error: det.error };
    parser = det.parser;
    text = det.text;
  }

  const result = await parser.parse(bytes, text, parserOptions || {}); // parsers may be async (FIT lazy-loads its reader)
  const warnings = [...(result.warnings || [])];

  if (result.errors && result.errors.length) {
    return { ok: false, error: `${parser.displayName}: ${result.errors.join(' · ')}`, parser: { id: parser.id, displayName: parser.displayName } };
  }

  let raw = result.dives || [];
  if (raw.length > LIMITS.maxDivesPerFile) {
    warnings.push(`file contains ${raw.length} dives — only the first ${LIMITS.maxDivesPerFile} were read`);
    raw = raw.slice(0, LIMITS.maxDivesPerFile);
  }

  const dives = [];
  raw.forEach((r, i) => {
    const { dive, problems } = validateDive(r);
    const label = `dive ${r && r.number ? r.number : i + 1}`;
    if (!dive) {
      warnings.push(`${label}: skipped — ${problems.join(', ')}`);
      return;
    }
    for (const p of problems) warnings.push(`${label}: ${p}`);
    dives.push(dive);
  });

  if (!dives.length) {
    return {
      ok: false,
      error: `${parser.displayName}: no dives found in this file.` + (warnings.length ? ` (${warnings.join(' · ')})` : ''),
      parser: { id: parser.id, displayName: parser.displayName },
    };
  }

  const existing = await store.listDives();
  const dupFlags = findDuplicates(dives, existing);
  const entries = dives.map((dive, i) => {
    const flag = dupFlags[i];
    if (!flag) return { dive, status: 'new', include: true };
    const dupNote = flag.kind === 'existing'
      ? 'matches a dive already in your logbook'
      : 'appears twice in this file';
    return { dive, status: 'duplicate', dupNote, include: false };
  });

  return {
    ok: true,
    parser: { id: parser.id, displayName: parser.displayName },
    entries,
    warnings,
    counts: {
      total: entries.length,
      new: entries.filter((e) => e.status === 'new').length,
      duplicates: entries.filter((e) => e.status === 'duplicate').length,
    },
  };
}

/**
 * Write the confirmed preview to the store.
 * @param {{entries: Object[], store: Object, fileName?: string, parserId?: string,
 *          warnings?: string[]}} args  entries: possibly with user-toggled `include`
 * @returns {Promise<{imported: number, skipped: number, importId: string}>}
 */
export async function commitImport({ entries, store, fileName, parserId, warnings }) {
  const importId = newId();
  const included = entries.filter((e) => e.include);

  const toStore = included.map((e) => {
    const dive = structuredClone(e.dive);
    dive.id = dive.id || newId();
    dive.source = { ...(dive.source || {}), importId, parserId: dive.source?.parserId || parserId };
    return dive;
  });

  await store.putDives(toStore);
  await store.putImport({
    id: importId,
    createdAt: new Date().toISOString(),
    fileName: fileName || '',
    parserId: parserId || '',
    imported: toStore.length,
    skipped: entries.length - included.length,
    warningCount: (warnings || []).length,
  });

  return { imported: toStore.length, skipped: entries.length - included.length, importId };
}
