// Builds the downloadable CSV report from real analysis results only.
import Papa from 'papaparse';

const r2 = (v, d = 2) => (v == null || !Number.isFinite(v) ? '' : Number(v.toFixed(d)));

export function buildReportRows(images) {
  return images.map((img) => {
    const f = img.result?.features;
    const m = img.match?.status === 'matched' ? img.match : null;
    const mm = m?.metrics;
    return {
      filename: img.name,
      file_size_kb: r2(img.size / 1024, 1),
      status: img.status === 'done' ? 'analysed' : img.status === 'error' ? 'error' : 'not analysed',
      error: img.error || '',
      width_px: f ? f.width : '',
      height_px: f ? f.height : '',
      aspect_ratio: f ? f.ratioLabel : '',
      nearest_ad_format: f ? f.nearestFormat : '',
      brightness_pct: f ? r2(f.brightness * 100, 1) : '',
      contrast_pct: f ? r2(f.contrast * 100, 1) : '',
      colourfulness: f ? r2(f.colourfulness, 1) : '',
      mean_saturation_pct: f ? r2(f.saturation * 100, 1) : '',
      sharpness_laplacian_var: f ? r2(f.sharpness, 0) : '',
      edge_density_pct: f ? r2(f.edgeDensity * 100, 1) : '',
      text_like_coverage_pct_approx: f ? r2(f.textLikeCoverage * 100, 1) : '',
      dominant_colours: f ? f.dominantColours.map((c) => `${c.hex} (${c.pct.toFixed(0)}%)`).join('; ') : '',
      visual_score: img.result ? img.result.score : '',
      category: img.result ? img.result.category : '',
      explanation: img.result ? img.result.explanation : '',
      recommendations: img.result ? img.result.suggestions.join(' | ') : '',
      dataset_match: img.match ? (m ? `${m.method}: ${m.key}` : img.match.status === 'ambiguous' ? 'ambiguous (not matched)' : 'no match') : 'no dataset loaded',
      matched_rows: m ? m.rowNumbers.join(';') : '',
      platform: m ? m.platforms.join('; ') : '',
      spend: mm ? r2(mm.spend) : '',
      impressions: mm ? r2(mm.impressions, 0) : '',
      clicks: mm ? r2(mm.clicks, 0) : '',
      purchases: mm ? r2(mm.purchases, 0) : '',
      revenue: mm ? r2(mm.revenue) : '',
      ctr_pct: mm ? r2(mm.ctr, 3) : '',
      conversion_rate_pct: mm ? r2(mm.cvr, 3) : '',
      roas: mm ? r2(mm.roas, 3) : '',
      method_note: img.result ? 'Rule-based visual-scoring prototype; estimate only, not a guarantee of reach.' : '',
    };
  });
}

export function downloadReport(images) {
  const csv = Papa.unparse(buildReportRows(images));
  // BOM so Excel opens UTF-8 characters correctly.
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `adreach-ai-report-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}