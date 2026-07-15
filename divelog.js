// DiveSZN dive log page app. Everything runs in the browser: files are read
// locally, parsed by lib/divelog/, stored in IndexedDB, exported as UDDF.
// Views are hash-routed: #log (default), #import, #dive/<id>, #add, #edit/<id>.

import { openDefaultStore, MemoryStore } from './lib/divelog/store.js';
import { preparePreview, commitImport } from './lib/divelog/pipeline.js';
import { exportUddf } from './lib/divelog/export-uddf.js';
import { validateDive, LIMITS } from './lib/divelog/types.js';
import { acceptedExtensions } from './lib/divelog/parsers/index.js';
import { csvIntrospect, CSV_FIELDS, NEEDS_MAPPING } from './lib/divelog/parsers/csv.js';
import { decodeText } from './lib/divelog/encoding.js';
import { formatDepth, formatTemp, formatDuration, formatHours, formatPressure, formatVolume, mToFt } from './lib/divelog/units.js';

const app = document.getElementById('app');

const state = {
  store: null,
  memoryOnly: false,
  units: 'metric',
  imp: null,        // in-flight import: {bytes, fileName, preview, intro, mapping, dayFirst}
  lastSummary: null,
};

/* ---------- tiny DOM builder (textContent everywhere — no user HTML) ---------- */
function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== false) node.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined) continue;
    node.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return node;
}

function fmtDate(iso, withTime = true) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const date = d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  if (!withTime) return date;
  const hasTime = /T\d/.test(iso);
  return hasTime ? `${date} · ${d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}` : date;
}

const sys = () => state.units;

/* ------------------------------ router ------------------------------ */
async function render() {
  const hash = location.hash.replace(/^#/, '');
  if (hash !== 'import') state.imp = null; // navigating away abandons an in-flight import
  app.replaceChildren();
  try {
    if (hash === 'import') await renderImport();
    else if (hash === 'add') await renderForm(null);
    else if (hash.startsWith('edit/')) await renderForm(decodeURIComponent(hash.slice(5)));
    else if (hash.startsWith('dive/')) await renderDive(decodeURIComponent(hash.slice(5)));
    else await renderLog();
  } catch (e) {
    app.replaceChildren(el('div', { class: 'msg error', text: `Something went wrong: ${e.message}` }));
  }
  window.scrollTo(0, 0);
}

function go(hash) { if (('#' + hash === location.hash) || (hash === '' && !location.hash)) render(); else location.hash = hash; }

/* ------------------------------ logbook ------------------------------ */
async function renderLog() {
  const dives = await state.store.listDives();

  if (state.memoryOnly) {
    app.append(el('div', { class: 'msg warn', role: 'status', text: 'This browser is blocking local storage, so the log lives in this tab only — export as UDDF before closing.' }));
  }
  if (state.lastSummary) {
    app.append(el('div', { class: 'msg okay', role: 'status', text: state.lastSummary }));
    state.lastSummary = null;
  }

  if (!dives.length) {
    app.append(el('div', { class: 'panel tint empty' },
      el('h2', { text: 'No dives yet' }),
      el('p', { text: 'Bring your history across: export your dives from your dive computer\'s app and drop the file here. Old computer, new computer, spreadsheet — the log reads them all into one place.' }),
      el('a', { class: 'btn', href: '#import', text: 'Import dives' }),
      ' ',
      el('a', { class: 'btn ghost', href: '#add', text: 'Add a dive manually' }),
      el('div', { class: 'chips' },
        ['UDDF (.uddf)', 'Subsurface (.ssrf/.xml)', 'Suunto DM4/DM5 (.sml)', 'CSV / spreadsheet'].map((f) => el('span', { class: 'chip', text: f }))),
    ));
    return;
  }

  const totalSec = dives.reduce((s, d) => s + (d.durationSec || 0), 0);
  const deepest = Math.max(...dives.map((d) => d.maxDepthM ?? 0));
  const sites = new Set(dives.filter((d) => d.site && d.site.name).map((d) => d.site.name.toLowerCase()));

  app.append(el('div', { class: 'kv' },
    el('div', {}, el('span', { text: 'Dives' }), el('b', { text: String(dives.length) })),
    el('div', {}, el('span', { text: 'Time underwater' }), el('b', { text: formatHours(totalSec) })),
    el('div', {}, el('span', { text: 'Deepest dive' }), el('b', { text: formatDepth(deepest, sys()) })),
    el('div', {}, el('span', { text: 'Dive sites' }), el('b', { text: String(sites.size) })),
  ));

  app.append(el('div', { class: 'toolbar' },
    el('a', { class: 'btn', href: '#import', text: 'Import dives' }),
    el('a', { class: 'btn ghost', href: '#add', text: 'Add dive' }),
    el('button', { class: 'btn ghost', text: 'Export UDDF', onclick: () => downloadUddf(dives) }),
    el('span', { class: 'spacer' }),
    unitToggle(),
  ));

  const rows = dives.map((d, i) => {
    const number = d.number !== undefined ? d.number : dives.length - i;
    const tr = el('tr', { class: 'rowlink', tabindex: '0', role: 'link', 'aria-label': `Dive ${number} on ${fmtDate(d.startedAt)}` },
      el('td', { class: 'num', text: '#' + number }),
      el('td', { text: fmtDate(d.startedAt) }),
      el('td', {}, el('div', { class: 'sitecell', text: d.site?.name || '—' })),
      el('td', { class: 'num', text: formatDepth(d.maxDepthM, sys()) }),
      el('td', { class: 'num', text: formatDuration(d.durationSec) }),
      el('td', { class: 'num', text: formatTemp(d.waterTempC, sys()) }),
    );
    const open = () => go('dive/' + encodeURIComponent(d.id));
    tr.addEventListener('click', open);
    tr.addEventListener('keydown', (e) => { if (e.key === 'Enter') open(); });
    return tr;
  });

  app.append(el('div', { class: 'tablewrap' },
    el('table', {},
      el('thead', {}, el('tr', {},
        el('th', { class: 'num', text: '#' }), el('th', { text: 'Date' }), el('th', { text: 'Site' }),
        el('th', { class: 'num', text: 'Max depth' }), el('th', { class: 'num', text: 'Duration' }), el('th', { class: 'num', text: 'Water' }))),
      el('tbody', {}, rows)),
  ));

  app.append(el('div', { class: 'toolbar' },
    el('span', { class: 'spacer' }),
    el('button', { class: 'btn quiet', text: 'Delete all dives', onclick: deleteAll }),
  ));
  app.append(el('div', { class: 'privacyline', text: 'Stored on this device only · nothing is uploaded' }));
}

function unitToggle() {
  const wrap = el('div', { class: 'unit-toggle', role: 'group', 'aria-label': 'Units' });
  for (const [key, label] of [['metric', 'm · °C'], ['imperial', 'ft · °F']]) {
    wrap.append(el('button', {
      class: state.units === key ? 'on' : '', text: label, 'aria-pressed': String(state.units === key),
      onclick: async () => {
        state.units = key;
        await state.store.setSetting('units', key);
        await render();
        const btn = app.querySelector('.unit-toggle button.on');
        if (btn) btn.focus(); // the re-render replaced the focused element
      },
    }));
  }
  return wrap;
}

async function deleteAll() {
  const answer = prompt('This deletes every dive, import record and remembered CSV mapping on this device. Type DELETE to confirm.');
  if (answer !== 'DELETE') return;
  await state.store.clearAll();
  state.lastSummary = 'Logbook cleared.';
  go('');
}

function downloadUddf(dives) {
  const xml = exportUddf(dives);
  const blob = new Blob([xml], { type: 'application/xml' });
  const url = URL.createObjectURL(blob);
  const a = el('a', { href: url, download: 'diveszn-divelog.uddf' });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

/* ------------------------------ import ------------------------------ */
async function renderImport() {
  app.append(el('a', { class: 'backlink', href: '#', text: '← Back to logbook' }));
  app.append(el('h2', { text: 'Import dives' }));

  if (!state.imp) {
    const input = el('input', { type: 'file', accept: acceptedExtensions().join(','), style: 'display:none' });
    input.addEventListener('change', () => { if (input.files[0]) handleFile(input.files[0]); });
    const drop = el('div', { class: 'drop', role: 'button', tabindex: '0', 'aria-label': 'Choose a dive log file' },
      el('b', { text: 'Drop your export file here' }),
      el('small', { text: `or tap to choose — ${acceptedExtensions().join(', ')} · up to ${LIMITS.maxFileBytes / 1048576} MB` }),
      input);
    drop.addEventListener('click', () => input.click());
    drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
    drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('over'));
    drop.addEventListener('drop', (e) => {
      e.preventDefault(); drop.classList.remove('over');
      if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
    });
    app.append(drop);
    app.append(el('div', { class: 'panel' },
      el('div', { class: 'kicker', text: 'Where to find your export' }),
      el('p', { style: 'margin:6px 0;color:#33565e;font-size:.92rem;line-height:1.65' },
        'Most dive apps have an export or backup option that writes one of these files. If yours only offers a format we don\'t read yet, import it as CSV via a spreadsheet — or tell us which app it came from and we\'ll add it to the list.'),
      el('div', { class: 'chips' },
        ['UDDF (.uddf)', 'Subsurface (.ssrf/.xml)', 'Suunto DM4/DM5 (.sml)', 'CSV / spreadsheet'].map((f) => el('span', { class: 'chip', text: f }))),
    ));
    return;
  }

  const imp = state.imp;
  if (imp.error && !imp.needsMapping) {
    app.append(el('div', { class: 'msg error', role: 'alert', text: imp.error }));
    app.append(el('button', { class: 'btn ghost', text: 'Try another file', onclick: () => { state.imp = null; render(); } }));
    return;
  }
  if (imp.needsMapping) return renderMapping(imp);
  return renderPreview(imp);
}

async function handleFile(file) {
  state.imp = null;
  app.replaceChildren(el('div', { class: 'panel tint', text: `Reading ${file.name}…` }));
  const bytes = new Uint8Array(await file.arrayBuffer());
  const imp = { bytes, fileName: file.name };
  state.imp = imp;

  // a remembered CSV column mapping is applied silently when headers match
  const preview = await preparePreview({ bytes, fileName: file.name, store: state.store });
  if (!preview.ok && preview.parser?.id === 'csv' && preview.error.includes(NEEDS_MAPPING)) {
    imp.intro = csvIntrospect(decodeText(bytes));
    const saved = imp.intro.error ? undefined : await state.store.getSetting('csvMapping:' + mapSignature(imp.intro.headers));
    if (saved) {
      const retry = await preparePreview({ bytes, fileName: file.name, store: state.store, parserId: 'csv', parserOptions: { mapping: saved.mapping, dayFirst: saved.dayFirst } });
      if (retry.ok) { imp.preview = retry; imp.mapping = saved.mapping; render(); return; }
    }
    imp.needsMapping = true;
    imp.mapping = {};
    imp.dayFirst = saved ? saved.dayFirst : true;
    render();
    return;
  }
  if (!preview.ok) { imp.error = preview.error; render(); return; }
  imp.preview = preview;
  render();
}

const mapSignature = (headers) => headers.map((h) => h.trim().toLowerCase()).join('');

function renderMapping(imp) {
  const intro = imp.intro;
  if (intro.error) {
    app.append(el('div', { class: 'msg error', text: intro.error }));
    app.append(el('button', { class: 'btn ghost', text: 'Try another file', onclick: () => { state.imp = null; render(); } }));
    return;
  }
  if (imp.error) {
    app.append(el('div', { class: 'msg error', role: 'alert', text: imp.error }));
    imp.error = null;
  }
  app.append(el('div', { class: 'msg warn', role: 'status', text: `We couldn't match all of this CSV's columns automatically — tell us what each column holds. At minimum, map the date plus a duration or max depth.` }));

  const selects = [];
  const grid = el('div', { class: 'mapgrid' });
  intro.headers.forEach((h, i) => {
    const sample = intro.rows[0] ? String(intro.rows[0][i] ?? '') : '';
    const select = el('select', { 'aria-label': `Field for column ${h}` },
      CSV_FIELDS.map((f) => el('option', { value: f.key, text: f.label })));
    select.value = imp.mapping['#' + i] || intro.autoMap[i] || 'ignore';
    selects.push(select);
    grid.append(
      el('div', { class: 'colname', title: h }, el('b', { text: h || `(column ${i + 1})` }), sample ? el('span', { style: 'color:var(--muted)' }, ` — e.g. "${sample.slice(0, 28)}"`) : null),
      select,
    );
  });

  const dayFirstBox = el('input', { type: 'checkbox' });
  dayFirstBox.checked = imp.dayFirst !== false;

  app.append(el('div', { class: 'panel' },
    el('div', { class: 'kicker', text: `Columns in ${imp.fileName}` }),
    grid,
    el('label', { class: 'checkline' }, dayFirstBox, 'Dates are day-first (31/07/2018). Untick for US month-first (7/31/2018).'),
    el('div', { class: 'formactions' },
      el('button', {
        class: 'btn', text: 'Preview dives', onclick: async () => {
          const mapping = {};
          selects.forEach((s, i) => { mapping['#' + i] = s.value; });
          imp.mapping = mapping;
          imp.dayFirst = dayFirstBox.checked;
          const preview = await preparePreview({ bytes: imp.bytes, fileName: imp.fileName, store: state.store, parserId: 'csv', parserOptions: { mapping, dayFirst: imp.dayFirst } });
          if (!preview.ok) {
            imp.needsMapping = !!preview.error.includes(NEEDS_MAPPING);
            imp.error = preview.error.replace(NEEDS_MAPPING + ': ', '');
            render(); // renderMapping/renderImport display imp.error
            return;
          }
          await state.store.setSetting('csvMapping:' + mapSignature(imp.intro.headers), { mapping, dayFirst: imp.dayFirst });
          imp.needsMapping = false;
          imp.error = null;
          imp.preview = preview;
          render();
        },
      }),
      el('button', { class: 'btn ghost', text: 'Cancel', onclick: () => { state.imp = null; render(); } }),
    ),
  ));
}

function renderPreview(imp) {
  const p = imp.preview;
  const boxes = [];

  app.append(el('div', { class: 'msg okay', text: `${imp.fileName} — read as ${p.parser.displayName}: ${p.counts.total} dive${p.counts.total === 1 ? '' : 's'}, ${p.counts.new} new, ${p.counts.duplicates} duplicate${p.counts.duplicates === 1 ? '' : 's'}.` }));

  if (p.warnings.length) {
    const shown = p.warnings.slice(0, 8);
    app.append(el('div', { class: 'msg warn' },
      el('b', { text: `${p.warnings.length} note${p.warnings.length === 1 ? '' : 's'} from this file` }),
      el('ul', {}, shown.map((w) => el('li', { text: w })), p.warnings.length > 8 ? el('li', { text: `…and ${p.warnings.length - 8} more` }) : null),
    ));
  }

  const rows = p.entries.map((entry) => {
    const box = el('input', { type: 'checkbox', class: 'includebox', 'aria-label': 'Import this dive' });
    box.checked = entry.include;
    box.addEventListener('change', () => { entry.include = box.checked; refreshCommit(); });
    boxes.push(box);
    const d = entry.dive;
    return el('tr', {},
      el('td', {}, box),
      el('td', { text: fmtDate(d.startedAt) }),
      el('td', {}, el('div', { class: 'sitecell', text: d.site?.name || '—' })),
      el('td', { class: 'num', text: formatDepth(d.maxDepthM, sys()) }),
      el('td', { class: 'num', text: formatDuration(d.durationSec) }),
      el('td', {}, el('span', { class: 'badge ' + entry.status, text: entry.status === 'duplicate' ? 'duplicate' : 'new' }),
        entry.dupNote ? el('div', { style: 'font-size:.7rem;color:var(--muted);margin-top:3px;white-space:normal', text: entry.dupNote }) : null),
    );
  });

  app.append(el('div', { class: 'tablewrap' },
    el('table', {},
      el('thead', {}, el('tr', {},
        el('th', { text: '' }), el('th', { text: 'Date' }), el('th', { text: 'Site' }),
        el('th', { class: 'num', text: 'Max depth' }), el('th', { class: 'num', text: 'Duration' }), el('th', { text: 'Status' }))),
      el('tbody', {}, rows)),
  ));

  const commitBtn = el('button', {
    class: 'btn', onclick: async () => {
      commitBtn.disabled = true;
      commitBtn.textContent = 'Importing…';
      const summary = await commitImport({ entries: p.entries, store: state.store, fileName: imp.fileName, parserId: p.parser.id, warnings: p.warnings });
      state.lastSummary = `${summary.imported} dive${summary.imported === 1 ? '' : 's'} imported from ${imp.fileName}` +
        (summary.skipped ? `, ${summary.skipped} skipped` : '') +
        (p.warnings.length ? `, ${p.warnings.length} note${p.warnings.length === 1 ? '' : 's'}` : '') + '.';
      state.imp = null;
      go('');
    },
  });
  const refreshCommit = () => {
    const n = p.entries.filter((e) => e.include).length;
    commitBtn.textContent = n ? `Import ${n} dive${n === 1 ? '' : 's'}` : 'Nothing selected';
    commitBtn.disabled = n === 0;
  };
  refreshCommit();

  app.append(el('div', { class: 'formactions' },
    commitBtn,
    el('button', { class: 'btn ghost', text: 'Cancel', onclick: () => { state.imp = null; render(); } }),
  ));
}

/* ------------------------------ dive detail ------------------------------ */
async function renderDive(id) {
  const d = await state.store.getDive(id);
  if (!d) {
    app.append(el('div', { class: 'msg error', text: 'That dive isn\'t in the log any more.' }));
    app.append(el('a', { class: 'btn ghost', href: '#', text: 'Back to logbook' }));
    return;
  }

  app.append(el('div', { class: 'toolbar' },
    el('a', { class: 'backlink', href: '#', text: '← Back to logbook' }),
    el('span', { class: 'spacer' }),
    unitToggle(),
  ));

  app.append(el('h2', { style: 'margin:10px 0 2px' },
    d.number !== undefined ? `Dive #${d.number} — ` : '', d.site?.name || 'Unnamed site'));
  app.append(el('div', { style: 'font-family:var(--mono);font-size:.78rem;color:var(--muted)' },
    fmtDate(d.startedAt),
    d.site?.country ? ` · ${d.site.country}` : '',
    d.source?.computerModel ? ` · ${d.source.computerModel}` : '',
    d.diveType && d.diveType !== 'scuba' ? ` · ${d.diveType}` : ''));

  app.append(el('div', { class: 'kv' },
    el('div', {}, el('span', { text: 'Max depth' }), el('b', { text: formatDepth(d.maxDepthM, sys()) })),
    el('div', {}, el('span', { text: 'Duration' }), el('b', { text: formatDuration(d.durationSec) })),
    d.avgDepthM !== undefined ? el('div', {}, el('span', { text: 'Avg depth' }), el('b', { text: formatDepth(d.avgDepthM, sys()) })) : null,
    d.waterTempC !== undefined ? el('div', {}, el('span', { text: 'Water' }), el('b', { text: formatTemp(d.waterTempC, sys()) })) : null,
    d.airTempC !== undefined ? el('div', {}, el('span', { text: 'Air' }), el('b', { text: formatTemp(d.airTempC, sys()) })) : null,
  ));

  if (d.samples && d.samples.length >= 2) {
    app.append(el('div', { class: 'kicker', text: 'Depth profile' }));
    app.append(profileChart(d.samples));
  } else {
    app.append(el('div', { class: 'panel', text: 'No depth profile in this dive\'s source data — the summary numbers above are everything the file carried.' }));
  }

  if (d.tanks && d.tanks.length) {
    app.append(el('div', { class: 'kicker', text: 'Gas' }));
    app.append(el('div', { class: 'tablewrap' }, el('table', {},
      el('thead', {}, el('tr', {},
        el('th', { text: 'Tank' }), el('th', { class: 'num', text: 'Size' }), el('th', { class: 'num', text: 'Mix' }),
        el('th', { class: 'num', text: 'Start' }), el('th', { class: 'num', text: 'End' }))),
      el('tbody', {}, d.tanks.map((t, i) => el('tr', {},
        el('td', { class: 'num', text: String(i + 1) }),
        el('td', { class: 'num', text: formatVolume(t.volumeL, sys()) }),
        el('td', { class: 'num', text: t.gasO2Pct === undefined ? '—' : (t.gasHePct ? `${Math.round(t.gasO2Pct)}/${Math.round(t.gasHePct)}` : (Math.abs(t.gasO2Pct - 21) < 0.5 ? 'Air' : `EAN${Math.round(t.gasO2Pct)}`)) }),
        el('td', { class: 'num', text: formatPressure(t.startBar, sys()) }),
        el('td', { class: 'num', text: formatPressure(t.endBar, sys()) }),
      ))))));
  }

  const facts = [['Buddy', d.buddy], ['Divemaster', d.diveMaster], ['Suit / equipment', d.equipment]].filter(([, v]) => v);
  if (facts.length || d.notes) {
    app.append(el('div', { class: 'panel' },
      facts.length ? el('div', { class: 'chips' }, facts.map(([k, v]) => el('span', { class: 'chip', text: `${k}: ${v}` }))) : null,
      d.notes ? el('div', { class: 'notesblock', text: d.notes }) : null,
    ));
  }

  app.append(el('div', { class: 'formactions' },
    el('a', { class: 'btn ghost', href: '#edit/' + encodeURIComponent(d.id), text: 'Edit dive' }),
    el('button', {
      class: 'btn quiet', text: 'Delete dive', onclick: async () => {
        if (!confirm('Delete this dive from the log?')) return;
        await state.store.deleteDive(d.id);
        state.lastSummary = 'Dive deleted.';
        go('');
      },
    }),
  ));
}

/* ------------------------- depth profile chart ------------------------- */
function profileChart(samples) {
  const W = 720, H = 260, L = 46, R = 14, T = 12, B = 28;
  const iw = W - L - R, ih = H - T - B;
  const tMax = Math.max(...samples.map((s) => s.tSec)) || 1;
  const dMax = Math.max(...samples.map((s) => s.depthM)) || 1;
  const imperial = sys() === 'imperial';
  const dTop = imperial ? Math.ceil(mToFt(dMax) / 10) * 10 : Math.ceil(dMax / 5) * 5;
  const x = (t) => L + (t / tMax) * iw;
  const y = (m) => T + ((imperial ? mToFt(m) : m) / dTop) * ih; // depth grows downward

  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Depth over time for this dive');
  const S = (name, attrs) => {
    const n = document.createElementNS(ns, name);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    svg.append(n);
    return n;
  };

  // recessive grid + axis labels (mono, muted)
  const ySteps = 5;
  for (let i = 0; i <= ySteps; i++) {
    const val = (dTop / ySteps) * i;
    const yy = T + (ih / ySteps) * i;
    S('line', { x1: L, x2: W - R, y1: yy, y2: yy, stroke: '#e2eeee', 'stroke-width': 1 });
    S('text', { x: L - 6, y: yy + 3, 'text-anchor': 'end', 'font-size': 10, fill: '#4a6a71', 'font-family': 'JetBrains Mono,monospace' })
      .textContent = i === 0 ? '0' : Math.round(val) + (imperial ? ' ft' : ' m');
  }
  // pick a tick step that always yields ≤12 gridlines, whatever tMax is
  const totalMin = tMax / 60;
  const everyMin = [1, 2, 5, 10, 20, 30, 60, 120, 240].find((st) => totalMin / st <= 12) || Math.ceil(totalMin / 12);
  for (let m = 0; m * 60 <= tMax; m += everyMin) {
    const xx = x(m * 60);
    const nearRightEdge = xx > W - R - 24;
    S('line', { x1: xx, x2: xx, y1: T, y2: H - B, stroke: '#eef5f5', 'stroke-width': 1 });
    S('text', { x: xx, y: H - B + 14, 'text-anchor': nearRightEdge ? 'end' : 'middle', 'font-size': 10, fill: '#4a6a71', 'font-family': 'JetBrains Mono,monospace' })
      .textContent = m === 0 ? '0' : m + ' min';
  }

  const pts = samples.map((s) => `${x(s.tSec).toFixed(1)},${y(s.depthM).toFixed(1)}`);
  S('path', { d: `M${L},${T} L${pts.join(' L')} L${x(samples[samples.length - 1].tSec).toFixed(1)},${T} Z`, fill: 'rgba(14,156,146,.12)', stroke: 'none' });
  S('path', { d: `M${pts.join(' L')}`, fill: 'none', stroke: '#0b6b74', 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' });

  // selective direct label: the deepest point
  const deepest = samples.reduce((a, b) => (b.depthM > a.depthM ? b : a));
  S('circle', { cx: x(deepest.tSec), cy: y(deepest.depthM), r: 3.5, fill: '#0b6b74', stroke: '#fff', 'stroke-width': 2 });
  const lx = Math.min(Math.max(x(deepest.tSec) + 8, L + 30), W - R - 60);
  S('text', { x: lx, y: Math.min(y(deepest.depthM) + 16, H - B - 4), 'font-size': 10.5, fill: '#0e2f37', 'font-family': 'JetBrains Mono,monospace' })
    .textContent = formatDepth(deepest.depthM, sys());

  // hover/tap layer: crosshair + mono tooltip
  const cross = S('line', { x1: 0, x2: 0, y1: T, y2: H - B, stroke: '#4a6a71', 'stroke-width': 1, 'stroke-dasharray': '3 3', visibility: 'hidden' });
  const dot = S('circle', { r: 4, fill: '#0b6b74', stroke: '#fff', 'stroke-width': 2, visibility: 'hidden' });

  const tip = el('div', { class: 'tip' });
  const box = el('div', { class: 'chart' }, svg, tip);

  const show = (clientX) => {
    const rect = svg.getBoundingClientRect();
    const t = Math.max(0, Math.min(tMax, ((clientX - rect.left) / rect.width * W - L) / iw * tMax));
    let best = samples[0];
    for (const s of samples) if (Math.abs(s.tSec - t) < Math.abs(best.tSec - t)) best = s;
    const cx = x(best.tSec);
    cross.setAttribute('x1', cx); cross.setAttribute('x2', cx);
    cross.setAttribute('visibility', 'visible');
    dot.setAttribute('cx', cx); dot.setAttribute('cy', y(best.depthM));
    dot.setAttribute('visibility', 'visible');
    const lines = [`${Math.floor(best.tSec / 60)}:${String(Math.round(best.tSec % 60)).padStart(2, '0')} min`, formatDepth(best.depthM, sys())];
    if (best.tempC !== undefined) lines.push(formatTemp(best.tempC, sys()));
    if (best.pressureBar !== undefined) lines.push(formatPressure(best.pressureBar, sys()));
    tip.textContent = lines.join(' · ');
    tip.style.display = 'block';
    const px = (cx / W) * rect.width;
    tip.style.left = Math.min(px + 10, rect.width - tip.offsetWidth - 4) + 'px';
    tip.style.top = Math.max(((y(best.depthM) / H) * rect.height) - 34, 0) + 'px';
  };
  const hide = () => { cross.setAttribute('visibility', 'hidden'); dot.setAttribute('visibility', 'hidden'); tip.style.display = 'none'; };
  svg.addEventListener('pointermove', (e) => show(e.clientX));
  svg.addEventListener('pointerdown', (e) => show(e.clientX));
  svg.addEventListener('pointerleave', hide);

  return box;
}

/* --------------------------- add / edit form --------------------------- */
async function renderForm(id) {
  const existing = id ? await state.store.getDive(id) : null;
  if (id && !existing) {
    app.append(el('div', { class: 'msg error', text: 'That dive isn\'t in the log any more.' }));
    app.append(el('a', { class: 'btn ghost', href: '#', text: 'Back to logbook' }));
    return;
  }

  app.append(el('a', { class: 'backlink', href: existing ? '#dive/' + encodeURIComponent(id) : '#', text: '← Back' }));
  app.append(el('h2', { text: existing ? 'Edit dive' : 'Add a dive' }));

  const f = {};
  const field = (key, label, type = 'text', attrs = {}) => {
    f[key] = el('input', { type, id: 'df-' + key, ...attrs });
    return el('div', {}, el('label', { text: label, for: 'df-' + key }), f[key]);
  };

  const startISO = existing?.startedAt || '';
  const tank = existing?.tanks?.[0] || {};

  const form = el('form', { class: 'dform' },
    field('date', 'Date *', 'date'),
    field('time', 'Time in', 'time'),
    field('duration', 'Duration (minutes) *', 'number', { min: '1', step: '1', inputmode: 'numeric' }),
    field('maxDepth', `Max depth (${sys() === 'imperial' ? 'ft' : 'm'})`, 'number', { min: '0', step: '0.1', inputmode: 'decimal' }),
    field('waterTemp', `Water temp (°${sys() === 'imperial' ? 'F' : 'C'})`, 'number', { step: '0.5', inputmode: 'decimal' }),
    field('site', 'Dive site'),
    field('country', 'Country'),
    field('buddy', 'Buddy'),
    field('diveMaster', 'Divemaster / guide'),
    field('equipment', 'Suit / equipment'),
    field('tankSize', 'Tank size (L)', 'number', { min: '0', step: '0.1' }),
    field('o2', 'O₂ %', 'number', { min: '1', max: '100', step: '1' }),
    field('startBar', `Start pressure (${sys() === 'imperial' ? 'psi' : 'bar'})`, 'number', { min: '0' }),
    field('endBar', `End pressure (${sys() === 'imperial' ? 'psi' : 'bar'})`, 'number', { min: '0' }),
    (() => {
      f.diveType = el('select', { id: 'df-diveType' },
        el('option', { value: 'scuba', text: 'Scuba' }),
        el('option', { value: 'freedive', text: 'Freedive' }),
        el('option', { value: 'other', text: 'Other' }));
      return el('div', {}, el('label', { text: 'Dive type', for: 'df-diveType' }), f.diveType);
    })(),
    el('div', { class: 'full' }, el('label', { text: 'Notes', for: 'df-notes' }), (f.notes = el('textarea', { id: 'df-notes' }))),
  );

  if (existing) {
    f.date.value = startISO.slice(0, 10);
    f.time.value = /T(\d{2}:\d{2})/.test(startISO) ? startISO.match(/T(\d{2}:\d{2})/)[1] : '';
    f.duration.value = existing.durationSec ? Math.round(existing.durationSec / 60) : '';
    const toUnit = (m) => (m === undefined ? '' : sys() === 'imperial' ? Math.round(mToFt(m)) : m);
    f.maxDepth.value = toUnit(existing.maxDepthM);
    f.waterTemp.value = existing.waterTempC === undefined ? '' : sys() === 'imperial' ? Math.round(existing.waterTempC * 9 / 5 + 32) : existing.waterTempC;
    f.site.value = existing.site?.name || '';
    f.country.value = existing.site?.country || '';
    f.buddy.value = existing.buddy || '';
    f.diveMaster.value = existing.diveMaster || '';
    f.equipment.value = existing.equipment || '';
    f.tankSize.value = tank.volumeL ?? '';
    f.o2.value = tank.gasO2Pct ?? '';
    f.startBar.value = tank.startBar === undefined ? '' : sys() === 'imperial' ? Math.round(tank.startBar * 14.5038) : tank.startBar;
    f.endBar.value = tank.endBar === undefined ? '' : sys() === 'imperial' ? Math.round(tank.endBar * 14.5038) : tank.endBar;
    f.diveType.value = existing.diveType || 'scuba';
    f.notes.value = existing.notes || '';
  }

  // snapshot the prefilled values: untouched fields keep their exact stored
  // value, so display rounding (imperial ft/°F/psi) never drifts the data
  // and a startedAt with a UTC offset survives an unrelated edit
  const initial = {};
  for (const k of Object.keys(f)) initial[k] = f[k].value;
  const changed = (k) => f[k].value !== initial[k];

  if (existing?.tanks && existing.tanks.length > 1) {
    app.append(el('div', { class: 'msg warn', role: 'status', text: `This dive has ${existing.tanks.length} tanks — the fields below edit tank 1; the others stay unchanged.` }));
  }

  const errBox = el('div', {});
  const save = async (e) => {
    e.preventDefault();
    errBox.replaceChildren();
    const imperial = sys() === 'imperial';
    const numv = (input) => (input.value.trim() === '' ? undefined : parseFloat(input.value));
    const keep = (key, existingVal, conv) => {
      if (existing && !changed(key)) return existingVal;
      const v = numv(f[key]);
      return v === undefined ? undefined : conv(v);
    };
    const raw = {
      ...(existing || {}),
      startedAt: existing && !changed('date') && !changed('time')
        ? existing.startedAt
        : (f.date.value ? `${f.date.value}T${f.time.value || '00:00'}:00` : ''),
      durationSec: keep('duration', existing?.durationSec, (v) => Math.round(v * 60)),
      maxDepthM: keep('maxDepth', existing?.maxDepthM, (v) => (imperial ? v * 0.3048 : v)),
      waterTempC: keep('waterTemp', existing?.waterTempC, (v) => (imperial ? ((v - 32) * 5) / 9 : v)),
      site: f.site.value.trim() ? { ...(existing?.site || {}), name: f.site.value.trim(), country: f.country.value.trim() || undefined } : undefined,
      buddy: f.buddy.value.trim() || undefined,
      diveMaster: f.diveMaster.value.trim() || undefined,
      equipment: f.equipment.value.trim() || undefined,
      notes: f.notes.value.trim() || undefined,
      diveType: f.diveType.value,
    };
    // tank 1 merges edited fields over the stored tank (He and any fields the
    // form doesn't expose survive); tanks 2+ pass through untouched
    const tank0 = { ...(existing?.tanks?.[0] || {}) };
    const setTank = (key, prop, conv) => {
      if (existing && !changed(key)) return;
      const v = numv(f[key]);
      if (v === undefined) delete tank0[prop];
      else tank0[prop] = conv(v);
    };
    setTank('tankSize', 'volumeL', (v) => v);
    setTank('o2', 'gasO2Pct', (v) => v);
    setTank('startBar', 'startBar', (v) => (imperial ? v / 14.503773773 : v));
    setTank('endBar', 'endBar', (v) => (imperial ? v / 14.503773773 : v));
    const restTanks = (existing?.tanks || []).slice(1);
    const tanks = [tank0, ...restTanks].filter((t) => Object.keys(t).length);
    raw.tanks = tanks.length ? tanks : undefined;
    if (!raw.startedAt) { errBox.replaceChildren(el('div', { class: 'msg error', role: 'alert', text: 'The dive needs a date.' })); return; }
    if (!raw.durationSec) { errBox.replaceChildren(el('div', { class: 'msg error', role: 'alert', text: 'The dive needs a duration.' })); return; }

    const { dive, problems } = validateDive(raw);
    if (!dive) { errBox.replaceChildren(el('div', { class: 'msg error', text: problems.join(', ') })); return; }
    dive.id = existing?.id || (crypto.randomUUID ? crypto.randomUUID() : 'id-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8));
    if (existing?.number !== undefined) dive.number = existing.number;
    dive.source = existing?.source || { parserId: 'manual' };
    await state.store.putDives([dive]);
    state.lastSummary = existing ? 'Dive updated.' : 'Dive added to the log.';
    go(existing ? 'dive/' + encodeURIComponent(dive.id) : '');
  };

  app.append(form, errBox, el('div', { class: 'formactions' },
    el('button', { class: 'btn', text: existing ? 'Save changes' : 'Add dive', onclick: save }),
    el('a', { class: 'btn ghost', href: existing ? '#dive/' + encodeURIComponent(id) : '#', text: 'Cancel' }),
  ));
}

/* ------------------------------ boot ------------------------------ */
async function boot() {
  try {
    state.store = await openDefaultStore();
  } catch {
    state.store = await new MemoryStore().init();
    state.memoryOnly = true;
  }
  state.units = (await state.store.getSetting('units')) === 'imperial' ? 'imperial' : 'metric';
  window.addEventListener('hashchange', render);
  render();
}

boot();
