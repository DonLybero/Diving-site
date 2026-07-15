// Tolerant value parsing shared by parsers (Subsurface unit-suffixed strings,
// CSV cell formats, Kelvin/Pascal conversions). All return undefined on junk —
// callers turn that into per-dive warnings, never exceptions.

const fin = Number.isFinite;

/** '18.2 m', '32,0 %', '200.0 bar', '"3,000" psi', '1,234.5' → number.
 *  Commas: with a dot present, or in 3-digit groups ('3,000'), they are
 *  thousands separators; otherwise a decimal comma ('18,4'). */
export function num(v) {
  if (typeof v === 'number') return fin(v) ? v : undefined;
  if (typeof v !== 'string') return undefined;
  let s = v.trim();
  if (!s) return undefined;
  const token = /^[-+]?[\d.,]+/.exec(s);
  if (token) {
    let t = token[0];
    if (t.includes(',') && t.includes('.')) t = t.replace(/,/g, '');
    else if (t.includes(',')) t = /^[-+]?\d{1,3}(?:,\d{3})+$/.test(t) ? t.replace(/,/g, '') : t.replace(',', '.');
    s = t + s.slice(token[0].length);
  }
  const m = /^[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?/.exec(s);
  if (!m) return undefined;
  const n = parseFloat(m[0]);
  return fin(n) ? n : undefined;
}

export function kelvinToC(k) {
  const v = num(k);
  if (v === undefined) return undefined;
  if (v === 0) return undefined; // 0 K = "not recorded" in several exports
  return v - 273.15;
}

export function pascalToBar(p) {
  const v = num(p);
  return v === undefined ? undefined : v / 100000;
}

/**
 * Duration to seconds. Accepts: 2880 (sec if suffixed 's'/'sec', else minutes
 * when small is ambiguous — callers pass `unit` to pin it), '48', '48 min',
 * '48:30 min' (MM:SS), '1:02:30' (H:MM:SS), '2880 s'.
 * @param {*} v @param {'sec'|'min'|undefined} [unit] unit for bare numbers
 */
export function parseDuration(v, unit) {
  if (v === undefined || v === null) return undefined;
  const s = String(v).trim().toLowerCase();
  if (!s) return undefined;
  const colon = /^(\d+):(\d{1,2})(?::(\d{1,2}))?(?:\s*min)?$/.exec(s);
  if (colon) {
    const a = +colon[1], b = +colon[2], c = colon[3] === undefined ? undefined : +colon[3];
    // 'H:MM:SS' with three parts; 'MM:SS' with two (Subsurface writes '48:30 min')
    return c === undefined ? a * 60 + b : a * 3600 + b * 60 + c;
  }
  const n = num(s);
  if (n === undefined) return undefined;
  if (/\bs(ec(onds?)?)?\b/.test(s)) return Math.round(n);
  if (/\bmin(utes?)?\b/.test(s) || /'$/.test(s)) return Math.round(n * 60);
  if (/\bh(ours?|rs?)?\b/.test(s)) return Math.round(n * 3600);
  if (unit === 'sec') return Math.round(n);
  if (unit === 'min') return Math.round(n * 60);
  // bare number: heuristics — dive durations in seconds are >600, in minutes <600
  return n >= 600 ? Math.round(n) : Math.round(n * 60);
}

const MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };

function pad(n, w = 2) { return String(n).padStart(w, '0'); }

function buildIso(y, mo, d, time) {
  if (!y || !mo || !d || mo > 12 || d > 31) return undefined;
  if (y < 100) y += y >= 70 ? 1900 : 2000;
  const iso = `${pad(y, 4)}-${pad(mo)}-${pad(d)}T${time || '00:00:00'}`;
  return Number.isNaN(new Date(iso).getTime()) ? undefined : iso;
}

function parseTimePart(t) {
  if (!t) return undefined;
  const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s*([ap])\.?m\.?)?$/i.exec(t.trim());
  if (!m) return undefined;
  let h = +m[1];
  const ap = m[4] && m[4].toLowerCase();
  if (ap === 'p' && h < 12) h += 12;
  if (ap === 'a' && h === 12) h = 0;
  if (h > 23 || +m[2] > 59) return undefined;
  return `${pad(h)}:${m[2]}:${m[3] || '00'}`;
}

/**
 * Date (+ optional separate time) to naive ISO 'YYYY-MM-DDTHH:MM:SS'.
 * Handles: ISO datetimes (offset preserved), YYYY-MM-DD, DD.MM.YYYY,
 * DD/MM/YYYY vs MM/DD/YYYY (dayFirst decides the ambiguous case), '12 Mar 2025'.
 * @param {*} dateV @param {*} [timeV] @param {{dayFirst?: boolean}} [opts]
 */
export function parseDateTime(dateV, timeV, opts = {}) {
  if (dateV === undefined || dateV === null) return undefined;
  const dayFirst = opts.dayFirst !== false; // UK/EU default
  const s = String(dateV).trim();
  if (!s) return undefined;
  const time = parseTimePart(timeV ? String(timeV) : '');

  // full ISO datetime (keep any offset the source had)
  let m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(\.\d+)?(Z|[-+]\d{2}:?\d{2})?$/.exec(s);
  if (m) {
    const base = `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6] || '00'}`;
    const iso = base + (m[8] ? (m[8] === 'Z' ? 'Z' : m[8].includes(':') ? m[8] : m[8].slice(0, 3) + ':' + m[8].slice(3)) : '');
    return Number.isNaN(new Date(iso).getTime()) ? undefined : iso;
  }
  m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(s);
  if (m) return buildIso(+m[1], +m[2], +m[3], time);
  m = /^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$/.exec(s); // DD.MM.YYYY (German-style, always day first)
  if (m) return buildIso(+m[3], +m[2], +m[1], time);
  m = /^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$/.exec(s);
  if (m) {
    let a = +m[1], b = +m[2];
    let d, mo;
    if (a > 12) { d = a; mo = b; } else if (b > 12) { d = b; mo = a; } else if (dayFirst) { d = a; mo = b; } else { d = b; mo = a; }
    return buildIso(+m[3], mo, d, time);
  }
  m = /^(\d{1,2})[ .-]([A-Za-z]{3,})[ .-](\d{2,4})$/.exec(s); // 12 Mar 2025
  if (m) {
    const mo = MONTHS[m[2].slice(0, 3).toLowerCase()];
    return mo ? buildIso(+m[3], mo, +m[1], time) : undefined;
  }
  m = /^([A-Za-z]{3,})[ .-](\d{1,2}),?[ .-](\d{4})$/.exec(s); // Mar 12, 2025
  if (m) {
    const mo = MONTHS[m[1].slice(0, 3).toLowerCase()];
    return mo ? buildIso(+m[3], mo, +m[2], time) : undefined;
  }
  // combined "date time" cell in any of the date formats above:
  // '14/03/2024 09:42', '2024-03-14 9:42', '12 Mar 2025 2:05 pm'
  if (!time) {
    const sp = /^(.*\S)\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]\.?m\.?)?)$/i.exec(s);
    if (sp) return parseDateTime(sp[1], sp[2], opts);
  }
  return undefined;
}
