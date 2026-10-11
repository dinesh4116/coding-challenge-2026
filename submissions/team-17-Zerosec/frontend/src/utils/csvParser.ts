import Papa from 'papaparse';
import { CampaignMetricRecord, ColumnMapping, DatasetMetadata } from '../types/dashboard';

const COMMON_HEADER_ALIASES: Record<keyof ColumnMapping, string[]> = {
  dateField: ['date', 'day', 'timestamp', 'dt', 'period', 'date_day'],
  campaignField: ['campaign', 'campaign_name', 'campaign_id', 'campaignname', 'name', 'utterance', 'source'],
  spendField: ['spend', 'cost', 'amount', 'total_spend', 'spend_amount', 'budget_spent'],
  conversionsField: ['conversions', 'conv', 'conversions_count', 'orders', 'leads', 'events', 'total_conversions'],
  impressionsField: ['impressions', 'impr', 'views', 'total_impressions'],
  clicksField: ['clicks', 'link_clicks', 'total_clicks'],
  isIncidentField: ['is_incident', 'critical_warning', 'is_anomaly', 'ground_truth', 'actual_anomaly', 'label', 'target', 'has_incident'],
  incidentTypeField: ['incident_type', 'ground_truth_label', 'anomaly_type', 'incident_category', 'reason', 'label_type', 'type']
};

/**
 * Automatically inspects headers and attempts to map them to standard schema fields.
 */
export function autoMapColumns(headers: string[]): ColumnMapping {
  const normalizedHeaders = headers.map(h => h.trim().toLowerCase().replace(/[\s\-_]+/g, '_'));

  const findMatch = (aliases: string[]): string => {
    for (const alias of aliases) {
      const idx = normalizedHeaders.findIndex(h => h === alias || h.includes(alias));
      if (idx !== -1) {
        return headers[idx];
      }
    }
    return '';
  };

  return {
    dateField: findMatch(COMMON_HEADER_ALIASES.dateField) || headers[0] || '',
    campaignField: findMatch(COMMON_HEADER_ALIASES.campaignField) || headers[1] || '',
    spendField: findMatch(COMMON_HEADER_ALIASES.spendField) || headers[2] || '',
    conversionsField: findMatch(COMMON_HEADER_ALIASES.conversionsField) || headers[3] || '',
    impressionsField: findMatch(COMMON_HEADER_ALIASES.impressionsField),
    clicksField: findMatch(COMMON_HEADER_ALIASES.clicksField),
    isIncidentField: findMatch(COMMON_HEADER_ALIASES.isIncidentField),
    incidentTypeField: findMatch(COMMON_HEADER_ALIASES.incidentTypeField),
  };
}

/**
 * Parses raw CSV text or File object using PapaParse.
 */
export function parseCSV(fileOrText: File | string): Promise<{ data: any[]; headers: string[]; errors: any[] }> {
  return new Promise((resolve, reject) => {
    Papa.parse(fileOrText, {
      header: true,
      skipEmptyLines: 'greedy',
      dynamicTyping: true,
      complete: (results) => {
        const headers = results.meta.fields || [];
        resolve({
          data: results.data,
          headers,
          errors: results.errors
        });
      },
      error: (err) => {
        reject(err);
      }
    });
  });
}

/**
 * Standardizes raw row data according to mapped column definitions.
 */
export function transformRawRowsToRecords(
  rows: any[],
  mapping: ColumnMapping
): CampaignMetricRecord[] {
  return rows.map((row, idx) => {
    const rawDate = String(row[mapping.dateField] || '').trim();
    // Normalize date format if possible
    let dateStr = rawDate;
    if (rawDate && !isNaN(Date.parse(rawDate))) {
      dateStr = new Date(rawDate).toISOString().split('T')[0];
    } else if (!rawDate) {
      dateStr = `2026-01-${String((idx % 30) + 1).padStart(2, '0')}`;
    }

    const campaign = String(row[mapping.campaignField] || 'Unassigned Campaign').trim();
    const spend = Math.max(0, Number(row[mapping.spendField]) || 0);
    const conversions = Math.max(0, Number(row[mapping.conversionsField]) || 0);
    const impressions = mapping.impressionsField ? Math.max(0, Number(row[mapping.impressionsField]) || 0) : Math.round(spend * (20 + (idx % 10)));
    const clicks = mapping.clicksField ? Math.max(0, Number(row[mapping.clicksField]) || 0) : Math.round(impressions * 0.025);

    const cpa = conversions > 0 ? Number((spend / conversions).toFixed(2)) : (spend > 0 ? Number(spend.toFixed(2)) : 0);
    const cvr = clicks > 0 ? Number(((conversions / clicks) * 100).toFixed(2)) : 0;
    const ctr = impressions > 0 ? Number(((clicks / impressions) * 100).toFixed(2)) : 0;

    let is_incident: boolean | undefined = undefined;
    if (mapping.isIncidentField && row[mapping.isIncidentField] !== undefined && row[mapping.isIncidentField] !== '') {
      const val = row[mapping.isIncidentField];
      const s = String(val).trim().toLowerCase();
      is_incident = val === true || val === 1 || s === 'true' || s === '1' || s === 'yes' || s === 'critical' || (s !== 'false' && s !== '0' && s !== 'no' && s !== 'normal' && s !== 'none');
    }

    const incident_type = mapping.incidentTypeField ? String(row[mapping.incidentTypeField] || '') : undefined;

    return {
      date: dateStr,
      campaign,
      spend: Number(spend.toFixed(2)),
      conversions: Math.round(conversions),
      impressions: Math.round(impressions),
      clicks: Math.round(clicks),
      cpa,
      cvr,
      ctr,
      is_incident,
      incident_type,
      raw: row
    };
  }).sort((a, b) => a.date.localeCompare(b.date));
}

/**
 * Generates realistic 180-day sample data across 20 campaigns with seeded anomalies.
 */
export function generateSampleDataset(): { records: CampaignMetricRecord[]; metadata: DatasetMetadata } {
  const campaigns = [
    { name: 'US - Search NonBrand - E-commerce', baseSpend: 1400, baseConv: 70 },
    { name: 'US - Search Brand - Core', baseSpend: 800, baseConv: 160 },
    { name: 'US - Performance Max - Retail', baseSpend: 2200, baseConv: 110 },
    { name: 'EU - Prospecting Display', baseSpend: 950, baseConv: 25 },
    { name: 'Global - Meta Advantage+ Shopping', baseSpend: 3100, baseConv: 140 },
    { name: 'US - TikTok Video Spark Ads', baseSpend: 1800, baseConv: 45 },
    { name: 'US - B2B SaaS LeadGen Search', baseSpend: 2500, baseConv: 35 },
    { name: 'US - YouTube Action Video', baseSpend: 1200, baseConv: 30 },
    { name: 'UK - Google Shopping Smart', baseSpend: 1100, baseConv: 55 },
    { name: 'CA - Retargeting Dynamic', baseSpend: 650, baseConv: 40 },
    { name: 'APAC - Search Competitor conquest', baseSpend: 1300, baseConv: 20 },
    { name: 'US - Paid Social Instagram Reels', baseSpend: 2100, baseConv: 65 },
    { name: 'LATAM - Performance Max General', baseSpend: 850, baseConv: 30 },
    { name: 'US - LinkedIn Enterprise Decision Makers', baseSpend: 2800, baseConv: 18 },
    { name: 'Global - Affiliate Network Boost', baseSpend: 500, baseConv: 25 },
    { name: 'US - Programmatic CTV Streaming', baseSpend: 1600, baseConv: 15 },
    { name: 'US - Mobile App Install iOS', baseSpend: 1900, baseConv: 190 },
    { name: 'US - Mobile App Install Android', baseSpend: 1500, baseConv: 210 },
    { name: 'EU - Search Brand Localized', baseSpend: 750, baseConv: 95 },
    { name: 'Global - Newsletter Sponsorships', baseSpend: 600, baseConv: 20 }
  ];

  const startDate = new Date('2026-04-14'); // 180 days up to 2026-10-10
  const records: CampaignMetricRecord[] = [];

  for (let day = 0; day < 180; day++) {
    const currentDate = new Date(startDate);
    currentDate.setDate(startDate.getDate() + day);
    const dateStr = currentDate.toISOString().split('T')[0];

    // Day of week seasonality multiplier (weekends slightly lower for B2B, higher for e-comm)
    const dayOfWeek = currentDate.getDay(); // 0 is Sunday
    const weekendFactor = (dayOfWeek === 0 || dayOfWeek === 6) ? 0.85 : 1.05;

    campaigns.forEach((cmp, cIdx) => {
      let spend = cmp.baseSpend * weekendFactor * (0.9 + Math.random() * 0.2);
      let conv = cmp.baseConv * weekendFactor * (0.88 + Math.random() * 0.24);
      let isIncident = false;
      let incidentType = 'none';

      // Seeded Incidents for realistic evaluation (PS-04 Requirement)
      
      // Incident 1: Broken Conversion Tag (Days 45 to 51) on Campaign #0 (US Search NonBrand)
      if (cIdx === 0 && day >= 45 && day <= 51) {
        conv = Math.floor(Math.random() * 2); // Drops to 0-1 conversions despite active spend
        isIncident = true;
        incidentType = 'tracking_failure';
      }

      // Incident 2: Mid-Month Budget Exhaustion (Days 105 to 112) on Campaign #4 (Meta Advantage+)
      if (cIdx === 4 && day >= 105 && day <= 112) {
        spend = 0;
        conv = 0;
        isIncident = true;
        incidentType = 'budget_exhaustion';
      }

      // Incident 3: Aggressive Bid Strategy Change / CPA Spike (Days 135 to 139) on Campaign #6 (B2B LeadGen)
      if (cIdx === 6 && day >= 135 && day <= 139) {
        spend = cmp.baseSpend * 2.8; // Spend surges 180%
        conv = cmp.baseConv * 0.4;   // Conversions drop 60%
        isIncident = true;
        incidentType = 'bid_strategy_change';
      }

      // Incident 4: Broken Conversion Tag (Days 160 to 164) on Campaign #16 (App Install iOS)
      if (cIdx === 16 && day >= 160 && day <= 164) {
        conv = Math.floor(Math.random() * 3);
        isIncident = true;
        incidentType = 'tracking_failure';
      }

      // Harmless Seasonal Surge (Days 75 to 80) on Campaign #2 (Retail PMax) - NOT an incident!
      if (cIdx === 2 && day >= 75 && day <= 80) {
        spend = cmp.baseSpend * 1.5;
        conv = cmp.baseConv * 1.55; // Both spend & conversions lift proportionally!
        isIncident = false; // Harmless seasonal shift
        incidentType = 'seasonal_shift';
      }

      const impr = Math.round(spend * (18 + Math.random() * 6));
      const clicks = Math.round(impr * (0.02 + Math.random() * 0.015));
      const cpa = conv > 0 ? Number((spend / conv).toFixed(2)) : (spend > 0 ? Number(spend.toFixed(2)) : 0);
      const cvr = clicks > 0 ? Number(((conv / clicks) * 100).toFixed(2)) : 0;
      const ctr = impr > 0 ? Number(((clicks / impr) * 100).toFixed(2)) : 0;

      records.push({
        date: dateStr,
        campaign: cmp.name,
        spend: Number(spend.toFixed(2)),
        conversions: Math.round(conv),
        impressions: impr,
        clicks,
        cpa,
        cvr,
        ctr,
        is_incident: isIncident,
        incident_type: incidentType
      });
    });
  }

  const mappedColumns: ColumnMapping = {
    dateField: 'date',
    campaignField: 'campaign',
    spendField: 'spend',
    conversionsField: 'conversions',
    impressionsField: 'impressions',
    clicksField: 'clicks',
    isIncidentField: 'is_incident',
    incidentTypeField: 'incident_type'
  };

  const metadata: DatasetMetadata = {
    filename: 'sample_campaign_metrics_180d.csv',
    source: 'demo',
    rowCount: records.length,
    campaignCount: campaigns.length,
    minDate: records[0].date,
    maxDate: records[records.length - 1].date,
    uploadedAt: new Date().toLocaleDateString() + ' ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    headers: Object.keys(records[0]),
    mappedColumns
  };

  return { records, metadata };
}

/**
 * Downloads a CSV string as a file in browser.
 */
export function exportToCSV(filename: string, rows: Record<string, any>[]) {
  const csvStr = Papa.unparse(rows);
  const blob = new Blob([csvStr], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
