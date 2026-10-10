// Conservative image <-> dataset matching. A match is only made when it is exact and unambiguous.
import { aggregate } from './dataset.js';
import { baseName } from './utils.js';

const norm = (s) => String(s ?? '').trim().toLowerCase();

const AD_PREFIX = /^(ad|ads|adid|ad_id)[\s_-]+/;
const CREATIVE_PREFIX = /^(creative|creativeid|creative_id|cr)[\s_-]+/;

function addTo(map, key, rec) {
  if (!key) return;
  if (!map.has(key)) map.set(key, []);
  map.get(key).push(rec);
}

export function buildIndex(dataset) {
  const index = { filename: new Map(), ad_id: new Map(), creative_id: new Map(), mapping: dataset.mapping };
  for (const rec of dataset.records) {
    if (rec.filename) addTo(index.filename, norm(baseName(rec.filename)), rec);
    if (rec.ad_id) addTo(index.ad_id, norm(rec.ad_id), rec);
    if (rec.creative_id) addTo(index.creative_id, norm(rec.creative_id), rec);
  }
  return index;
}

function lookup(map, base, prefix) {
  if (map.has(base)) return map.get(base);
  const stripped = base.replace(prefix, '');
  if (stripped !== base && stripped && map.has(stripped)) return map.get(stripped);
  return null;
}

const sameRecords = (a, b) => a.length === b.length && a.every((r) => b.includes(r));

/**
 * Returns { status: 'matched' | 'ambiguous' | 'none', method, key, records, metrics, adIds, platforms }.
 */
export function matchImage(fileName, index) {
  if (!index) return null;
  const base = norm(baseName(fileName));
  if (!base) return { status: 'none' };

  // 1. An explicit filename column is the most reliable link.
  const byFile = index.filename.get(base);
  if (byFile) return result('matched', 'Filename column', baseName(fileName), byFile, index.mapping);

  // 2. Ad ID / creative ID equal to the filename (optionally with an "ad_" / "creative_" prefix).
  const byAd = lookup(index.ad_id, base, AD_PREFIX);
  const byCreative = lookup(index.creative_id, base, CREATIVE_PREFIX);

  if (byAd && byCreative && !sameRecords(byAd, byCreative)) {
    return { status: 'ambiguous', reason: 'The filename matches an ad ID and a creative ID that belong to different rows, so no match was made.' };
  }
  if (byAd) return result('matched', 'Ad ID', byAd[0].ad_id, byAd, index.mapping);
  if (byCreative) return result('matched', 'Creative ID', byCreative[0].creative_id, byCreative, index.mapping);
  return { status: 'none' };
}

function result(status, method, key, records, mapping) {
  const uniq = (f) => [...new Set(records.map((r) => r[f]).filter(Boolean))];
  return {
    status,
    method,
    key,
    records,
    rowNumbers: records.map((r) => r.rowNumber),
    adIds: uniq('ad_id'),
    creativeIds: uniq('creative_id'),
    platforms: uniq('platform'),
    metrics: aggregate(records, mapping),
  };
}