// UDDF 3.2.1 export of the whole logbook (PRD §2: the anti-silo guarantee).
// Emits the element order real tools use and Subsurface accepts
// (informationbeforedive, tankdata*, samples, informationafterdive; waypoint:
// depth, divetime, switchmix, tankpressure, temperature), strict SI units,
// always a <name> under <site> (Subsurface drops nameless sites), and never
// the 273.15 K "no reading" sentinel. Known v1 limits: diveMaster and
// equipment free-text have no UDDF home and stay local.

const esc = (s) => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&apos;');

const fmt = (n, dp = 2) => {
  const s = n.toFixed(dp);
  return s.includes('.') ? s.replace(/0+$/, '').replace(/\.$/, '') : s;
};

const cToK = (c) => fmt(c + 273.15, 2);
const barToPa = (bar) => String(Math.round(bar * 100000));

function mixKey(tank) {
  const o2 = tank.gasO2Pct === undefined ? 21 : tank.gasO2Pct;
  const he = tank.gasHePct === undefined ? 0 : tank.gasHePct;
  return `${fmt(o2, 1)}/${fmt(he, 1)}`;
}

function mixName(o2Pct, hePct) {
  if (hePct > 0) return `TMx ${fmt(o2Pct, 0)}/${fmt(hePct, 0)}`;
  if (Math.abs(o2Pct - 21) < 0.5) return 'air';
  return `EANx ${fmt(o2Pct, 0)}`;
}

/**
 * @param {import('./types.js').CanonicalDive[]} dives
 * @param {{generatedAt?: string}} [opts]  generatedAt: ISO timestamp for <generator><datetime>
 * @returns {string} a complete UDDF 3.2.1 document
 */
export function exportUddf(dives, opts = {}) {
  const generatedAt = opts.generatedAt || new Date().toISOString().slice(0, 19);
  const sorted = [...dives].sort((a, b) => new Date(a.startedAt) - new Date(b.startedAt));

  // dedupe shared entities across dives
  const sites = new Map();   // key → {id, site}
  const buddies = new Map(); // name → id
  const mixes = new Map();   // 'o2/he' → {id, o2Pct, hePct}
  for (const d of sorted) {
    if (d.site && d.site.name) {
      const key = `${d.site.name}|${d.site.lat ?? ''}|${d.site.lon ?? ''}`;
      if (!sites.has(key)) sites.set(key, { id: `site_${sites.size + 1}`, site: d.site });
    }
    if (d.buddy) {
      for (const name of d.buddy.split(',').map((s) => s.trim()).filter(Boolean)) {
        if (!buddies.has(name)) buddies.set(name, `buddy_${buddies.size + 1}`);
      }
    }
    for (const t of d.tanks || []) {
      const key = mixKey(t);
      if (!mixes.has(key)) {
        mixes.set(key, {
          id: `mix_${mixes.size + 1}`,
          o2Pct: t.gasO2Pct === undefined ? 21 : t.gasO2Pct,
          hePct: t.gasHePct === undefined ? 0 : t.gasHePct,
        });
      }
    }
  }

  const out = [];
  const push = (depth, s) => out.push('  '.repeat(depth) + s);

  push(0, '<?xml version="1.0" encoding="utf-8"?>');
  push(0, '<uddf xmlns="http://www.streit.cc/uddf/3.2/" version="3.2.1">');
  push(1, '<generator>');
  push(2, '<name>DiveSZN Dive Log</name>');
  push(2, '<type>logbook</type>');
  push(2, '<manufacturer id="diveszn">');
  push(3, '<name>DiveSZN</name>');
  push(2, '</manufacturer>');
  push(2, '<version>1.0</version>');
  push(2, `<datetime>${esc(generatedAt)}</datetime>`);
  push(1, '</generator>');

  push(1, '<diver>');
  push(2, '<owner id="owner">');
  push(3, '<personal><firstname/><lastname/></personal>');
  push(2, '</owner>');
  for (const [name, id] of buddies) {
    const words = name.split(/\s+/);
    const first = words.length > 1 ? words[0] : '';
    const last = words.length > 1 ? words.slice(1).join(' ') : name;
    push(2, `<buddy id="${esc(id)}">`);
    push(3, `<personal><firstname>${esc(first)}</firstname><lastname>${esc(last)}</lastname></personal>`);
    push(2, '</buddy>');
  }
  push(1, '</diver>');

  if (sites.size) {
    push(1, '<divesite>');
    for (const { id, site } of sites.values()) {
      push(2, `<site id="${esc(id)}">`);
      push(3, `<name>${esc(site.name)}</name>`);
      push(3, '<geography>');
      push(4, `<location>${esc(site.country ? `${site.name}, ${site.country}` : site.name)}</location>`);
      if (site.lat !== undefined && site.lon !== undefined) {
        push(4, `<latitude>${fmt(site.lat, 6)}</latitude>`);
        push(4, `<longitude>${fmt(site.lon, 6)}</longitude>`);
      }
      push(3, '</geography>');
      push(2, '</site>');
    }
    push(1, '</divesite>');
  }

  if (mixes.size) {
    push(1, '<gasdefinitions>');
    for (const m of mixes.values()) {
      push(2, `<mix id="${esc(m.id)}">`);
      push(3, `<name>${esc(mixName(m.o2Pct, m.hePct))}</name>`);
      push(3, `<o2>${fmt(m.o2Pct / 100, 4)}</o2>`);
      if (m.hePct > 0) push(3, `<he>${fmt(m.hePct / 100, 4)}</he>`);
      push(2, '</mix>');
    }
    push(1, '</gasdefinitions>');
  }

  push(1, '<profiledata>');
  sorted.forEach((d, i) => {
    const n = i + 1;
    push(2, `<repetitiongroup id="rg_${n}">`);
    push(3, `<dive id="${esc(d.id || `dive_${n}`)}">`);

    push(4, '<informationbeforedive>');
    for (const name of (d.buddy ? d.buddy.split(',').map((s) => s.trim()).filter(Boolean) : [])) {
      push(5, `<link ref="${esc(buddies.get(name))}"/>`);
    }
    if (d.site && d.site.name) {
      const key = `${d.site.name}|${d.site.lat ?? ''}|${d.site.lon ?? ''}`;
      push(5, `<link ref="${esc(sites.get(key).id)}"/>`);
    }
    if (d.number !== undefined) push(5, `<divenumber>${d.number}</divenumber>`);
    push(5, `<datetime>${esc(d.startedAt)}</datetime>`);
    if (d.airTempC !== undefined) push(5, `<airtemperature>${cToK(d.airTempC)}</airtemperature>`);
    push(4, '</informationbeforedive>');

    for (const t of d.tanks || []) {
      push(4, '<tankdata>');
      push(5, `<link ref="${esc(mixes.get(mixKey(t)).id)}"/>`);
      if (t.volumeL !== undefined) push(5, `<tankvolume>${fmt(t.volumeL / 1000, 4)}</tankvolume>`);
      if (t.startBar !== undefined) push(5, `<tankpressurebegin>${barToPa(t.startBar)}</tankpressurebegin>`);
      if (t.endBar !== undefined) push(5, `<tankpressureend>${barToPa(t.endBar)}</tankpressureend>`);
      push(4, '</tankdata>');
    }

    if (d.samples && d.samples.length) {
      push(4, '<samples>');
      for (const s of d.samples) {
        push(5, '<waypoint>');
        push(6, `<depth>${fmt(s.depthM, 2)}</depth>`);
        push(6, `<divetime>${fmt(s.tSec, 1)}</divetime>`);
        if (s.pressureBar !== undefined) push(6, `<tankpressure>${barToPa(s.pressureBar)}</tankpressure>`);
        if (s.tempC !== undefined && Math.abs(s.tempC) > 1e-9) push(6, `<temperature>${cToK(s.tempC)}</temperature>`);
        push(5, '</waypoint>');
      }
      push(4, '</samples>');
    }

    push(4, '<informationafterdive>');
    if (d.maxDepthM !== undefined) push(5, `<greatestdepth>${fmt(d.maxDepthM, 2)}</greatestdepth>`);
    if (d.avgDepthM !== undefined) push(5, `<averagedepth>${fmt(d.avgDepthM, 2)}</averagedepth>`);
    push(5, `<diveduration>${fmt(d.durationSec, 1)}</diveduration>`);
    if (d.waterTempC !== undefined && Math.abs(d.waterTempC) > 1e-9) {
      push(5, `<lowesttemperature>${cToK(d.waterTempC)}</lowesttemperature>`);
    }
    if (d.notes) {
      push(5, '<notes>');
      for (const para of d.notes.split(/\n{2,}/)) push(6, `<para>${esc(para)}</para>`);
      push(5, '</notes>');
    }
    push(4, '</informationafterdive>');

    push(3, '</dive>');
    push(2, '</repetitiongroup>');
  });
  push(1, '</profiledata>');
  push(0, '</uddf>');

  return out.join('\n') + '\n';
}
