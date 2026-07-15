// Duplicate detection (PRD §7): two dives are duplicates when their start
// times are within ±3 minutes and durations within ±2 minutes.
// Start times compare on BOTH the absolute instant and the wall-clock text —
// the same dive can arrive once with a UTC offset (e.g. Shearwater UDDF) and
// once naive (Subsurface), and a single diver can't log two dives at the same
// wall time anyway. Date-only sources (midnight timestamps from time-less
// CSVs) carry no time evidence, so they must also agree on duration exactly
// and on max depth before they count as duplicates.

export const START_TOLERANCE_SEC = 180;
export const DURATION_TOLERANCE_SEC = 120;

/** Epoch ms of the absolute instant (naive strings resolve in the viewer's zone). */
export function startMs(dive) {
  return new Date(dive.startedAt).getTime();
}

/** Epoch ms of the wall-clock reading, offset ignored. */
function wallMs(dive) {
  const m = /^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?)/.exec(String(dive.startedAt || ''));
  if (!m) return NaN;
  return new Date(m[1].replace(' ', 'T') + 'Z').getTime();
}

const isMidnight = (dive) => /T00:00(?::00)?(?:$|[.Z+-])/.test(String(dive.startedAt || ''));

function depthClose(a, b) {
  if (a.maxDepthM === undefined && b.maxDepthM === undefined) return true;
  if (a.maxDepthM === undefined || b.maxDepthM === undefined) return false;
  return Math.abs(a.maxDepthM - b.maxDepthM) <= 0.05;
}

export function isDuplicate(a, b) {
  const durDiff = Math.abs((a.durationSec || 0) - (b.durationSec || 0));
  if (durDiff > DURATION_TOLERANCE_SEC) return false;
  const tolMs = START_TOLERANCE_SEC * 1000;
  const ia = startMs(a), ib = startMs(b);
  const wa = wallMs(a), wb = wallMs(b);
  const instantClose = !Number.isNaN(ia) && !Number.isNaN(ib) && Math.abs(ia - ib) <= tolMs;
  const wallClose = !Number.isNaN(wa) && !Number.isNaN(wb) && Math.abs(wa - wb) <= tolMs;
  if (!instantClose && !wallClose) return false;
  if (isMidnight(a) && isMidnight(b)) {
    // date-only timestamps: identical start proves nothing — require the
    // numbers to agree (a re-import of the same file still matches exactly)
    return durDiff === 0 && depthClose(a, b);
  }
  return true;
}

/**
 * Flag duplicates among `candidates` against `existing` dives and against
 * earlier candidates in the same batch (same file listing a dive twice).
 * @param {import('./types.js').CanonicalDive[]} candidates
 * @param {import('./types.js').CanonicalDive[]} existing
 * @returns {(null | {kind: 'existing', match: Object} | {kind: 'batch', index: number})[]}
 */
export function findDuplicates(candidates, existing) {
  // precompute times once — isDuplicate reparses dates, too slow for n·m
  const tolMs = START_TOLERANCE_SEC * 1000;
  const entry = (d, batchIndex) => ({ d, batchIndex, i: startMs(d), w: wallMs(d), mid: isMidnight(d) });
  const pool = existing.map((d) => entry(d, -1));

  const matches = (a, b) => {
    const durDiff = Math.abs((a.d.durationSec || 0) - (b.d.durationSec || 0));
    if (durDiff > DURATION_TOLERANCE_SEC) return false;
    const instantClose = !Number.isNaN(a.i) && !Number.isNaN(b.i) && Math.abs(a.i - b.i) <= tolMs;
    const wallClose = !Number.isNaN(a.w) && !Number.isNaN(b.w) && Math.abs(a.w - b.w) <= tolMs;
    if (!instantClose && !wallClose) return false;
    if (a.mid && b.mid) return durDiff === 0 && depthClose(a.d, b.d);
    return true;
  };

  const results = new Array(candidates.length).fill(null);
  candidates.forEach((cand, ci) => {
    const c = entry(cand, ci);
    if (Number.isNaN(c.i) && Number.isNaN(c.w)) return;
    for (const p of pool) {
      if (matches(c, p)) {
        results[ci] = p.batchIndex >= 0
          ? { kind: 'batch', index: p.batchIndex }
          : { kind: 'existing', match: p.d };
        break;
      }
    }
    if (!results[ci]) pool.push(c); // accepted candidates dedupe later batch entries
  });

  return results;
}
