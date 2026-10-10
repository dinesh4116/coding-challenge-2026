// Dataset loading: real CSV / Excel parsing, column detection, validation and metric calculation.
import Papa from 'papaparse';
import { getExt, cellToString } from './utils.js';

export const MAX_DATASET_BYTES = 25 * 1024 * 1024;
const ACCEPTED_EXT = ['csv', 'xlsx', 'xls'];

/**
 * Recognised fields and the header variations that map to them.
 * Headers are compared after lower-casing and removing every non-alphanumeric character,
 * so "Amount Spent (USD)" becomes "amountspentusd". Aliases are tried in order of preference.
 */
export const FIELDS = {
  ad_id: {
    label: 'Ad ID',
    aliases: ['adid', 'adidentifier', 'adcode', 'adnumber', 'adref', 'adreference', 'ad', 'id'],
  },
  creative_id: {
    label: 'Creative ID',
    aliases: ['creativeid', 'creativeidentifier', 'creativecode', 'creativeref', 'creative', 'assetid'],
  },
  filename: {
    label: 'Filename',
    aliases: ['filename', 'imagefilename', 'creativefilename', 'imagename', 'imagefile', 'creativefile', 'assetname', 'file', 'image'],
  },
  platform: {
    label: 'Platform',
    aliases: ['platform', 'adplatform', 'channel', 'network', 'publisherplatform', 'source'],
  },
  spend: {
    label: 'Spend',
    numeric: true,
    aliases: ['spend', 'amountspent', 'amountspentusd', 'amountspentinr', 'amountspenteur', 'amountspentgbp', 'adspend', 'totalspend', 'spendusd', 'spendinr', 'cost', 'costusd', 'totalcost', 'mediacost'],
  },
  impressions: {
    label: 'Impressions',
    numeric: true,
    aliases: ['impressions', 'impression', 'totalimpressions', 'impr', 'imps', 'imp'],
  },
  clicks: {
    label: 'Clicks',
    numeric: true,
    aliases: ['clicks', 'linkclicks', 'clicksall', 'totalclicks', 'outboundclicks', 'click'],
  },
  purchases: {
    label: 'Purchases',
    numeric: true,
    aliases: ['purchases', 'purchase', 'websitepurchases', 'totalpurchases', 'conversions', 'conversion', 'totalconversions', 'orders', 'conv'],
  },
  revenue: {
    label: 'Revenue',
    numeric: true,
    aliases: ['revenue', 'totalrevenue', 'revenueusd', 'revenueinr', 'purchasevalue', 'purchaseconversionvalue', 'websitepurchasesconversionvalue', 'conversionvalue', 'totalconversionvalue', 'sales', 'salesvalue', 'totalsales', 'value'],
  },
};

export const NUMERIC_FIELDS = Object.keys(FIELDS).filter((k) => FIELDS[k].numeric);

export const normalizeHeader = (h) => String(h ?? '').toLowerCase().replace(/[^a-z0-9]/g, '');

/**
 * Parse a numeric cell. Accepts currency symbols, thousands separators (commas) and
 * accounting negatives "(12.50)". Returns null for anything that is not clearly a number.
 */
export function parseNumber(v) {
  if (v == null) return null;
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  let s = String(v).trim();
  if (!s) return null;
  let negative = false;
  if (/^\(.*\)$/.test(s)) {
    negative = true;
    s = s.slice(1, -1);
  }
  s = s.replace(/[\s$€£₹¥,]/g, '').replace(/^(usd|inr|eur|gbp|rs\.?)/i, '').replace(/(usd|inr|eur|gbp)$/i, '');
  if (!/^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i.test(s)) return null;
  const n = parseFloat(s);
  if (!Number.isFinite(n)) return null;
  return negative ? -n : n;
}

/** Map recognised fields -> original header name. */
export function detectColumns(headers) {
  const normalized = headers.map(normalizeHeader);
  const used = new Set();
  const mapping = {};
  for (const [field, def] of Object.entries(FIELDS)) {
    for (const alias of def.aliases) {
      const idx = normalized.findIndex((n, i) => n === alias && !used.has(i));
      if (idx !== -1) {
        mapping[field] = headers[idx];
        used.add(idx);
        break;
      }
    }
  }
  return mapping;
}

function parseCsvFile(file) {
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: false,
      skipEmptyLines: 'greedy',
      complete: (res) => resolve({ rows: res.data, parseErrors: res.errors || [] }),
      error: (err) => reject(new Error(`The CSV file could not be read: ${err?.message || err}`)),
    });
  });
}

async function parseExcelFile(file) {
  const XLSX = await import('xlsx');
  const buffer = await file.arrayBuffer();
  let workbook;
  try {
    workbook = XLSX.read(buffer, { type: 'array', cellDates: true });
  } catch (err) {
    throw new Error('The Excel file could not be opened. It may be corrupted, password-protected, or not a real Excel workbook.');
  }
  const sheetName = workbook.SheetNames.find((n) => workbook.Sheets[n]?.['!ref']);
  if (!sheetName) throw new Error('The Excel workbook has no sheets that contain data.');
  const rows = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { header: 1, defval: '', raw: true, blankrows: false });
  return { rows, sheetName, sheetCount: workbook.SheetNames.length, parseErrors: [] };
}

const isBlankRow = (row) => !row || row.every((c) => cellToString(c).trim() === '');

function buildHeaders(rawHeaderRow) {
  const seen = new Map();
  return rawHeaderRow.map((h, i) => {
    let name = cellToString(h).trim() || `Column ${i + 1}`;
    const count = seen.get(name.toLowerCase()) || 0;
    seen.set(name.toLowerCase(), count + 1);
    if (count > 0) name = `${name} (${count + 1})`;
    return name;
  });
}

/**
 * Read and analyse a dataset file. Throws an Error with a user-friendly message for fatal problems.
 * Returns { info, headers, rows, records, mapping, warnings, metricStatus, summary, idDuplicates }.
 */
export async function loadDataset(file) {
  const ext = getExt(file.name);
  if (!ACCEPTED_EXT.includes(ext)) {
    throw new Error(`“${file.name}” is not a supported dataset. Please upload a .csv, .xlsx or .xls file.`);
  }
  if (file.size === 0) throw new Error(`“${file.name}” is empty (0 bytes).`);
  if (file.size > MAX_DATASET_BYTES) throw new Error(`“${file.name}” is larger than the 25 MB limit for in-browser parsing.`);

  const parsed = ext === 'csv' ? await parseCsvFile(file) : await parseExcelFile(file);
  const warnings = [];

  if (parsed.parseErrors.length) {
    const first = parsed.parseErrors[0];
    warnings.push(`${parsed.parseErrors.length} formatting issue(s) were found while reading the CSV (first: ${first.message}${Number.isInteger(first.row) ? ` near row ${first.row + 1}` : ''}). Affected rows may be incomplete.`);
  }
  if (parsed.sheetCount > 1) {
    warnings.push(`The workbook has ${parsed.sheetCount} sheets. Only the first sheet with data (“${parsed.sheetName}”) was read.`);
  }

  const allRows = parsed.rows;
  const headerIdx = allRows.findIndex((r) => !isBlankRow(r));
  if (headerIdx === -1) throw new Error('The file does not contain any data.');

  const headers = buildHeaders(allRows[headerIdx]);
  const dataRows = allRows.slice(headerIdx + 1).filter((r) => !isBlankRow(r));
  if (!dataRows.length) throw new Error('A header row was found, but the file contains no data rows beneath it.');

  let overflowRows = 0;
  const rows = dataRows.map((r) => {
    if (r.length > headers.length && r.slice(headers.length).some((c) => cellToString(c).trim() !== '')) overflowRows++;
    const obj = {};
    headers.forEach((h, i) => {
      obj[h] = r[i] ?? '';
    });
    return obj;
  });
  if (overflowRows) warnings.push(`${overflowRows} row(s) have more values than there are column headers. The extra values were ignored.`);

  const mapping = detectColumns(headers);
  const hasPerfColumns = NUMERIC_FIELDS.some((f) => mapping[f]);
  if (!hasPerfColumns && !mapping.ad_id && !mapping.creative_id) {
    warnings.push('No advertisement performance columns were recognised. The data is shown as a plain table, and no metrics were calculated.');
  }

  // Normalise each row into a record with validated numeric values.
  const invalidCounts = {};
  const negativeCounts = {};
  let ctrInvalid = 0;
  let cvrInvalid = 0;
  const records = rows.map((raw, index) => {
    const rec = { rowNumber: index + 1, raw };
    for (const f of ['ad_id', 'creative_id', 'filename', 'platform']) {
      rec[f] = mapping[f] ? cellToString(raw[mapping[f]]).trim() || null : null;
    }
    for (const f of NUMERIC_FIELDS) {
      if (!mapping[f]) {
        rec[f] = null;
        continue;
      }
      const cell = raw[mapping[f]];
      const blank = cellToString(cell).trim() === '';
      const n = parseNumber(cell);
      if (n == null) {
        if (!blank) invalidCounts[f] = (invalidCounts[f] || 0) + 1;
        rec[f] = null;
      } else if (n < 0) {
        negativeCounts[f] = (negativeCounts[f] || 0) + 1;
        rec[f] = null;
      } else {
        rec[f] = n;
      }
    }
    rec.ctr = null;
    rec.cvr = null;
    rec.roas = null;
    if (rec.clicks != null && rec.impressions != null && rec.impressions > 0) {
      if (rec.clicks <= rec.impressions) rec.ctr = (rec.clicks / rec.impressions) * 100;
      else ctrInvalid++;
    }
    if (rec.purchases != null && rec.clicks != null && rec.clicks > 0) {
      if (rec.purchases <= rec.clicks) rec.cvr = (rec.purchases / rec.clicks) * 100;
      else cvrInvalid++;
    }
    if (rec.revenue != null && rec.spend != null && rec.spend > 0) rec.roas = rec.revenue / rec.spend;
    return rec;
  });

  for (const [f, n] of Object.entries(invalidCounts)) {
    warnings.push(`${n} value(s) in “${mapping[f]}” (${FIELDS[f].label}) are not valid numbers and were left out of the calculations.`);
  }
  for (const [f, n] of Object.entries(negativeCounts)) {
    warnings.push(`${n} negative value(s) in “${mapping[f]}” (${FIELDS[f].label}) were treated as invalid.`);
  }
  if (ctrInvalid) warnings.push(`${ctrInvalid} row(s) report more clicks than impressions, so CTR was not calculated for them.`);
  if (cvrInvalid) warnings.push(`${cvrInvalid} row(s) report more purchases than clicks, so conversion rate was not calculated for them.`);

  const metricStatus = buildMetricStatus(mapping);

  const idDuplicates = {};
  for (const f of ['ad_id', 'creative_id']) {
    if (!mapping[f]) continue;
    const counts = new Map();
    for (const r of records) if (r[f]) counts.set(r[f].toLowerCase(), (counts.get(r[f].toLowerCase()) || 0) + 1);
    const dupes = [...counts.values()].filter((c) => c > 1).length;
    if (dupes) {
      idDuplicates[f] = dupes;
      warnings.push(`${dupes} ${FIELDS[f].label} value(s) appear on more than one row. Matched images show totals across those rows.`);
    }
  }

  return {
    info: {
      name: file.name,
      ext,
      type: ext === 'csv' ? 'CSV (comma-separated values)' : ext === 'xlsx' ? 'Excel workbook (.xlsx)' : 'Excel 97–2003 workbook (.xls)',
      size: file.size,
      sheetName: parsed.sheetName || null,
    },
    headers,
    rows,
    records,
    mapping,
    warnings,
    metricStatus,
    summary: aggregate(records, mapping),
    idDuplicates,
  };
}

function buildMetricStatus(mapping) {
  const need = {
    ctr: { label: 'CTR', requires: ['clicks', 'impressions'], formula: 'clicks ÷ impressions × 100' },
    cvr: { label: 'Conversion rate', requires: ['purchases', 'clicks'], formula: 'purchases ÷ clicks × 100' },
    roas: { label: 'ROAS', requires: ['revenue', 'spend'], formula: 'revenue ÷ spend' },
  };
  const out = {};
  for (const [k, def] of Object.entries(need)) {
    const missing = def.requires.filter((f) => !mapping[f]).map((f) => FIELDS[f].label);
    out[k] = { ...def, available: missing.length === 0, missing };
  }
  return out;
}

/**
 * Totals and ratio metrics across a set of records. Ratios only use rows where both inputs are valid,
 * and are null whenever they cannot be calculated validly.
 */
export function aggregate(records, mapping) {
  const out = { rowCount: records.length };
  for (const f of NUMERIC_FIELDS) {
    if (!mapping[f]) {
      out[f] = null;
      continue;
    }
    let total = 0;
    let n = 0;
    for (const r of records) {
      if (r[f] != null) {
        total += r[f];
        n++;
      }
    }
    out[f] = n ? total : null;
  }
  // Sum numerator/denominator over rows where both are valid. For rate metrics, rows where the
  // numerator exceeds the denominator (e.g. more clicks than impressions) are excluded as invalid.
  const pair = (a, b, isRate) => {
    let ta = 0;
    let tb = 0;
    let n = 0;
    for (const r of records) {
      if (r[a] != null && r[b] != null && (!isRate || r[a] <= r[b])) {
        ta += r[a];
        tb += r[b];
        n++;
      }
    }
    return n ? [ta, tb] : null;
  };
  const ctr = mapping.clicks && mapping.impressions ? pair('clicks', 'impressions', true) : null;
  out.ctr = ctr && ctr[1] > 0 ? (ctr[0] / ctr[1]) * 100 : null;
  const cvr = mapping.purchases && mapping.clicks ? pair('purchases', 'clicks', true) : null;
  out.cvr = cvr && cvr[1] > 0 ? (cvr[0] / cvr[1]) * 100 : null;
  const roas = mapping.revenue && mapping.spend ? pair('revenue', 'spend', false) : null;
  out.roas = roas && roas[1] > 0 ? roas[0] / roas[1] : null;
  return out;
}