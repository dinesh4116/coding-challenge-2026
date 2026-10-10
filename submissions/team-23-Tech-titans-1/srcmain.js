import '@fontsource-variable/sora';
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import '@fontsource/ibm-plex-sans/600.css';
import '@fontsource-variable/jetbrains-mono';
import './style.css';

import { loadDataset, FIELDS, NUMERIC_FIELDS } from './dataset.js';
import { buildIndex, matchImage } from './matching.js';
import { analyseImage, MAX_IMAGE_BYTES, CATEGORY, LIKELY_THRESHOLD } from './analysis.js';
import { downloadReport } from './report.js';
import { escapeHtml as esc, formatBytes, fmtNum, fmtPct, getExt, yieldToBrowser, cellToString } from './utils.js';

const MAX_IMAGES = 200;
const PREVIEW_ROWS = 100;
const IMAGE_EXT = ['jpg', 'jpeg', 'png', 'webp'];
const IMAGE_MIME = ['image/jpeg', 'image/jpg', 'image/pjpeg', 'image/png', 'image/webp'];

const state = {
  dataset: null,
  index: null,
  images: [],
  nextId: 1,
  filter: 'all',
  sort: 'upload',
  search: '',
  run: null, // { total, processed, current, cancel }
  lastRun: null,
  detailId: null,
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// ---------------------------------------------------------------------------
// Generic helpers
// ---------------------------------------------------------------------------

function setupDropzone(zone, input, onFiles) {
  const stop = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };
  ['dragenter', 'dragover'].forEach((ev) =>
    zone.addEventListener(ev, (e) => {
      stop(e);
      zone.classList.add('dragging');
    })
  );
  ['dragleave', 'dragend'].forEach((ev) =>
    zone.addEventListener(ev, (e) => {
      stop(e);
      if (ev === 'dragend' || !zone.contains(e.relatedTarget)) zone.classList.remove('dragging');
    })
  );
  zone.addEventListener('drop', (e) => {
    stop(e);
    zone.classList.remove('dragging');
    const files = [...(e.dataTransfer?.files || [])];
    if (files.length) onFiles(files);
  });
  zone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      input.click();
    }
  });
  input.addEventListener('change', () => {
    const files = [...(input.files || [])];
    input.value = ''; // allow selecting the same file again
    if (files.length) onFiles(files);
  });
}

// Stop the browser from opening files dropped outside a dropzone.
window.addEventListener('dragover', (e) => e.preventDefault());
window.addEventListener('drop', (e) => e.preventDefault());

function messageHtml(kind, html) {
  return `<div class="notice notice-${kind}">${html}</div>`;
}

let toastTimer;
function toast(text) {
  const el = $('#toast');
  el.textContent = text;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 3200);
}

// ---------------------------------------------------------------------------
// Dataset section
// ---------------------------------------------------------------------------

const datasetInput = $('#dataset-input');
setupDropzone($('#dataset-drop'), datasetInput, (files) => handleDatasetFiles(files));

async function handleDatasetFiles(files) {
  const file = files[0];
  const msgs = $('#dataset-messages');
  const extra = files.length > 1 ? messageHtml('warn', `Only one dataset can be loaded at a time. Using “${esc(file.name)}” and ignoring ${files.length - 1} other file(s).`) : '';
  renderDatasetFile({ name: file.name, ext: getExt(file.name), size: file.size, status: 'reading' });
  msgs.innerHTML = extra;
  try {
    const dataset = await loadDataset(file);
    state.dataset = dataset;
    state.index = buildIndex(dataset);
    renderDatasetFile({ ...dataset.info, status: 'ready', rows: dataset.rows.length, cols: dataset.headers.length });
    msgs.innerHTML =
      extra +
      messageHtml('ok', `Parsed <strong>${fmtNum(dataset.rows.length)}</strong> data row(s) and <strong>${dataset.headers.length}</strong> column(s)${dataset.info.sheetName ? ` from sheet “${esc(dataset.info.sheetName)}”` : ''}.`) +
      dataset.warnings.map((w) => messageHtml('warn', esc(w))).join('');
    renderDatasetPanel();
    rematchImages();
    toast('Dataset loaded');
  } catch (err) {
    const prev = state.dataset;
    msgs.innerHTML =
      extra +
      messageHtml('error', `<strong>Could not load “${esc(file.name)}”.</strong> ${esc(err.message || String(err))}${prev ? ` Your previous dataset “${esc(prev.info.name)}” is still loaded.` : ''}`);
    if (prev) renderDatasetFile({ ...prev.info, status: 'ready', rows: prev.rows.length, cols: prev.headers.length });
    else renderDatasetFile({ name: file.name, ext: getExt(file.name), size: file.size, status: 'error' });
  }
}

function renderDatasetFile(info) {
  const el = $('#dataset-file');
  el.hidden = false;
  const statusMap = {
    reading: ['Reading…', 'pill-info'],
    ready: ['Parsed', 'pill-good'],
    error: ['Failed', 'pill-bad'],
  };
  const [statusText, statusCls] = statusMap[info.status];
  const typeLabel = info.type || (info.ext ? `.${info.ext} file` : 'Unknown type');
  el.innerHTML = `
    <div class="file-row">
      <div class="file-badge">${esc((info.ext || '?').toUpperCase())}</div>
      <div class="file-meta">
        <div class="file-name" title="${esc(info.name)}">${esc(info.name)}</div>
        <div class="file-sub">${esc(typeLabel)} · ${formatBytes(info.size)}${info.rows != null ? ` · ${fmtNum(info.rows)} rows · ${info.cols} columns` : ''}</div>
      </div>
      <span class="pill ${statusCls}">${info.status === 'reading' ? '<span class="spinner"></span>' : ''}${statusText}</span>
    </div>
    ${
      info.status !== 'reading'
        ? `<div class="file-actions">
            <button class="btn btn-ghost btn-sm" type="button" data-ds="replace">Replace file</button>
            ${state.dataset ? '<button class="btn btn-danger-ghost btn-sm" type="button" data-ds="remove">Remove dataset</button>' : '<button class="btn btn-danger-ghost btn-sm" type="button" data-ds="dismiss">Dismiss</button>'}
          </div>`
        : ''
    }`;
}

$('#dataset-file').addEventListener('click', (e) => {
  const action = e.target.closest('[data-ds]')?.dataset.ds;
  if (action === 'replace') datasetInput.click();
  if (action === 'remove') removeDataset();
  if (action === 'dismiss') {
    $('#dataset-file').hidden = true;
    $('#dataset-messages').innerHTML = '';
  }
});

function removeDataset() {
  state.dataset = null;
  state.index = null;
  $('#dataset-file').hidden = true;
  $('#dataset-messages').innerHTML = messageHtml('info', 'Dataset removed. Image analysis still works without a dataset.');
  $('#dataset-panel').hidden = true;
  rematchImages();
}

function renderDatasetPanel() {
  const ds = state.dataset;
  const panel = $('#dataset-panel');
  if (!ds) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const roleByHeader = Object.fromEntries(Object.entries(ds.mapping).map(([f, h]) => [h, f]));
  $('#dataset-panel-sub').textContent = `${ds.info.name} · ${fmtNum(ds.rows.length)} rows · ${ds.headers.length} columns`;

  const recognised = Object.keys(FIELDS).map((f) => {
    const h = ds.mapping[f];
    return `<li class="${h ? 'found' : 'missing'}"><span class="field">${esc(FIELDS[f].label)}</span>${h ? `<span class="arrow">←</span><code>${esc(h)}</code>` : '<span class="muted">not found</span>'}</li>`;
  });
  $('#dataset-columns').innerHTML = `
    <div class="columns-block">
      <h3>Recognised fields</h3>
      <ul class="field-list">${recognised.join('')}</ul>
    </div>
    <div class="columns-block">
      <h3>All detected columns (${ds.headers.length})</h3>
      <div class="chips">${ds.headers.map((h) => `<span class="chip ${roleByHeader[h] ? 'chip-mapped' : ''}">${esc(h)}${roleByHeader[h] ? ` <em>${esc(FIELDS[roleByHeader[h]].label)}</em>` : ''}</span>`).join('')}</div>
    </div>`;

  const s = ds.summary;
  const kpis = [['Rows', fmtNum(ds.rows.length)], ['Columns', fmtNum(ds.headers.length)]];
  if (s.spend != null) kpis.push(['Total spend', fmtNum(s.spend, 2)]);
  if (s.impressions != null) kpis.push(['Impressions', fmtNum(s.impressions)]);
  if (s.clicks != null) kpis.push(['Clicks', fmtNum(s.clicks)]);
  if (s.purchases != null) kpis.push(['Purchases', fmtNum(s.purchases)]);
  if (s.revenue != null) kpis.push(['Revenue', fmtNum(s.revenue, 2)]);
  const ms = ds.metricStatus;
  if (ms.ctr.available) kpis.push(['Overall CTR', fmtPct(s.ctr), 'calc']);
  if (ms.cvr.available) kpis.push(['Conversion rate', fmtPct(s.cvr), 'calc']);
  if (ms.roas.available) kpis.push(['ROAS', s.roas == null ? '—' : `${fmtNum(s.roas, 2)}×`, 'calc']);
  $('#dataset-kpis').innerHTML = kpis
    .map(([label, value, calc]) => `<div class="kpi ${calc ? 'kpi-calc' : ''}"><span class="kpi-label">${esc(label)}${calc ? ' <em>calculated</em>' : ''}</span><span class="kpi-value">${esc(value)}</span></div>`)
    .join('');

  const notes = Object.values(ms).map((m) =>
    m.available
      ? messageHtml('ok', `<strong>${m.label}</strong> calculated as ${esc(m.formula)} (only for rows where the inputs are valid numbers and the denominator is above zero).`)
      : messageHtml('warn', `<strong>${m.label} not calculated:</strong> missing column(s): ${esc(m.missing.join(', '))}.`)
  );
  $('#dataset-metric-notes').innerHTML = notes.join('');

  const calcCols = [
    ms.ctr.available && ['ctr', 'CTR', (r) => fmtPct(r.ctr)],
    ms.cvr.available && ['cvr', 'Conv. rate', (r) => fmtPct(r.cvr)],
    ms.roas.available && ['roas', 'ROAS', (r) => (r.roas == null ? '—' : `${fmtNum(r.roas, 2)}×`)],
  ].filter(Boolean);
  const shown = ds.records.slice(0, PREVIEW_ROWS);
  $('#dataset-preview-note').textContent =
    ds.records.length > PREVIEW_ROWS ? `Showing first ${PREVIEW_ROWS} of ${fmtNum(ds.records.length)} rows` : `Showing all ${fmtNum(ds.records.length)} rows`;
  const head = `<thead><tr><th class="rownum">#</th>${ds.headers
    .map((h) => `<th>${esc(h)}${roleByHeader[h] ? `<span class="th-role">${esc(FIELDS[roleByHeader[h]].label)}</span>` : ''}</th>`)
    .join('')}${calcCols.map(([, l]) => `<th class="th-calc">${l}<span class="th-role">calculated</span></th>`).join('')}</tr></thead>`;
  const numericHeaders = new Set(NUMERIC_FIELDS.map((f) => ds.mapping[f]).filter(Boolean));
  const body = shown
    .map((r) => {
      const cells = ds.headers
        .map((h) => {
          const v = cellToString(r.raw[h]);
          const invalid = numericHeaders.has(h) && v.trim() !== '' && r[roleByHeader[h]] == null;
          return `<td class="${numericHeaders.has(h) ? 'num' : ''} ${invalid ? 'invalid' : ''}" ${invalid ? 'title="Invalid value: excluded from calculations"' : ''}>${esc(v)}</td>`;
        })
        .join('');
      return `<tr><td class="rownum">${r.rowNumber}</td>${cells}${calcCols.map(([, , fn]) => `<td class="num calc">${fn(r)}</td>`).join('')}</tr>`;
    })
    .join('');
  $('#dataset-table').innerHTML = head + `<tbody>${body}</tbody>`;
}

// ---------------------------------------------------------------------------
// Image section
// ---------------------------------------------------------------------------

setupDropzone($('#image-drop'), $('#image-input'), (files) => addImages(files));

function isAcceptedImage(file) {
  const ext = getExt(file.name);
  if (file.type) return IMAGE_MIME.includes(file.type) && IMAGE_EXT.includes(ext || 'jpg');
  return IMAGE_EXT.includes(ext);
}

function addImages(files) {
  const rejected = [];
  let skippedLimit = 0;
  let duplicates = 0;
  let added = 0;
  const existing = new Set(state.images.map((i) => `${i.name}|${i.size}|${i.file.lastModified}`));
  for (const file of files) {
    if (!isAcceptedImage(file)) {
      rejected.push(`${file.name}: unsupported type${file.type ? ` (${file.type})` : ''}. Use JPG, JPEG, PNG or WEBP.`);
      continue;
    }
    if (file.size === 0) {
      rejected.push(`${file.name}: the file is empty.`);
      continue;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      rejected.push(`${file.name}: larger than the 30 MB per-image limit.`);
      continue;
    }
    const key = `${file.name}|${file.size}|${file.lastModified}`;
    if (existing.has(key)) {
      duplicates++;
      continue;
    }
    if (state.images.length >= MAX_IMAGES) {
      skippedLimit++;
      continue;
    }
    existing.add(key);
    state.images.push({
      id: state.nextId++,
      file,
      name: file.name,
      size: file.size,
      url: URL.createObjectURL(file),
      thumbUrl: null,
      status: 'ready',
      result: null,
      error: null,
      match: state.index ? matchImage(file.name, state.index) : null,
    });
    added++;
  }

  const msgs = [];
  if (added) msgs.push(messageHtml('ok', `Added ${added} image(s). Click <strong>Analyse images</strong> when you're ready.`));
  if (duplicates) msgs.push(messageHtml('info', `${duplicates} file(s) were already in the batch and were skipped.`));
  if (skippedLimit) msgs.push(messageHtml('warn', `${skippedLimit} file(s) were not added: the batch limit is ${MAX_IMAGES} images. Clear or remove images to add more.`));
  if (rejected.length) {
    msgs.push(
      messageHtml('error', `<strong>${rejected.length} file(s) rejected:</strong><ul class="msg-list">${rejected.slice(0, 8).map((r) => `<li>${esc(r)}</li>`).join('')}${rejected.length > 8 ? `<li>…and ${rejected.length - 8} more</li>` : ''}</ul>`)
    );
  }
  $('#image-messages').innerHTML = msgs.join('');
  renderGallery();
  updateImageControls();
}

function removeImage(id) {
  const idx = state.images.findIndex((i) => i.id === id);
  if (idx === -1) return;
  const [img] = state.images.splice(idx, 1);
  URL.revokeObjectURL(img.url);
  if (img.thumbUrl) URL.revokeObjectURL(img.thumbUrl);
  $(`#card-${id}`)?.remove();
  if (state.detailId === id) $('#detail-dialog').close();
  refreshAfterChange();
}

function clearImages() {
  if (state.run) state.run.cancel = true;
  for (const img of state.images) {
    URL.revokeObjectURL(img.url);
    if (img.thumbUrl) URL.revokeObjectURL(img.thumbUrl);
  }
  state.images = [];
  state.lastRun = null;
  $('#image-messages').innerHTML = messageHtml('info', 'All images were cleared. The dataset (if any) is still loaded.');
  refreshAfterChange();
}

function refreshAfterChange() {
  renderGallery();
  updateImageControls();
}

function rematchImages() {
  for (const img of state.images) img.match = state.index ? matchImage(img.name, state.index) : null;
  renderGallery();
  updateStats();
}

$('#clear-images-btn').addEventListener('click', clearImages);
$('#analyse-btn').addEventListener('click', analysePending);
$('#stop-btn').addEventListener('click', () => {
  if (state.run) state.run.cancel = true;
});
$('#download-report-btn').addEventListener('click', () => {
  const rows = state.images.filter((i) => i.status === 'done' || i.status === 'error');
  if (!rows.length) return;
  downloadReport(rows);
  toast(`Report downloaded (${rows.length} image${rows.length === 1 ? '' : 's'})`);
});

function updateImageControls() {
  const ready = state.images.filter((i) => i.status === 'ready').length;
  const running = !!state.run;
  $('#image-count').textContent = state.images.length;
  const analyseBtn = $('#analyse-btn');
  analyseBtn.disabled = running || ready === 0;
  analyseBtn.textContent = running ? 'Analysing…' : ready ? `Analyse ${ready} image${ready === 1 ? '' : 's'}` : 'Analyse images';
  $('#stop-btn').hidden = !running;
  $('#clear-images-btn').disabled = state.images.length === 0;
  $('#download-report-btn').disabled = running || !state.images.some((i) => i.status === 'done' || i.status === 'error');
  updateStats();
}

// ---------------------------------------------------------------------------
// Analysis loop: one image at a time, yielding to the browser between images.
// ---------------------------------------------------------------------------

async function analysePending() {
  if (state.run) return;
  const queue = state.images.filter((i) => i.status === 'ready');
  if (!queue.length) return;
  queue.forEach((i) => (i.status = 'queued'));
  state.run = { total: queue.length, processed: 0, ok: 0, failed: 0, current: null, cancel: false };
  renderGallery();
  updateImageControls();
  updateProgress();
  document.getElementById('results').scrollIntoView({ behavior: 'smooth', block: 'start' });

  for (const img of queue) {
    if (state.run.cancel) break;
    if (!state.images.includes(img)) {
      state.run.processed++;
      continue;
    }
    img.status = 'analysing';
    state.run.current = img.name;
    updateCard(img);
    updateProgress();
    await yieldToBrowser();
    try {
      const result = await analyseImage(img.file);
      if (result.thumbnail) {
        img.thumbUrl = URL.createObjectURL(result.thumbnail);
      }
      delete result.thumbnail;
      img.result = result;
      img.status = 'done';
      state.run.ok++;
    } catch (err) {
      img.status = 'error';
      img.error = err?.message || 'The image could not be processed.';
      state.run.failed++;
    }
    state.run.processed++;
    if (!state.images.includes(img) && img.thumbUrl) URL.revokeObjectURL(img.thumbUrl);
    updateCard(img);
    updateProgress();
    updateStats();
    await yieldToBrowser();
  }

  const cancelled = state.run.cancel;
  for (const img of state.images) if (img.status === 'queued') img.status = 'ready';
  state.lastRun = { ...state.run, cancelled };
  state.run = null;
  renderGallery();
  updateImageControls();
  updateProgress();
  toast(cancelled ? 'Analysis stopped' : 'Analysis complete');
}

function updateProgress() {
  const label = $('#progress-label');
  const pctEl = $('#progress-pct');
  const fill = $('#progress-fill');
  const bar = fill.parentElement;
  let pct = 0;
  if (state.run) {
    const r = state.run;
    pct = Math.round((r.processed / r.total) * 100);
    label.textContent = `Analysing ${Math.min(r.processed + 1, r.total)} of ${r.total}${r.current ? ` · ${r.current}` : ''}`;
    bar.classList.add('running');
  } else if (state.lastRun && state.images.length) {
    const r = state.lastRun;
    pct = Math.round((r.processed / r.total) * 100);
    label.textContent = `${r.cancelled ? 'Stopped' : 'Finished'}: ${r.ok} analysed successfully, ${r.failed} failed${r.cancelled ? `, ${r.total - r.processed} not analysed` : ''}`;
    bar.classList.remove('running');
  } else {
    label.textContent = 'No analysis running';
    bar.classList.remove('running');
  }
  fill.style.width = `${pct}%`;
  pctEl.textContent = `${pct}%`;
  bar.setAttribute('aria-valuenow', String(pct));
}

function updateStats() {
  const imgs = state.images;
  const done = imgs.filter((i) => i.status === 'done');
  const set = (k, v) => ($(`[data-stat="${k}"]`).textContent = v);
  set('total', imgs.length);
  set('done', done.length);
  set('likely', done.filter((i) => i.result.category === CATEGORY.LIKELY).length);
  set('less', done.filter((i) => i.result.category === CATEGORY.LESS).length);
  set('error', imgs.filter((i) => i.status === 'error').length);
  set('matched', state.index ? imgs.filter((i) => i.match?.status === 'matched').length : '—');
}

// ---------------------------------------------------------------------------
// Gallery
// ---------------------------------------------------------------------------

$('#search-input').addEventListener('input', (e) => {
  state.search = e.target.value.trim().toLowerCase();
  renderGallery();
});
$('#sort-select').addEventListener('change', (e) => {
  state.sort = e.target.value;
  renderGallery();
});
$$('.seg-btn').forEach((btn) =>
  btn.addEventListener('click', () => {
    $$('.seg-btn').forEach((b) => b.classList.toggle('active', b === btn));
    state.filter = btn.dataset.filter;
    renderGallery();
  })
);

function visibleImages() {
  let list = state.images.filter((img) => {
    switch (state.filter) {
      case 'likely':
        return img.status === 'done' && img.result.category === CATEGORY.LIKELY;
      case 'less':
        return img.status === 'done' && img.result.category === CATEGORY.LESS;
      case 'pending':
        return ['ready', 'queued', 'analysing'].includes(img.status);
      case 'error':
        return img.status === 'error';
      case 'matched':
        return img.match?.status === 'matched';
      default:
        return true;
    }
  });
  if (state.search) {
    const q = state.search;
    list = list.filter((img) => {
      const hay = [img.name, ...(img.match?.adIds || []), ...(img.match?.creativeIds || [])].join(' ').toLowerCase();
      return hay.includes(q);
    });
  }
  const scoreOf = (i) => (i.status === 'done' ? i.result.score : null);
  if (state.sort === 'score-desc' || state.sort === 'score-asc') {
    const dir = state.sort === 'score-desc' ? -1 : 1;
    list = [...list].sort((a, b) => {
      const sa = scoreOf(a);
      const sb = scoreOf(b);
      if (sa == null && sb == null) return a.id - b.id;
      if (sa == null) return 1;
      if (sb == null) return -1;
      return (sa - sb) * dir || a.id - b.id;
    });
  } else if (state.sort === 'name') {
    list = [...list].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
  }
  return list;
}

const STATUS_LABEL = { ready: 'Ready', queued: 'Queued', analysing: 'Analysing…', done: 'Analysed', error: 'Error' };

function matchChip(img) {
  if (!state.index) return '';
  const m = img.match;
  if (m?.status === 'matched') {
    const mm = m.metrics;
    const bits = [];
    if (mm.ctr != null) bits.push(`CTR ${fmtPct(mm.ctr)}`);
    if (mm.roas != null) bits.push(`ROAS ${fmtNum(mm.roas, 2)}×`);
    if (!bits.length && mm.impressions != null) bits.push(`${fmtNum(mm.impressions)} impr.`);
    return `<div class="match match-yes" title="Matched by ${esc(m.method)} · dataset row(s) ${esc(m.rowNumbers.join(', '))}">
      <span class="match-tag">Dataset match · ${esc(m.method)} ${esc(m.key)}</span>
      ${bits.length ? `<span class="match-metrics">${esc(bits.join(' · '))}</span>` : ''}
    </div>`;
  }
  if (m?.status === 'ambiguous') return `<div class="match match-amb" title="${esc(m.reason)}"><span class="match-tag">Ambiguous match, so not linked</span></div>`;
  return '<div class="match match-no"><span class="match-tag">No dataset match, analysed independently</span></div>';
}

function cardHtml(img) {
  const done = img.status === 'done';
  const likely = done && img.result.category === CATEGORY.LIKELY;
  const f = img.result?.features;
  return `
  <article class="img-card status-${img.status} ${done ? (likely ? 'is-likely' : 'is-less') : ''}" id="card-${img.id}" data-id="${img.id}">
    <div class="thumb">
      <img src="${img.thumbUrl || img.url}" alt="Preview of ${esc(img.name)}" loading="lazy" decoding="async" />
      <span class="status-badge">${img.status === 'analysing' ? '<span class="spinner"></span>' : ''}${STATUS_LABEL[img.status]}</span>
      ${done ? `<div class="score-badge" aria-label="Visual score ${img.result.score} out of 100"><span>${img.result.score}</span><small>/100</small></div>` : ''}
      <button class="icon-btn remove-btn" type="button" data-action="remove" aria-label="Remove ${esc(img.name)}" ${img.status === 'analysing' ? 'disabled' : ''}>
        <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M18.3 5.7 12 12l6.3 6.3-1.4 1.4L10.6 13.4 4.3 19.7 2.9 18.3 9.2 12 2.9 5.7 4.3 4.3l6.3 6.3 6.3-6.3 1.4 1.4Z"/></svg>
      </button>
    </div>
    <div class="card-body">
      <div class="fname" title="${esc(img.name)}">${esc(img.name)}</div>
      <div class="fmeta">${formatBytes(img.size)}${f ? ` · ${f.width}×${f.height} · ${esc(f.ratioLabel)}` : ''}</div>
      ${done ? `<div class="verdict ${likely ? 'verdict-likely' : 'verdict-less'}">${likely ? '▲' : '▼'} ${esc(img.result.category)}</div>` : ''}
      ${img.status === 'error' ? `<p class="card-error">${esc(img.error)}</p>` : ''}
      ${matchChip(img)}
      ${
        done
          ? `<p class="expl">${esc(img.result.explanation)}</p>
             <details class="card-more"><summary>${img.result.suggestions.length} suggestions to improve</summary>
               <ul>${img.result.suggestions.map((s) => `<li>${esc(s)}</li>`).join('')}</ul>
             </details>
             <p class="limit-note">Estimate only. This is a rule-based visual prototype and does not guarantee reach.</p>`
          : ''
      }
      <button class="btn btn-ghost btn-sm card-detail-btn" type="button" data-action="details">${done ? 'View full analysis' : 'View details'}</button>
    </div>
  </article>`;
}

function renderGallery() {
  const gallery = $('#gallery');
  const list = visibleImages();
  gallery.innerHTML = list.map(cardHtml).join('');
  const empty = $('#gallery-empty');
  if (!state.images.length) {
    empty.hidden = false;
    empty.querySelector('p').innerHTML = '<strong>No images yet.</strong> Add advertisement images in the <a href="#images">image upload</a> section to preview and analyse them here.';
  } else if (!list.length) {
    empty.hidden = false;
    empty.querySelector('p').innerHTML = '<strong>No images match the current search or filter.</strong>';
  } else {
    empty.hidden = true;
  }
  updateStats();
}

let rerenderTimer = null;
function updateCard(img) {
  const el = $(`#card-${img.id}`);
  const ordered = state.sort !== 'upload' && state.sort !== 'name';
  if (ordered || state.filter !== 'all') {
    // Position or visibility may change: debounce a full render.
    clearTimeout(rerenderTimer);
    rerenderTimer = setTimeout(renderGallery, 250);
  }
  if (el) el.outerHTML = cardHtml(img);
  if (state.detailId === img.id && $('#detail-dialog').open) openDetail(img.id);
}

$('#gallery').addEventListener('click', (e) => {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const id = Number(btn.closest('[data-id]').dataset.id);
  if (btn.dataset.action === 'remove') removeImage(id);
  if (btn.dataset.action === 'details') openDetail(id);
});

// ---------------------------------------------------------------------------
// Detail dialog
// ---------------------------------------------------------------------------

const dialog = $('#detail-dialog');
dialog.addEventListener('click', (e) => {
  if (e.target === dialog) dialog.close();
  const act = e.target.closest('[data-dlg]')?.dataset.dlg;
  if (act === 'close') dialog.close();
  if (act === 'prev' || act === 'next') {
    const list = visibleImages();
    const i = list.findIndex((x) => x.id === state.detailId);
    const next = list[(i + (act === 'next' ? 1 : -1) + list.length) % list.length];
    if (next) openDetail(next.id);
  }
});
dialog.addEventListener('close', () => (state.detailId = null));

function openDetail(id) {
  const img = state.images.find((i) => i.id === id);
  if (!img) return;
  state.detailId = id;
  const r = img.result;
  const f = r?.features;
  const likely = r?.category === CATEGORY.LIKELY;

  const featureRows = f
    ? [
        ['Dimensions', `${f.width} × ${f.height} px (${fmtNum(f.megapixels, 2)} MP)`],
        ['Aspect ratio', `${f.ratioLabel}, nearest standard: ${f.nearestFormat} (${fmtNum(f.formatDeviation * 100, 1)}% off)`],
        ['File size', formatBytes(f.fileSize)],
        ['Brightness (mean luminance)', fmtPct(f.brightness * 100, 1)],
        ['Contrast (luminance std. dev.)', fmtPct(f.contrast * 100, 1)],
        ['Colourfulness (Hasler–Süsstrunk)', fmtNum(f.colourfulness, 1)],
        ['Mean saturation', fmtPct(f.saturation * 100, 1)],
        ['Neutral / greyscale pixels', fmtPct(f.neutralShare * 100, 1)],
        ['Dark / bright pixels', `${fmtPct(f.darkShare * 100, 1)} / ${fmtPct(f.brightShare * 100, 1)}`],
        ['Clarity (Laplacian variance)', fmtNum(f.sharpness, 0)],
        ['Edge density (Sobel)', fmtPct(f.edgeDensity * 100, 1)],
        ['Text-like detail (approx., not scored)', fmtPct(f.textLikeCoverage * 100, 1)],
        ['Measured at', `${f.analysedWidth} × ${f.analysedHeight} px`],
      ]
    : [];

  const maxHue = f ? Math.max(1, ...f.hueDistribution.map((h) => h.pct)) : 1;
  const hueColours = ['#ef4444', '#f97316', '#eab308', '#84cc16', '#22c55e', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6', '#8b5cf6', '#d946ef', '#f43f5e'];

  let matchBlock = '';
  if (!state.index) {
    matchBlock = '<p class="muted">No dataset is loaded. This image was analysed on its own.</p>';
  } else if (img.match?.status === 'matched') {
    const m = img.match;
    const mm = m.metrics;
    const rows = [
      ['Matched by', `${m.method}: ${m.key}`],
      ['Dataset row(s)', `${m.rowNumbers.slice(0, 20).join(', ')}${m.rowNumbers.length > 20 ? ` …(+${m.rowNumbers.length - 20})` : ''}`],
      m.adIds.length && ['Ad ID(s)', m.adIds.join(', ')],
      m.creativeIds.length && ['Creative ID(s)', m.creativeIds.join(', ')],
      m.platforms.length && ['Platform(s)', m.platforms.join(', ')],
      mm.spend != null && ['Spend', fmtNum(mm.spend, 2)],
      mm.impressions != null && ['Impressions', fmtNum(mm.impressions)],
      mm.clicks != null && ['Clicks', fmtNum(mm.clicks)],
      mm.purchases != null && ['Purchases', fmtNum(mm.purchases)],
      mm.revenue != null && ['Revenue', fmtNum(mm.revenue, 2)],
      state.dataset.metricStatus.ctr.available && ['CTR', fmtPct(mm.ctr)],
      state.dataset.metricStatus.cvr.available && ['Conversion rate', fmtPct(mm.cvr)],
      state.dataset.metricStatus.roas.available && ['ROAS', mm.roas == null ? '—' : `${fmtNum(mm.roas, 2)}×`],
    ].filter(Boolean);
    matchBlock = `<table class="kv">${rows.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')}</table>
      <p class="muted small">These are historical values from your uploaded dataset${m.rowNumbers.length > 1 ? `, totalled across ${m.rowNumbers.length} rows` : ''}. “—” means the value could not be calculated validly.</p>`;
  } else if (img.match?.status === 'ambiguous') {
    matchBlock = `<p class="muted">${esc(img.match.reason)}</p>`;
  } else {
    matchBlock = '<p class="muted">No dataset row has a filename, ad ID or creative ID that exactly matches this filename, so the image was analysed on its own.</p>';
  }

  $('#detail-body').innerHTML = `
    <header class="dlg-head">
      <div>
        <h2 id="detail-title" title="${esc(img.name)}">${esc(img.name)}</h2>
        <p class="muted small">${formatBytes(img.size)} · ${STATUS_LABEL[img.status]}</p>
      </div>
      <div class="dlg-nav">
        <button class="icon-btn" type="button" data-dlg="prev" aria-label="Previous image">‹</button>
        <button class="icon-btn" type="button" data-dlg="next" aria-label="Next image">›</button>
        <button class="icon-btn" type="button" data-dlg="close" aria-label="Close details">✕</button>
      </div>
    </header>
    <div class="dlg-grid">
      <div class="dlg-media">
        <img src="${img.url}" alt="Full preview of ${esc(img.name)}" />
        ${
          f
            ? `<h3>Dominant colours</h3>
               <div class="swatches">${f.dominantColours.map((c) => `<div class="swatch"><span style="background:${c.hex}"></span><code>${c.hex}</code><small>${fmtNum(c.pct, 0)}%</small></div>`).join('')}</div>
               <h3>Colour distribution (hue, % of pixels)</h3>
               <div class="hue-bars">${f.hueDistribution
                 .map((h, i) => `<div class="hue" title="${h.name}: ${fmtNum(h.pct, 1)}%"><span style="height:${Math.max(2, (h.pct / maxHue) * 100)}%;background:${hueColours[i]}"></span><small>${h.name.slice(0, 3)}</small></div>`)
                 .join('')}</div>
               <p class="muted small">${fmtPct(f.neutralShare * 100, 0)} of pixels are neutral (grey, white, black or very dark) and are not shown in the hue chart.</p>`
            : ''
        }
      </div>
      <div class="dlg-info">
        ${
          r
            ? `<div class="dlg-score ${likely ? 'is-likely' : 'is-less'}">
                 <div class="ring" style="--p:${r.score}"><span>${r.score}</span><small>/100</small></div>
                 <div>
                   <div class="verdict ${likely ? 'verdict-likely' : 'verdict-less'}">${likely ? '▲' : '▼'} ${esc(r.category)}</div>
                   <p class="muted small">Visual analysis score · threshold ${LIKELY_THRESHOLD} · rule-based prototype</p>
                 </div>
               </div>
               <p>${esc(r.explanation)}</p>
               <h3>Score breakdown</h3>
               <div class="factors">${r.factors
                 .map(
                   (x) => `<div class="factor factor-${x.status}">
                     <div class="factor-top"><span>${esc(x.label)}</span><span class="mono">${fmtNum(x.points, 1)} / ${x.max}</span></div>
                     <div class="factor-bar"><span style="width:${(x.points / x.max) * 100}%"></span></div>
                     <div class="factor-val muted small">${esc(x.value)}</div>
                   </div>`
                 )
                 .join('')}</div>
               <h3>Suggestions</h3>
               <ol class="suggestions">${r.suggestions.map((s) => `<li>${esc(s)}</li>`).join('')}</ol>`
            : img.status === 'error'
              ? messageHtml('error', `<strong>This image could not be processed.</strong> ${esc(img.error)}`)
              : messageHtml('info', 'This image has not been analysed yet. Click <strong>Analyse images</strong> to run the visual analysis.')
        }
        <h3>Dataset metrics</h3>
        ${matchBlock}
        ${f ? `<h3>Measured features</h3><table class="kv">${featureRows.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')}</table>` : ''}
        ${r ? `<div class="notice notice-warn"><strong>Analysis limitations</strong><ul class="msg-list">${r.limitations.map((l) => `<li>${esc(l)}</li>`).join('')}</ul></div>` : ''}
      </div>
    </div>`;
  if (!dialog.open) dialog.showModal();
}

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

const navToggle = $('.nav-toggle');
navToggle.addEventListener('click', () => {
  const open = document.body.classList.toggle('nav-open');
  navToggle.setAttribute('aria-expanded', String(open));
});
$$('#nav a').forEach((a) =>
  a.addEventListener('click', () => {
    document.body.classList.remove('nav-open');
    navToggle.setAttribute('aria-expanded', 'false');
  })
);

renderGallery();
updateImageControls();
updateProgress();