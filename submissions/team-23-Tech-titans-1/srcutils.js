// Small shared helpers used across modules.

const HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

export const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => HTML_ESCAPES[c]);

export function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let v = bytes;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function fmtNum(n, digits = 0) {
  if (n == null || !Number.isFinite(n)) return '—';
  return n.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export const fmtPct = (n, digits = 2) => (n == null || !Number.isFinite(n) ? '—' : `${fmtNum(n, digits)}%`);

export function getExt(name) {
  const m = /\.([^.\\/]+)$/.exec(name || '');
  return m ? m[1].toLowerCase() : '';
}

/** Filename without folder path and without extension. */
export const baseName = (name) => String(name ?? '').replace(/^.*[\\/]/, '').replace(/\.[^.]+$/, '');

/** Yield to the browser so the UI can repaint between heavy work units. */
export const yieldToBrowser = () => new Promise((resolve) => setTimeout(resolve, 0));

export const clamp = (v, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, v));

export function cellToString(v) {
  if (v == null) return '';
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? '' : v.toISOString().slice(0, 10);
  return String(v);
}