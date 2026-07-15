// Display-layer unit conversion. Storage is always metric (types.js);
// these run only at render time, per the user's remembered preference.

export const UNIT_SYSTEMS = ['metric', 'imperial'];

export const mToFt = (m) => m * 3.280839895;
export const cToF = (c) => (c * 9) / 5 + 32;
export const barToPsi = (bar) => bar * 14.503773773;
export const lToCuFt = (l) => l * 0.0353146667;

const r1 = (v) => Math.round(v * 10) / 10;

export function formatDepth(m, sys = 'metric') {
  if (!Number.isFinite(m)) return '—';
  return sys === 'imperial' ? `${Math.round(mToFt(m))} ft` : `${r1(m)} m`;
}

export function formatTemp(c, sys = 'metric') {
  if (!Number.isFinite(c)) return '—';
  return sys === 'imperial' ? `${Math.round(cToF(c))}°F` : `${r1(c)}°C`;
}

export function formatPressure(bar, sys = 'metric') {
  if (!Number.isFinite(bar)) return '—';
  return sys === 'imperial' ? `${Math.round(barToPsi(bar))} psi` : `${Math.round(bar)} bar`;
}

export function formatVolume(l, sys = 'metric') {
  if (!Number.isFinite(l)) return '—';
  return sys === 'imperial' ? `${r1(lToCuFt(l))} cuft` : `${r1(l)} L`;
}

/** 2880 → '48 min'; 4380 → '1 h 13 min'; also used for the stats header. */
export function formatDuration(sec) {
  if (!Number.isFinite(sec) || sec <= 0) return '—';
  const min = Math.round(sec / 60);
  if (min < 60) return `${min} min`;
  return `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, '0')} min`;
}

/** Total seconds → '87.5 h' for the stats header. */
export function formatHours(sec) {
  if (!Number.isFinite(sec) || sec <= 0) return '0 h';
  return `${Math.round(sec / 360) / 10} h`;
}
