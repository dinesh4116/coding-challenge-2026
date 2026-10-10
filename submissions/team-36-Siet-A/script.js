'use strict';
/* =====================================================================
   Search Term Triage Engine  -  script.js
   Part 1: logic (no page access, easy to test)
   Part 2: UI (everything below the "UI" marker)
   ===================================================================== */

/* ===== 1. LOGIC ===== */

// Editable thresholds (also shown in the UI). Z is fixed for a 95% Wilson interval.
const DEFAULTS = { minClicks: 15, minConv: 3, alpha: 0.05, costMult: 1, Z: 1.96 };
const Z = DEFAULTS.Z;

// Column names we recognise (lowercase, letters and digits only)
const ALIAS = {
  q:     ['searchterm', 'query', 'querytext', 'searchquery', 'term', 'keyword', 'searchtermtext'],
  match: ['matchtype', 'match', 'searchtermmatchtype'],
  camp:  ['campaign', 'campaignname'],
  ag:    ['adgroup', 'adgroupname'],
  imp:   ['impressions', 'impr', 'impressionscount'],
  clicks:['clicks', 'click'],
  cost:  ['cost', 'spend', 'costusd'],
  conv:  ['conversions', 'conv', 'allconv', 'conversioncount'],
  val:   ['conversionvalue', 'convvalue', 'conversionsvalue', 'revenue', 'allconvvalue']
};
const REQUIRED = { q: 'search term', clicks: 'clicks', cost: 'cost', conv: 'conversions' };

// Grammar words ignored when grouping or learning (not intent words like "buy" or "free")
const STOP = new Set(['the','a','an','for','of','in','on','to','and','with','is','are','at','by','from','my','your','i','a']);

/* ---- CSV reading ---- */

// Splits text into rows of cells. Handles quotes, escaped quotes and line breaks inside cells.
function parseCSV(text, delim) {
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
  const out = []; let row = [], cell = '', inQ = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQ) {
      if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else inQ = false; }
      else cell += ch;
    } else if (ch === '"') inQ = true;
    else if (ch === delim) { row.push(cell); cell = ''; }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(cell); cell = ''; out.push(row); row = [];
    } else cell += ch;
  }
  if (cell !== '' || row.length) { row.push(cell); out.push(row); }
  return out.filter(r => r.some(c => c.trim() !== ''));
}

const norm = h => String(h).toLowerCase().replace(/[^a-z0-9]/g, '');

function mapColumns(fields) {
  const nf = fields.map(norm), map = {};
  for (const k in ALIAS) { const i = nf.findIndex(h => ALIAS[k].includes(h)); if (i >= 0) map[k] = i; }
  return map;
}

// Turns raw file text into {fields, data}. Skips title lines that Google Ads puts above the header.
function tableFromText(text) {
  const head = text.split(/\r?\n/).slice(0, 8).join('\n');
  const count = d => (head.match(new RegExp(d === '\t' ? '\t' : '\\' + d, 'g')) || []).length;
  const delim = [',', ';', '\t'].sort((a, b) => count(b) - count(a))[0];
  const grid = parseCSV(text, delim);
  // A real header must at least name the search-term column; missing required
  // metrics are reported later by buildRows with the columns that were found.
  for (let i = 0; i < Math.min(grid.length, 15); i++) {
    const m = mapColumns(grid[i]);
    if (m.q !== undefined) {
      const fields = grid[i];
      const data = grid.slice(i + 1).map(r => Object.fromEntries(fields.map((f, j) => [f, r[j] === undefined ? '' : r[j]])));
      return { fields, data };
    }
  }
  // ZIP magic bytes (PK) mean the user dropped an archive as if it were a CSV
  if (text.charCodeAt(0) === 0x50 && text.charCodeAt(1) === 0x4B) {
    throw new Error('That file is a ZIP archive, not a CSV. Drop the .zip again (this app can open it), or unzip first and choose search_terms_report.csv.');
  }
  const first = grid[0] || [];
  throw new Error('Could not find the header row. Expected columns for ' + Object.values(REQUIRED).join(', ') + '. First row found: ' + first.slice(0, 6).join(', '));
}

/* ---- ZIP reading (so dropping the challenge .zip works) ---- */

function isZipBuffer(buf) {
  const b = new Uint8Array(buf);
  return b.length >= 4 && b[0] === 0x50 && b[1] === 0x4B && (b[2] === 3 || b[2] === 5 || b[2] === 7);
}

// Inflate a raw DEFLATE payload (ZIP method 8). Uses the browser API or Node zlib.
async function inflateRaw(bytes) {
  const u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  if (typeof DecompressionStream !== 'undefined') {
    const stream = new Blob([u8]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }
  if (typeof require !== 'undefined') {
    return new Uint8Array(require('zlib').inflateRawSync(Buffer.from(u8)));
  }
  throw new Error('Cannot unzip this file here. Unzip it yourself and drop search_terms_report.csv.');
}

// Walk local-file headers and return { name, method, data } for each entry.
function listZipEntries(buf) {
  const u8 = new Uint8Array(buf);
  const view = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  const entries = [];
  let o = 0;
  while (o + 30 <= u8.length) {
    if (view.getUint32(o, true) !== 0x04034b50) break;
    const flags = view.getUint16(o + 6, true);
    const method = view.getUint16(o + 8, true);
    const comp = view.getUint32(o + 18, true);
    const nlen = view.getUint16(o + 26, true);
    const elen = view.getUint16(o + 28, true);
    const name = new TextDecoder().decode(u8.subarray(o + 30, o + 30 + nlen));
    const dataStart = o + 30 + nlen + elen;
    if (flags & 0x8) {
      throw new Error('This ZIP uses an unusual layout. Unzip it and drop search_terms_report.csv instead.');
    }
    entries.push({ name, method, data: u8.subarray(dataStart, dataStart + comp) });
    o = dataStart + comp;
  }
  return entries;
}

async function unzipEntryBytes(entry) {
  if (entry.method === 0) return entry.data;
  if (entry.method === 8) return inflateRaw(entry.data);
  throw new Error('Unsupported ZIP compression. Unzip the archive and drop the .csv file.');
}

// Find a CSV inside a ZIP (and inside nested ZIPs like the Srishti pack).
async function extractCsvFromZip(buf, depth) {
  if (depth == null) depth = 0;
  if (depth > 3) {
    throw new Error('ZIP is nested too deeply. Unzip it and drop search_terms_report.csv.');
  }
  const files = listZipEntries(buf).filter(e => e.name && !e.name.endsWith('/'));
  const csvs = files.filter(e => /\.csv$/i.test(e.name));
  if (csvs.length) {
    const pick = csvs.find(e => /search.?term/i.test(e.name)) || csvs[0];
    const bytes = await unzipEntryBytes(pick);
    return { name: pick.name.split(/[/\\]/).pop(), bytes };
  }
  const zips = files.filter(e => /\.zip$/i.test(e.name));
  if (zips.length) {
    const pick = zips.find(e => /PS-01|search.?term/i.test(e.name)) || zips[0];
    const nested = await unzipEntryBytes(pick);
    return extractCsvFromZip(nested.buffer.slice(nested.byteOffset, nested.byteOffset + nested.byteLength), depth + 1);
  }
  throw new Error('No CSV found inside that ZIP. Use search_terms_report.csv, or drop PS-01_search_term_triage_dataset.zip.');
}

const num = v => { const x = parseFloat(String(v == null ? '' : v).replace(/[^0-9.\-]/g, '')); return isFinite(x) ? x : 0; };

// Builds clean row objects from the parsed table
function buildRows({ fields, data }) {
  const m = mapColumns(fields);
  const miss = Object.keys(REQUIRED).filter(k => m[k] === undefined);
  if (miss.length) throw new Error('Missing column(s): ' + miss.map(k => REQUIRED[k]).join(', ') + '. Columns found: ' + fields.join(', '));
  const get = (r, k) => m[k] === undefined ? '' : r[fields[m[k]]];
  const rows = [];
  data.forEach(r => {
    const q = String(get(r, 'q')).trim();
    if (!q || /^(total|--)/i.test(q)) return; // drop empty and "Total: ..." lines
    rows.push({ i: rows.length, raw: r, q, match: get(r, 'match'), camp: get(r, 'camp'), ag: get(r, 'ag'),
      imp: num(get(r, 'imp')), clicks: num(get(r, 'clicks')), cost: num(get(r, 'cost')), conv: num(get(r, 'conv')), val: num(get(r, 'val')),
      override: null, auto: false, sugg: null });
  });
  if (!rows.length) throw new Error('The file has a header but no search-term rows.');
  return rows;
}

/* ---- Statistics ---- */

// 95% confidence interval for a conversion rate; stays honest when clicks are few
function wilson(c, n) {
  if (!n) return [0, 1];
  const p = c / n, d = 1 + Z * Z / n, mid = p + Z * Z / (2 * n);
  const span = Z * Math.sqrt((p * (1 - p) + Z * Z / (4 * n)) / n);
  return [(mid - span) / d, (mid + span) / d];
}
const pct = x => (x * 100).toFixed(1) + '%';

// Decides promote / block / ignore for one set of numbers (a term, or a pooled group)
function judge(n, c, cost, acct, C) {
  const [lo, hi] = wilson(c, n), cvr = n ? c / n : 0, p = acct.p, z0 = Math.pow(1 - p, n);
  const spendOK = cost >= C.costMult * acct.cpa;
  let decision = 'ignore', conf = 'medium', review = false, reason;
  if (n < C.minClicks) {
    review = true; conf = 'low';
    reason = c > 0 ? `${c} conv from only ${n} clicks, likely noise. Needs a human look.` : `Only ${n} clicks, too little data to judge.`;
  } else if (c >= C.minConv && lo > p) {
    decision = 'promote'; conf = (lo > 2 * p && c >= 5) ? 'high' : 'medium';
    reason = `${n} clicks, ${c} conv, rate ${pct(cvr)}. Lower bound ${pct(lo)} beats account ${pct(p)}.`;
  } else if (c === 0 && z0 < C.alpha && spendOK) {
    decision = 'block'; conf = z0 < C.alpha / 5 ? 'high' : 'medium';
    reason = `${n} clicks, ${cost.toFixed(0)} spent, 0 conv. Only ${(z0 * 100).toFixed(1)}% chance at account rate ${pct(p)}.`;
  } else if (c > 0 && hi < p && spendOK) {
    decision = 'block'; conf = 'medium';
    reason = `${n} clicks, ${c} conv. Upper bound ${pct(hi)} is below account ${pct(p)}.`;
  } else if (c > 0 && cvr > p) {
    review = true; conf = 'low';
    reason = `${c} conv from ${n} clicks looks promising, but lower bound ${pct(lo)} does not beat account ${pct(p)}.`;
  } else if (c === 0) {
    reason = `${n} clicks, 0 conv, but not enough evidence to block (expected ${(n * p).toFixed(1)} conv).`;
  } else {
    reason = `${n} clicks, ${c} conv, rate ${pct(cvr)}, close to account ${pct(p)}.`;
  }
  return { decision, conf, review, reason, cvr };
}

/* ---- Grouping similar queries ---- */

function stem(w) {
  if (/(ches|shes|sses|xes|zes)$/.test(w)) return w.slice(0, -2);
  if (w.length > 3 && w.endsWith('s') && !w.endsWith('ss')) w = w.slice(0, -1);
  if (w.length > 5 && w.endsWith('ing')) return w.slice(0, -3);
  if (w.length > 4 && w.endsWith('ed')) return w.slice(0, -2);
  return w;
}
const words = q => q.toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(w => w && !STOP.has(w));
// Same words in any order, singular or plural, end up with the same key
function groupKey(q) {
  const k = [...new Set(words(q).map(stem))].sort().join(' ');
  return k || q.toLowerCase();
}

/* ---- Main computation ---- */

function computeAll(rows, C) {
  let N = 0, V = 0, CS = 0;
  for (const r of rows) { N += r.clicks; V += r.conv; CS += r.cost; }
  const acct = { N, V, CS, p: N ? V / N : 0, cpa: V ? CS / V : Infinity };
  const gm = new Map();
  for (const r of rows) {
    Object.assign(r, judge(r.clicks, r.conv, r.cost, acct, C));
    r.key = groupKey(r.q);
    let g = gm.get(r.key);
    if (!g) { g = { key: r.key, members: [], clicks: 0, conv: 0, cost: 0 }; gm.set(r.key, g); }
    g.members.push(r); g.clicks += r.clicks; g.conv += r.conv; g.cost += r.cost; r.group = g;
  }
  const groups = [...gm.values()];
  for (const g of groups) {
    const j = judge(g.clicks, g.conv, g.cost, acct, C);
    Object.assign(g, j, { reason: `${g.members.length} variants pooled: ${j.reason}` });
    g.rep = g.members.reduce((a, b) => (b.clicks > a.clicks ? b : a));
  }
  return { acct, groups, patterns: findPatterns(rows, acct, C) };
}

// Words that lose money across several terms: candidates for a phrase-match negative
function findPatterns(rows, acct, C) {
  const m = new Map();
  for (const r of rows) {
    for (const w of new Set(words(r.q))) {
      if (w.length < 3 || /^\d+$/.test(w)) continue;
      const k = (r.camp || '') + '|' + w;
      let s = m.get(k);
      if (!s) { s = { word: w, camp: r.camp || '', terms: 0, clicks: 0, conv: 0, cost: 0, ags: new Set(), promoted: 0 }; m.set(k, s); }
      s.terms++; s.clicks += r.clicks; s.conv += r.conv; s.cost += r.cost; s.ags.add(r.ag || '');
      if (r.decision === 'promote') s.promoted++;
    }
  }
  const out = [];
  for (const s of m.values()) {
    const [, hi] = wilson(s.conv, s.clicks);
    if (s.terms >= 3 && s.clicks >= C.minClicks * 2 && hi < acct.p * 0.5 && s.cost >= C.costMult * acct.cpa) {
      s.level = s.ags.size > 1 ? 'Campaign' : 'Ad group';
      s.adGroup = s.ags.size > 1 ? '' : [...s.ags][0];
      out.push(s);
    }
  }
  return out.sort((a, b) => b.cost - a.cost);
}

/* ---- Suggestions for terms that were sent to review ---- */

const fin = r => r.override || r.decision;

// Word scores learned from the reviewer's own corrections (not from auto-applied suggestions)
function learnWords(rows) {
  const L = {};
  for (const r of rows) {
    if (!r.override || r.auto) continue;
    for (const w of new Set(words(r.q))) (L[w] = L[w] || { promote: 0, block: 0, ignore: 0 })[r.override]++;
  }
  return L;
}

function suggest(rows) {
  const L = learnWords(rows);
  for (const r of rows) {
    r.sugg = null;
    if (!(r.review && !r.override)) continue;
    const g = r.group;
    if (g.members.length > 1 && !g.review) {
      r.sugg = { d: g.decision, src: `its group of ${g.members.length} variants has enough combined data` };
      continue;
    }
    const v = { promote: 0, block: 0, ignore: 0 }, used = [];
    for (const w of new Set(words(r.q))) if (L[w]) { used.push(w); for (const k in v) v[k] += L[w][k]; }
    const tot = v.promote + v.block + v.ignore, top = Object.keys(v).sort((a, b) => v[b] - v[a])[0];
    if (tot >= 3 && v[top] / tot >= 0.75) r.sugg = { d: top, src: `learned from your corrections on: ${used.join(', ')}` };
  }
}

/* ---- Export helpers ---- */

// Prefix formula-like cells so spreadsheets do not execute them (= + - @ tab CR).
function safeCell(v) {
  v = v == null ? '' : String(v);
  if (/^[=+\-@\t\r]/.test(v) && !/^-?\d+(\.\d+)?$/.test(v)) v = "'" + v;
  return /[",\n\r]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
}

function toCSV(objs) {
  if (!objs.length) return '\ufeff';
  const cols = []; objs.forEach(o => Object.keys(o).forEach(k => { if (!cols.includes(k)) cols.push(k); }));
  return '\ufeff' + [cols.map(safeCell).join(','), ...objs.map(o => cols.map(c => safeCell(o[c])).join(','))].join('\r\n');
}

function keywordRows(rows) {
  return rows.filter(r => fin(r) === 'promote').map(r => ({ Campaign: r.camp, 'Ad group': r.ag, Keyword: r.q, 'Match type': 'Exact' }));
}

// Exact negatives. Campaign level when the same term is blocked in more than one ad group.
function negativeRows(rows) {
  const m = new Map();
  rows.filter(r => fin(r) === 'block').forEach(r => {
    const k = r.camp + '|' + r.q.toLowerCase();
    if (!m.has(k)) m.set(k, { r, ags: new Set() });
    m.get(k).ags.add(r.ag);
  });
  return [...m.values()].map(({ r, ags }) => {
    const camp = ags.size > 1;
    return { Campaign: r.camp, 'Ad group': camp ? '' : r.ag, 'Negative keyword': r.q, 'Match type': 'Exact', Level: camp ? 'Campaign' : 'Ad group' };
  });
}

function patternRows(patterns) {
  return patterns.map(s => ({ Campaign: s.camp, 'Ad group': s.adGroup, 'Negative keyword': s.word, 'Match type': 'Phrase', Level: s.level,
    Evidence: `${s.terms} terms, ${s.clicks} clicks, ${s.cost.toFixed(0)} spent, ${s.conv} conv` }));
}

function resultRows(rows) {
  return rows.map(r => ({ ...r.raw, decision: r.decision, confidence: r.conf, needs_review: r.review, reason: r.reason,
    suggestion: r.sugg ? r.sugg.d : '', final_decision: fin(r), group_variants: r.group.members.length }));
}

/* ---- Sample data ---- */

function makeSample(count = 5000) {
  let s = 7; const R = () => (s = (s * 16807) % 2147483647) / 2147483647;
  const pick = a => a[Math.floor(R() * a.length)];
  const A = ['buy', 'cheap', 'best', 'discount', 'online', 'free', 'how to', 'diy', 'used', 'near me', '2026', 'review'];
  const P = ['running shoes', 'white sneakers', 'trail shoes', 'shoe cleaner', 'school shoes', 'leather boots', 'sandals'];
  const out = [];
  for (let i = 0; i < count; i++) {
    const a = pick(A), b = pick(A), p = pick(P);
    let q = R() < 0.5 ? `${a} ${p}` : `${a} ${p} ${b}`;
    const v = R(); if (v < 0.15) q = q.split(' ').reverse().join(' '); else if (v < 0.25) q += 's';
    const junk = /free|how to|diy|review/.test(q), buyer = /buy|discount|best|online/.test(q);
    const n = Math.max(1, Math.floor(Math.exp(R() * R() * 6))), rate = junk ? 0.004 : buyer ? 0.09 : 0.035;
    let c = 0; for (let k = 0; k < n; k++) if (R() < rate) c++;
    out.push({ 'Search term': q, 'Match type': pick(['Broad', 'Phrase', 'Exact']), Campaign: pick(['Shoes - Search', 'Care - Search']),
      'Ad group': pick(['Core', 'Brand', 'Generic']), Impressions: n * Math.floor(8 + R() * 30), Clicks: n,
      Cost: (n * (0.4 + R() * 1.6)).toFixed(2), Conversions: c, 'Conversion value': (c * (20 + R() * 60)).toFixed(2) });
  }
  return out;
}

/* ===== UI ===== */
if (typeof document !== 'undefined') (function ui() {

const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const PS = 100; // rows per page
const S = { rows: [], groups: [], patterns: [], acct: { p: 0, cpa: Infinity }, tab: 'terms', page: 0, gpage: 0, open: new Set() };

/* ---- helpers ---- */
const store = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } },
  remove(k) { try { localStorage.removeItem(k); } catch (e) { /* ignore */ } }
};
const SESSION_KEY = 'stte_session';
const DEMO_USER = 'analyst';
const DEMO_PASS = 'triage2026';
const cfg = () => ({
  minClicks: +$('#minClicks').value || DEFAULTS.minClicks, minConv: +$('#minConv').value || DEFAULTS.minConv,
  alpha: +$('#alpha').value || DEFAULTS.alpha, costMult: $('#costMult').value === '' ? DEFAULTS.costMult : +$('#costMult').value
});
const showErr = m => { const e = $('#err'); e.textContent = m; e.hidden = !m; };
const setStatus = m => { $('#status').textContent = m; };
function download(name, text) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }));
  a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
let timer; const debounce = (fn, ms) => () => { clearTimeout(timer); timer = setTimeout(fn, ms); };

/* ---- theme ---- */
function setTheme(t) {
  document.documentElement.dataset.theme = t; store.set('theme', t);
  const label = t === 'dark' ? 'Light mode' : 'Dark mode';
  document.querySelectorAll('.theme-toggle').forEach(b => { b.textContent = label; });
}
setTheme(store.get('theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
document.querySelectorAll('.theme-toggle').forEach(b => {
  b.onclick = () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
});

/* ---- login / session (demo, client-side only) ---- */
function showLoginErr(m) {
  const e = $('#loginErr'); e.textContent = m; e.hidden = !m;
}
function setLoggedIn(on) {
  $('#login').hidden = !!on;
  $('#app').hidden = !on;
  if (on) {
    const q = $('#user'); if (q) q.value = '';
    const p = $('#pass'); if (p) p.value = '';
    showLoginErr('');
  } else {
    const u = $('#user'); if (u) { u.focus(); }
  }
}
function isLoggedIn() { return store.get(SESSION_KEY) === '1'; }
$('#loginForm').addEventListener('submit', e => {
  e.preventDefault();
  const user = ($('#user').value || '').trim();
  const pass = $('#pass').value || '';
  if (user === DEMO_USER && pass === DEMO_PASS) {
    store.set(SESSION_KEY, '1');
    setLoggedIn(true);
  } else {
    showLoginErr('Incorrect username or password. Use the demo credentials shown below the form.');
    $('#pass').value = '';
    $('#pass').focus();
  }
});
$('#logout').onclick = () => {
  store.remove(SESSION_KEY);
  setLoggedIn(false);
};
setLoggedIn(isLoggedIn());

/* ---- saved thresholds ---- */
try {
  const saved = JSON.parse(store.get('thresholds') || 'null');
  if (saved) ['minClicks', 'minConv', 'alpha', 'costMult'].forEach(k => {
    if (saved[k] != null) $('#' + k).value = saved[k];
  });
} catch (e) { /* ignore */ }

/* ---- loading data ---- */
function decode(buf) {
  const b = new Uint8Array(buf);
  if (b[0] === 0xFF && b[1] === 0xFE) return new TextDecoder('utf-16le').decode(buf);
  if (b[0] === 0xFE && b[1] === 0xFF) return new TextDecoder('utf-16be').decode(buf);
  return new TextDecoder('utf-8').decode(buf);
}
function loadRows(rows, label) {
  S.rows = rows; S.open = new Set();
  setStatus(`${label}: ${rows.length.toLocaleString()} terms loaded`);
  run();
}
async function bufferToRows(buf, label) {
  // Accept .zip challenge packs: pull out the CSV (even from a nested ZIP).
  if (isZipBuffer(buf)) {
    setStatus('Unzipping archive...');
    const { name, bytes } = await extractCsvFromZip(buf);
    label = label + ' → ' + name;
    buf = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  }
  return { rows: buildRows(tableFromText(decode(buf))), label };
}

function readFile(f) {
  showErr(''); setStatus('Reading file...');
  f.arrayBuffer().then(buf => bufferToRows(buf, f.name)).then(({ rows, label }) => {
    loadRows(rows, label);
  }).catch(e => {
    setStatus('');
    showErr(e && e.message ? e.message : 'Could not read that file. Use a .csv or the PS-01 .zip.');
  });
}
const drop = $('#drop');
drop.onclick = () => $('#file').click();
drop.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); $('#file').click(); } };
$('#file').onchange = e => e.target.files[0] && readFile(e.target.files[0]);
drop.ondragover = e => { e.preventDefault(); drop.classList.add('on'); };
drop.ondragleave = () => drop.classList.remove('on');
drop.ondrop = e => { e.preventDefault(); drop.classList.remove('on'); e.dataTransfer.files[0] && readFile(e.dataTransfer.files[0]); };
$('#sample').onclick = () => { showErr(''); loadRows(buildRows(tableFromText(toCSV(makeSample()))), 'Sample data'); };

/* ---- computing ---- */
function run() {
  if (!S.rows.length) return;
  const C = cfg(); store.set('thresholds', JSON.stringify(C));
  Object.assign(S, computeAll(S.rows, C));
  $('#results').hidden = false;
  refresh(true);
}
function refresh(reset) {
  suggest(S.rows);
  if (reset) { S.page = 0; S.gpage = 0; }
  render();
}

/* ---- rendering ---- */
const gOv = g => { const f = g.members[0].override; return f && g.members.every(m => m.override === f) ? f : ''; };
const gFin = g => gOv(g) || g.decision;

function renderStats() {
  const t = { promote: 0, block: 0, ignore: 0 }; let rev = 0, sg = 0;
  S.rows.forEach(r => { t[fin(r)]++; if (r.review && !r.override) rev++; if (r.sugg) sg++; });
  const card = (c, v, l) => `<div class="stat ${c}"><b>${v}</b><span>${l}</span></div>`;
  $('#stats').innerHTML = card('s-acc', S.rows.length.toLocaleString(), 'terms') + card('s-pro', t.promote.toLocaleString(), 'promote') +
    card('s-blk', t.block.toLocaleString(), 'block') + card('s-ign', t.ignore.toLocaleString(), 'ignore') +
    card('s-rev', rev.toLocaleString(), 'need review') + card('s-acc', pct(S.acct.p), 'account conv. rate') +
    card('s-acc', isFinite(S.acct.cpa) ? S.acct.cpa.toFixed(2) : 'n/a', 'cost per conversion');
  const w = x => (x / S.rows.length * 100).toFixed(2) + '%';
  $('#mix').innerHTML = `<i class="m-pro" style="width:${w(t.promote)}"></i><i class="m-blk" style="width:${w(t.block)}"></i><i class="m-ign" style="width:${w(t.ignore)}"></i>`;
  $('#mix').title = `${t.promote} promote, ${t.block} block, ${t.ignore} ignore`;
  $('#suggBar').hidden = !sg;
  $('#suggText').textContent = `${sg.toLocaleString()} review term${sg === 1 ? ' has' : 's have'} a suggested decision from group evidence or your earlier corrections.`;
}

const badges = (d, review, sugg, override) => `<span class="bd ${d}">${d}</span>` +
  (review && !override ? '<span class="bd review">review</span>' : '') +
  (sugg ? `<span class="bd sug" title="${esc(sugg.src)}">suggest: ${sugg.d}</span>` : '');
const select = (attr, val) => `<select ${attr} aria-label="Override decision"><option value="">Keep</option>` +
  ['promote', 'block', 'ignore'].map(o => `<option value="${o}"${val === o ? ' selected' : ''}>${o[0].toUpperCase() + o.slice(1)}</option>`).join('') + '</select>';

function filters() {
  return { dec: $('#fDec').value, conf: $('#fConf').value, rev: $('#fRev').checked, q: $('#fQ').value.toLowerCase().trim(), sort: $('#fSort').value };
}
function pager(prefix, page, total) {
  const pages = Math.max(1, Math.ceil(total / PS)), p = Math.min(page, pages - 1);
  $('#' + prefix + 'pinfo').textContent = `${total.toLocaleString()} ${prefix ? 'groups' : 'terms'}, page ${p + 1} of ${pages}`;
  $('#' + prefix + 'prev').disabled = p === 0; $('#' + prefix + 'next').disabled = p >= pages - 1;
  return p;
}

function renderTerms() {
  const f = filters();
  const v = S.rows.filter(r => (!f.dec || fin(r) === f.dec) && (!f.conf || r.conf === f.conf) && (!f.rev || (r.review && !r.override)) && (!f.q || r.q.toLowerCase().includes(f.q)));
  v.sort((a, b) => b[f.sort] - a[f.sort]);
  S.page = pager('', S.page, v.length);
  const rows = v.slice(S.page * PS, S.page * PS + PS);
  $('#tb').innerHTML = rows.length ? rows.map(r => `<tr>
    <td class="q">${esc(r.q)}<small>${esc([r.camp, r.ag, r.match].filter(Boolean).join(' / '))}</small></td>
    <td class="n">${r.clicks.toLocaleString()}</td><td class="n">${r.cost.toFixed(2)}</td><td class="n">${r.conv}</td><td class="n">${pct(r.cvr)}</td>
    <td>${badges(fin(r), r.review, r.sugg, r.override)}</td><td class="conf-${r.conf}">${r.conf}</td>
    <td class="why">${esc(r.reason)}${r.sugg ? `<em>Suggestion: ${r.sugg.d}, because ${esc(r.sugg.src)}.</em>` : ''}</td>
    <td>${select(`data-i="${r.i}"`, r.override)}</td></tr>`).join('')
    : '<tr><td colspan="9" class="empty">No terms match these filters. Clear a filter to see more.</td></tr>';
}

function renderGroups() {
  const f = filters();
  const v = S.groups.filter(g => g.members.length > 1 && (!f.dec || gFin(g) === f.dec) && (!f.conf || g.conf === f.conf) &&
    (!f.rev || (g.review && !gOv(g))) && (!f.q || g.members.some(m => m.q.toLowerCase().includes(f.q))));
  v.sort((a, b) => b[f.sort] - a[f.sort]);
  S.gpage = pager('g', S.gpage, v.length);
  const gs = v.slice(S.gpage * PS, S.gpage * PS + PS);
  $('#gtb').innerHTML = gs.length ? gs.map(g => {
    const open = S.open.has(g.key);
    const sub = open ? `<tr class="sub"><td colspan="9">${g.members.slice().sort((a, b) => b.clicks - a.clicks).map(m =>
      `<span class="chip">${esc(m.q)}: ${m.clicks} clicks, ${m.conv} conv</span>`).join('')}</td></tr>` : '';
    return `<tr><td class="q">${esc(g.rep.q)}<small>${g.members.length} variants</small>
      <button type="button" class="expand" data-key="${esc(g.key)}" aria-expanded="${open}">${open ? 'Hide variants' : 'Show variants'}</button></td>
      <td class="n">${g.clicks.toLocaleString()}</td><td class="n">${g.cost.toFixed(2)}</td><td class="n">${g.conv}</td><td class="n">${pct(g.cvr)}</td>
      <td>${badges(gFin(g), g.review, null, gOv(g))}</td><td class="conf-${g.conf}">${g.conf}</td>
      <td class="why">${esc(g.reason)}</td><td>${select(`data-key="${esc(g.key)}"`, gOv(g))}</td></tr>${sub}`;
  }).join('') : '<tr><td colspan="9" class="empty">No groups match these filters. Groups need at least two variants of the same intent.</td></tr>';
}

function renderPatterns() {
  $('#ptb').innerHTML = S.patterns.length ? S.patterns.slice(0, 200).map(s => `<tr>
    <td class="q">${esc(s.word)}</td><td>${esc(s.camp)}</td><td class="n">${s.terms}</td><td class="n">${s.clicks.toLocaleString()}</td>
    <td class="n">${s.cost.toFixed(2)}</td><td class="n">${s.conv}</td>
    <td>Phrase match, ${s.level.toLowerCase()} level${s.adGroup ? ' (' + esc(s.adGroup) + ')' : ''}</td>
    <td class="n">${s.promoted ? `<span class="bd review">${s.promoted} promoted</span>` : 'none'}</td></tr>`).join('')
    : '<tr><td colspan="8" class="empty">No word shows enough evidence of wasted spend yet. Try lowering the minimum clicks.</td></tr>';
}

function render() {
  if (!S.rows.length) return;
  renderStats();
  $('#tools').hidden = S.tab === 'patterns';
  ['terms', 'groups', 'patterns'].forEach(t => {
    $('#panel-' + t).hidden = S.tab !== t;
    $('#tab-' + t).setAttribute('aria-selected', S.tab === t);
  });
  if (S.tab === 'terms') renderTerms(); else if (S.tab === 'groups') renderGroups(); else renderPatterns();
}

/* ---- events ---- */
document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => { S.tab = b.dataset.tab; render(); });
['fDec', 'fConf', 'fSort', 'fRev'].forEach(id => $('#' + id).onchange = () => { S.page = 0; S.gpage = 0; render(); });
$('#fQ').oninput = debounce(() => { S.page = 0; S.gpage = 0; render(); }, 200);
$('#prev').onclick = () => { S.page--; render(); };  $('#next').onclick = () => { S.page++; render(); };
$('#gprev').onclick = () => { S.gpage--; render(); }; $('#gnext').onclick = () => { S.gpage++; render(); };

// Your call on a single term
$('#tb').addEventListener('change', e => {
  const i = e.target.dataset.i; if (i == null) return;
  const r = S.rows[i]; r.override = e.target.value || null; r.auto = false; refresh();
});
// Your call on a whole group, and show/hide variants
$('#gtb').addEventListener('change', e => {
  const key = e.target.dataset.key; if (key == null) return;
  const g = S.groups.find(x => x.key === key);
  g.members.forEach(m => { m.override = e.target.value || null; m.auto = false; }); refresh();
});
$('#gtb').addEventListener('click', e => {
  const b = e.target.closest('.expand'); if (!b) return;
  const k = b.dataset.key; S.open.has(k) ? S.open.delete(k) : S.open.add(k); render();
});

$('#applySugg').onclick = () => { S.rows.forEach(r => { if (r.sugg) { r.override = r.sugg.d; r.auto = true; } }); refresh(); };
$('#resetOv').onclick = () => { S.rows.forEach(r => { r.override = null; r.auto = false; }); refresh(); };

['minClicks', 'minConv', 'alpha', 'costMult'].forEach(id => $('#' + id).oninput = debounce(run, 300));
$('#resetSet').onclick = () => {
  ['minClicks', 'minConv', 'alpha', 'costMult'].forEach(k => { $('#' + k).value = DEFAULTS[k]; });
  run();
};

// Exports (decisions you corrected are used)
$('#dAll').onclick = () => download('triage_output.csv', toCSV(resultRows(S.rows)));
$('#dPro').onclick = () => download('keywords_to_add.csv', toCSV(keywordRows(S.rows)));
$('#dNeg').onclick = () => download('negatives_to_add.csv', toCSV(negativeRows(S.rows)));
$('#dPat').onclick = () => download('phrase_negatives.csv', toCSV(patternRows(S.patterns)));

})();

/* Export pure logic for Node tests (no page access). */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    DEFAULTS, Z, ALIAS, REQUIRED, STOP,
    parseCSV, tableFromText, buildRows, num, wilson, judge, stem, words, groupKey,
    computeAll, findPatterns, learnWords, suggest, fin,
    toCSV, safeCell, keywordRows, negativeRows, patternRows, resultRows, makeSample,
    isZipBuffer, inflateRaw, listZipEntries, extractCsvFromZip
  };
}
