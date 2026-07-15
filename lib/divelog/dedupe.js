// Duplicate detection (PRD §7): two dives are duplicates when their start
// times are within ±3 minutes and durations within ±2 minutes.

export const START_TOLERANCE_SEC = 180;
export const DURATION_TOLERANCE_SEC = 120;

/** Epoch ms for comparison. Naive ISO strings resolve in the viewer's zone —
 *  consistent for ordering/dedupe as long as comparisons stay on one device. */
export function startMs(dive) {
  return new Date(dive.startedAt).getTime();
}

export function isDuplicate(a, b) {
  const ta = startMs(a), tb = startMs(b);
  if (Number.isNaN(ta) || Number.isNaN(tb)) return false;
  return (
    Math.abs(ta - tb) <= START_TOLERANCE_SEC * 1000 &&
    Math.abs((a.durationSec || 0) - (b.durationSec || 0)) <= DURATION_TOLERANCE_SEC
  );
}

/**
 * Flag duplicates among `candidates` against `existing` dives and against
 * earlier candidates in the same batch (same file listing a dive twice).
 * @param {import('./types.js').CanonicalDive[]} candidates
 * @param {import('./types.js').CanonicalDive[]} existing
 * @returns {(null | {kind: 'existing', match: Object} | {kind: 'batch', index: number})[]}
 */
export function findDuplicates(candidates, existing) {
  const pool = existing
    .map((d) => ({ t: startMs(d), d, batchIndex: -1 }))
    .filter((e) => !Number.isNaN(e.t))
    .sort((a, b) => a.t - b.t);

  const results = new Array(candidates.length).fill(null);
  const tolMs = START_TOLERANCE_SEC * 1000;

  candidates.forEach((cand, i) => {
    const t = startMs(cand);
    if (Number.isNaN(t)) return;
    // binary search for the first pool entry within the window
    let lo = 0, hi = pool.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (pool[mid].t < t - tolMs) lo = mid + 1; else hi = mid;
    }
    for (let j = lo; j < pool.length && pool[j].t <= t + tolMs; j++) {
      if (Math.abs((cand.durationSec || 0) - (pool[j].d.durationSec || 0)) <= DURATION_TOLERANCE_SEC) {
        results[i] = pool[j].batchIndex >= 0
          ? { kind: 'batch', index: pool[j].batchIndex }
          : { kind: 'existing', match: pool[j].d };
        break;
      }
    }
    if (!results[i]) {
      // accepted candidates join the pool so later batch entries dedupe against them
      let k = pool.length;
      pool.push({ t, d: cand, batchIndex: i });
      while (k > 0 && pool[k - 1].t > t) { const tmp = pool[k - 1]; pool[k - 1] = pool[k]; pool[k] = tmp; k--; }
    }
  });

  return results;
}
