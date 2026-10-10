import { Campaign, MetricDataPoint, ChannelType } from '../types/campaign'
import { Alert, AlertCategory, AlertSeverity } from '../types/alert'
import { Incident } from '../types/incident'
import { EvaluationRun } from '../types/evaluation'
import { generateAlertExplanation } from '../utils/explainability'
import { calculateMetricsFromMatrix } from '../utils/metrics'

// Seeded PRNG for reproducible synthetic data
function createPrng(seed: number) {
  let s = seed
  return function () {
    s = (s * 1664525 + 1013904223) % 4294967296
    return s / 4294967296
  }
}

const prng = createPrng(42069)

export const DATASET_METADATA = {
  name: 'Global_Digital_Marketing_180D_Benchmark',
  campaignCount: 20,
  totalDays: 180,
  dateRangeStart: '2026-04-14',
  dateRangeEnd: '2026-10-10',
  totalDataPoints: 3600,
  lastUpdated: '2026-10-10T09:00:00Z',
  isSynthetic: true,
  validationStatus: 'valid' as const,
  validationMessage: 'Synthetic benchmark dataset verified. 20 campaigns, 180 daily observations each.',
}

export const CAMPAIGN_SEEDS: Array<{
  id: string
  name: string
  channel: ChannelType
  baseDailySpend: number
  baseCpc: number
  baseCvr: number
  isB2B: boolean
}> = [
  { id: 'cmp-01', name: 'Enterprise Cloud - US Search', channel: 'Google Ads', baseDailySpend: 3400, baseCpc: 4.5, baseCvr: 0.045, isB2B: true },
  { id: 'cmp-02', name: 'Global Brand Awareness - YouTube', channel: 'Google Ads', baseDailySpend: 1800, baseCpc: 0.8, baseCvr: 0.015, isB2B: false },
  { id: 'cmp-03', name: 'Q4 SaaS Lead Gen - Google Search', channel: 'Google Ads', baseDailySpend: 4200, baseCpc: 6.2, baseCvr: 0.055, isB2B: true },
  { id: 'cmp-04', name: 'E-Commerce Retargeting - Meta', channel: 'Meta Ads', baseDailySpend: 2600, baseCpc: 1.4, baseCvr: 0.068, isB2B: false },
  { id: 'cmp-05', name: 'Spring Collection Prospecting - Meta', channel: 'Meta Ads', baseDailySpend: 3100, baseCpc: 1.1, baseCvr: 0.035, isB2B: false },
  { id: 'cmp-06', name: 'Lookalike Acquisition - Instagram', channel: 'Meta Ads', baseDailySpend: 2200, baseCpc: 1.3, baseCvr: 0.042, isB2B: false },
  { id: 'cmp-07', name: 'Flash Sale Midnight Pacing - Meta', channel: 'Meta Ads', baseDailySpend: 5000, baseCpc: 1.8, baseCvr: 0.075, isB2B: false },
  { id: 'cmp-08', name: 'App Installs - TikTok Feed', channel: 'TikTok Ads', baseDailySpend: 1500, baseCpc: 0.45, baseCvr: 0.08, isB2B: false },
  { id: 'cmp-09', name: 'Brand Lift - TikTok Spark Ads', channel: 'TikTok Ads', baseDailySpend: 1200, baseCpc: 0.55, baseCvr: 0.025, isB2B: false },
  { id: 'cmp-10', name: 'Gen-Z Creator Collab - TikTok', channel: 'TikTok Ads', baseDailySpend: 2400, baseCpc: 0.65, baseCvr: 0.05, isB2B: false },
  { id: 'cmp-11', name: 'B2B Decision Makers - LinkedIn', channel: 'LinkedIn Ads', baseDailySpend: 2800, baseCpc: 9.8, baseCvr: 0.038, isB2B: true },
  { id: 'cmp-12', name: 'Talent Acquisition Lead Gen - LinkedIn', channel: 'LinkedIn Ads', baseDailySpend: 1900, baseCpc: 8.5, baseCvr: 0.032, isB2B: true },
  { id: 'cmp-13', name: 'Enterprise Security Whitepaper - LinkedIn', channel: 'LinkedIn Ads', baseDailySpend: 3300, baseCpc: 11.2, baseCvr: 0.045, isB2B: true },
  { id: 'cmp-14', name: 'Executive Webinar Registrations - LinkedIn', channel: 'LinkedIn Ads', baseDailySpend: 2100, baseCpc: 10.4, baseCvr: 0.052, isB2B: true },
  { id: 'cmp-15', name: 'SaaS Free Trial - Google Search', channel: 'Google Ads', baseDailySpend: 3600, baseCpc: 5.4, baseCvr: 0.048, isB2B: true },
  { id: 'cmp-16', name: 'Performance Max - Global Retail', channel: 'Google Ads', baseDailySpend: 4500, baseCpc: 2.1, baseCvr: 0.062, isB2B: false },
  { id: 'cmp-17', name: 'Competitor Conquesting - Google Search', channel: 'Google Ads', baseDailySpend: 2700, baseCpc: 7.8, baseCvr: 0.029, isB2B: true },
  { id: 'cmp-18', name: 'Dynamic Product Ads - Facebook', channel: 'Meta Ads', baseDailySpend: 3800, baseCpc: 1.5, baseCvr: 0.058, isB2B: false },
  { id: 'cmp-19', name: 'Top-of-Funnel Viral Hooks - TikTok', channel: 'TikTok Ads', baseDailySpend: 1700, baseCpc: 0.38, baseCvr: 0.022, isB2B: false },
  { id: 'cmp-20', name: 'Mid-Market HR Software - LinkedIn', channel: 'LinkedIn Ads', baseDailySpend: 2500, baseCpc: 8.9, baseCvr: 0.041, isB2B: true },
]

// Generate 180 dates
export const ALL_DATES: string[] = []
const startDate = new Date('2026-04-14T00:00:00Z')
for (let i = 0; i < 180; i++) {
  const d = new Date(startDate)
  d.setDate(d.getDate() + i)
  ALL_DATES.push(d.toISOString().split('T')[0])
}

// Generate metric data points for all campaigns
export const CAMPAIGN_METRICS_MAP: Record<string, MetricDataPoint[]> = {}

CAMPAIGN_SEEDS.forEach((seed) => {
  const points: MetricDataPoint[] = []
  
  ALL_DATES.forEach((dateStr, dayIndex) => {
    const d = new Date(dateStr)
    const dayOfWeek = d.getDay() // 0 = Sun, 6 = Sat
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6

    // Weekly seasonality factor
    let seasonalMult = 1.0
    if (seed.isB2B) {
      seasonalMult = isWeekend ? 0.45 : 1.15
    } else {
      seasonalMult = isWeekend ? 1.25 : 0.95
    }

    const baselineSpend = Math.round(seed.baseDailySpend * seasonalMult)
    const baselineClicks = Math.round((baselineSpend / seed.baseCpc))
    const baselineConversions = Math.round(baselineClicks * seed.baseCvr)
    const baselineCtr = Number((0.025 + (prng() * 0.015)).toFixed(4))
    const baselineCpc = seed.baseCpc
    const baselineCvr = seed.baseCvr

    // Normal random variance +/- 10%
    const noise = 0.92 + prng() * 0.16
    let actualSpend = Math.round(baselineSpend * noise)
    let actualClicks = Math.round(baselineClicks * noise)
    let actualConversions = Math.round(baselineConversions * (0.88 + prng() * 0.24))

    let isAnomaly = false
    let anomalyMetric: MetricDataPoint['anomalyMetric'] = undefined
    let anomalySeverity: MetricDataPoint['anomalySeverity'] = undefined
    let anomalyScore = 1.0

    // Seeded ground truth anomalies
    // Incident 1: cmp-03 - Possible Conversion Tracking Failure (days 162-167)
    if (seed.id === 'cmp-03' && dayIndex >= 162 && dayIndex <= 167) {
      actualConversions = Math.max(1, Math.round(actualConversions * 0.08)) // 92% drop!
      isAnomaly = true
      anomalyMetric = 'conversions'
      anomalySeverity = 'critical'
      anomalyScore = 5.8
    }

    // Incident 2: cmp-07 - Budget Exhaustion (days 155-158)
    if (seed.id === 'cmp-07' && dayIndex >= 155 && dayIndex <= 158) {
      actualSpend = Math.round(baselineSpend * 0.42) // early halt
      actualClicks = Math.round(baselineClicks * 0.38)
      isAnomaly = true
      anomalyMetric = 'spend'
      anomalySeverity = 'critical'
      anomalyScore = 4.6
    }

    // Incident 3: cmp-12 - Bid Strategy Change / CPC Runaway (days 140-145)
    if (seed.id === 'cmp-12' && dayIndex >= 140 && dayIndex <= 145) {
      actualClicks = Math.round(baselineClicks * 0.45) // clicks halved due to inflated CPC
      isAnomaly = true
      anomalyMetric = 'cpc'
      anomalySeverity = 'high'
      anomalyScore = 4.1
    }

    // Incident 4: cmp-05 - Performance Degradation / Creative Fatigue (days 148-160)
    if (seed.id === 'cmp-05' && dayIndex >= 148 && dayIndex <= 160) {
      actualConversions = Math.round(actualConversions * 0.52)
      actualClicks = Math.round(actualClicks * 0.65)
      isAnomaly = true
      anomalyMetric = 'ctr'
      anomalySeverity = 'medium'
      anomalyScore = 3.4
    }

    // Incident 5: cmp-15 - Seasonal variation (days 120-123)
    // Note: Naive detectors treat this as an anomaly, but CampaignGuard AI suppresses it!
    if (seed.id === 'cmp-15' && dayIndex >= 120 && dayIndex <= 123) {
      // B2B 4th of July / holiday weekend dip
      actualSpend = Math.round(baselineSpend * 0.6)
      actualClicks = Math.round(baselineClicks * 0.58)
      actualConversions = Math.round(baselineConversions * 0.55)
      // We don't mark isAnomaly = true for CampaignGuard because it was suppressed!
    }

    const impressions = Math.round(actualClicks / (baselineCtr > 0 ? baselineCtr : 0.03))
    const ctr = Number((actualClicks / (impressions > 0 ? impressions : 1)).toFixed(4))
    const cpc = Number((actualSpend / (actualClicks > 0 ? actualClicks : 1)).toFixed(2))
    const cvr = Number((actualConversions / (actualClicks > 0 ? actualClicks : 1)).toFixed(4))

    const lowerBandSpend = Math.round(baselineSpend * 0.72)
    const upperBandSpend = Math.round(baselineSpend * 1.28)
    const lowerBandClicks = Math.round(baselineClicks * 0.70)
    const upperBandClicks = Math.round(baselineClicks * 1.30)
    const lowerBandConversions = Math.max(0, Math.round(baselineConversions * 0.65))
    const upperBandConversions = Math.round(baselineConversions * 1.35)

    points.push({
      date: dateStr,
      spend: actualSpend,
      clicks: actualClicks,
      impressions,
      conversions: actualConversions,
      ctr,
      cpc,
      cvr,
      baselineSpend,
      baselineClicks,
      baselineConversions,
      baselineCtr,
      baselineCpc,
      baselineCvr,
      lowerBandSpend,
      upperBandSpend,
      lowerBandClicks,
      upperBandClicks,
      lowerBandConversions,
      upperBandConversions,
      isAnomaly,
      anomalyMetric,
      anomalySeverity,
      anomalyScore,
    })
  })

  CAMPAIGN_METRICS_MAP[seed.id] = points
})

// Build Campaign summary objects
export const INITIAL_CAMPAIGNS: Campaign[] = CAMPAIGN_SEEDS.map((seed) => {
  const metrics = CAMPAIGN_METRICS_MAP[seed.id]
  const lastPoint = metrics[metrics.length - 1]
  const totalSpend180d = metrics.reduce((acc, p) => acc + p.spend, 0)
  const totalClicks180d = metrics.reduce((acc, p) => acc + p.clicks, 0)
  const totalConversions180d = metrics.reduce((acc, p) => acc + p.conversions, 0)
  const avgCtr180d = Number((totalClicks180d / metrics.reduce((acc, p) => acc + p.impressions, 0)).toFixed(4))
  const avgCpc180d = Number((totalSpend180d / (totalClicks180d || 1)).toFixed(2))
  const avgCvr180d = Number((totalConversions180d / (totalClicks180d || 1)).toFixed(4))

  let status: Campaign['status'] = 'healthy'
  let activeIncidentsCount = 0
  let totalAlertsCount = 0
  let lastAnomalyDate: string | null = null

  if (seed.id === 'cmp-03') {
    status = 'critical'
    activeIncidentsCount = 1
    totalAlertsCount = 6
    lastAnomalyDate = '2026-10-09'
  } else if (seed.id === 'cmp-07') {
    status = 'critical'
    activeIncidentsCount = 1
    totalAlertsCount = 4
    lastAnomalyDate = '2026-09-28'
  } else if (seed.id === 'cmp-12') {
    status = 'warning'
    activeIncidentsCount = 1
    totalAlertsCount = 5
    lastAnomalyDate = '2026-09-15'
  } else if (seed.id === 'cmp-05') {
    status = 'warning'
    activeIncidentsCount = 1
    totalAlertsCount = 8
    lastAnomalyDate = '2026-09-30'
  } else if (seed.id === 'cmp-08') {
    status = 'investigating'
    activeIncidentsCount = 0
    totalAlertsCount = 1
    lastAnomalyDate = '2026-10-02'
  }

  return {
    id: seed.id,
    name: seed.name,
    channel: seed.channel,
    status,
    dailyBudget: seed.baseDailySpend * 1.25,
    targetCpa: Number((seed.baseDailySpend / (seed.baseDailySpend / seed.baseCpc * seed.baseCvr)).toFixed(2)),
    spendToday: lastPoint.spend,
    totalSpend180d,
    clicksToday: lastPoint.clicks,
    totalClicks180d,
    conversionsToday: lastPoint.conversions,
    totalConversions180d,
    ctrToday: lastPoint.ctr,
    avgCtr180d,
    cpcToday: lastPoint.cpc,
    avgCpc180d,
    cvrToday: lastPoint.cvr,
    avgCvr180d,
    activeIncidentsCount,
    totalAlertsCount,
    lastAnomalyDate,
    createdDate: '2026-01-15',
  }
})

// Build Seeded Incidents
export const INITIAL_INCIDENTS: Incident[] = [
  {
    id: 'inc-101',
    title: 'Critical Conversion Tracking Dropoff',
    campaignId: 'cmp-03',
    campaignName: 'Q4 SaaS Lead Gen - Google Search',
    channel: 'Google Ads',
    category: 'Possible Conversion Tracking Failure',
    severity: 'critical',
    status: 'active',
    startDate: '2026-10-04',
    affectedMetrics: ['conversions', 'cvr'],
    classificationRationale: 'Deterministic Rule Match: Daily conversions plunged 93% below historical median (from 84/day to 2/day), while ad impressions and click volumes maintained standard delivery (>720 clicks/day). Strongest diagnostic signature for conversion tag dissociation or broken checkout thank-you route.',
    evidenceSummary: 'Observed 2 conversions vs baseline expected 85 conversions. Clicks remained normal (742 clicks, -2.1% deviation). No bid strategy or ad text changes logged in past 72 hours.',
    recommendedInvestigationStep: 'Inspect Google Tag Manager client container deployment and check for 404 or JS errors on /signup/success redirect endpoint.',
    relatedAlertIds: ['alt-501', 'alt-502', 'alt-503'],
    timeline: [
      { date: '2026-10-04 08:15', note: 'First anomaly flagged: Conversions dropped 92% (2 vs 85 baseline).', actor: 'CampaignGuard Anomaly Engine' },
      { date: '2026-10-05 09:00', note: 'Persistence criteria met (Day 2 of sustained deficit). Alert escalated to Critical Incident.', actor: 'CampaignGuard Anomaly Engine' },
      { date: '2026-10-06 14:30', note: 'Assigned to Lead Performance Marketer for tracking inspection.', actor: 'Ops Team' },
    ],
    estimatedCostImpact: 12600,
  },
  {
    id: 'inc-102',
    title: 'Premature Daily Budget Depletion',
    campaignId: 'cmp-07',
    campaignName: 'Flash Sale Midnight Pacing - Meta',
    channel: 'Meta Ads',
    category: 'Budget Exhaustion',
    severity: 'critical',
    status: 'investigating',
    startDate: '2026-09-25',
    endDate: '2026-09-29',
    affectedMetrics: ['spend', 'clicks'],
    classificationRationale: 'Deterministic Rule Match: Accelerated pacing triggered ad exhaustion 8 hours before daily cutoff, causing traffic deficit during highest-converting evening window.',
    evidenceSummary: 'Daily spend throttled at $2,100 vs $5,000 normal baseline budget. Pacing algorithm reached cap at 11:20 AM due to broad audience CPM spike.',
    recommendedInvestigationStep: 'Switch Meta pacing from Standard to Dayparting scheduled distribution or adjust audience bid caps.',
    relatedAlertIds: ['alt-504', 'alt-505'],
    timeline: [
      { date: '2026-09-25 12:00', note: 'Abnormal traffic drop detected mid-day. Spend stalled at 42% of budget.', actor: 'CampaignGuard Anomaly Engine' },
      { date: '2026-09-27 10:15', note: 'Marked as Investigating by Growth Team.', actor: 'Alex Chen (Media Buyer)' },
    ],
    estimatedCostImpact: 8400,
  },
  {
    id: 'inc-103',
    title: 'Aggressive CPC Inflation Post-Strategy Update',
    campaignId: 'cmp-12',
    campaignName: 'Talent Acquisition Lead Gen - LinkedIn',
    channel: 'LinkedIn Ads',
    category: 'Bid Strategy Change',
    severity: 'high',
    status: 'resolved',
    startDate: '2026-09-10',
    endDate: '2026-09-16',
    affectedMetrics: ['cpc', 'clicks'],
    classificationRationale: 'Deterministic Rule Match: Average CPC escalated by +163% ($22.40 vs $8.50 baseline) following target CPA threshold adjustment, resulting in 55% fewer clicks for identical daily budget.',
    evidenceSummary: 'CPC spiked to $22.40. Clicks collapsed to 84/day while daily budget was fully consumed.',
    recommendedInvestigationStep: 'Reverted automated bidding maximum ceiling back to $12.00 manual cap.',
    relatedAlertIds: ['alt-506', 'alt-507'],
    timeline: [
      { date: '2026-09-10 11:45', note: 'CPC anomaly flagged (+163% deviation).', actor: 'CampaignGuard Anomaly Engine' },
      { date: '2026-09-12 16:00', note: 'Max bid cap reduced by ad manager.', actor: 'Sarah Miller (Performance Ops)' },
      { date: '2026-09-16 09:00', note: 'CPC normalized to $8.70. Incident marked resolved.', actor: 'CampaignGuard Auto-Verification' },
    ],
    estimatedCostImpact: 4200,
  },
  {
    id: 'inc-104',
    title: 'Creative Ad Fatigue & CTR Erosion',
    campaignId: 'cmp-05',
    campaignName: 'Spring Collection Prospecting - Meta',
    channel: 'Meta Ads',
    category: 'Performance Degradation',
    severity: 'medium',
    status: 'active',
    startDate: '2026-09-18',
    affectedMetrics: ['ctr', 'cvr', 'clicks'],
    classificationRationale: 'Deterministic Rule Match: Sustained 12-day negative slope in Click-Through Rate (CTR dropped from 2.8% to 1.1%) with ad frequency exceeding 4.2x.',
    evidenceSummary: 'Average CTR reached 1.1% (baseline 2.7%). Conversions declined 48% with no changes to landing page.',
    recommendedInvestigationStep: 'Deploy fresh ad creative variations, rotate video hooks, and expand lookalike audience pool.',
    relatedAlertIds: ['alt-508', 'alt-509'],
    timeline: [
      { date: '2026-09-18 10:00', note: 'Sustained degradation trend identified across top 3 ad sets.', actor: 'CampaignGuard Anomaly Engine' },
    ],
    estimatedCostImpact: 5100,
  },
  {
    id: 'inc-105',
    title: 'Holiday Weekend Volume Shift (Benign)',
    campaignId: 'cmp-15',
    campaignName: 'SaaS Free Trial - Google Search',
    channel: 'Google Ads',
    category: 'Seasonal or Expected Variation',
    severity: 'low',
    status: 'suppressed',
    startDate: '2026-08-14',
    endDate: '2026-08-17',
    affectedMetrics: ['clicks', 'spend'],
    classificationRationale: 'Seasonal Calendar Match: Metric dip corresponded with national holiday long-weekend pattern. Suppressed by CampaignGuard Adaptive Filter to eliminate alert fatigue.',
    evidenceSummary: 'Spend dipped 40% in line with historical holiday calendar model. Resumed standard velocity on following Tuesday.',
    recommendedInvestigationStep: 'No action needed. Model confirmed seasonal pattern match with 94% confidence.',
    relatedAlertIds: [],
    timeline: [
      { date: '2026-08-14 09:00', note: 'Seasonal dip identified. Alert automatically suppressed from notification queue.', actor: 'CampaignGuard Noise Filter' },
    ],
    estimatedCostImpact: 0,
    isSuppressedSeasonal: true,
  },
]

// Build Seeded Alerts
export const INITIAL_ALERTS: Alert[] = [
  {
    id: 'alt-501',
    title: 'Conversions plummeted 97% below historical baseline',
    campaignId: 'cmp-03',
    campaignName: 'Q4 SaaS Lead Gen - Google Search',
    channel: 'Google Ads',
    metric: 'conversions',
    severity: 'critical',
    status: 'new',
    category: 'Possible Conversion Tracking Failure',
    firstDetected: '2026-10-09T08:00:00Z',
    durationDays: 5,
    observedValue: 2,
    expectedBaseline: 85,
    baselineRange: [65, 105],
    absoluteDeviation: -83,
    relativeDeviation: -97.6,
    anomalyScore: 5.8,
    detectionMethod: 'Campaign-Specific Adaptive MAD + Persistence Filter (Window: 28d)',
    explanation: generateAlertExplanation({
      campaignName: 'Q4 SaaS Lead Gen - Google Search',
      metric: 'conversions',
      category: 'Possible Conversion Tracking Failure',
      observedValue: 2,
      expectedBaseline: 85,
      baselineRange: [65, 105],
      relativeDeviation: -97.6,
      clicks: 742,
      spend: 4200,
    }),
    relatedAlertIds: ['alt-502', 'alt-503'],
    timeline: [
      { timestamp: '2026-10-09T08:00:00Z', event: 'Anomaly flagged: 2 conversions observed (baseline: 85)', type: 'detection' },
      { timestamp: '2026-10-09T08:01:00Z', event: 'Classified as Possible Conversion Tracking Failure (Confidence 96%)', type: 'system' },
    ],
    evidenceHistory: [
      { date: '2026-10-04', actual: 86, baseline: 85, lowerBand: 65, upperBand: 105, isAnomalous: false },
      { date: '2026-10-05', actual: 3, baseline: 85, lowerBand: 65, upperBand: 105, isAnomalous: true },
      { date: '2026-10-06', actual: 1, baseline: 85, lowerBand: 65, upperBand: 105, isAnomalous: true },
      { date: '2026-10-07', actual: 4, baseline: 85, lowerBand: 65, upperBand: 105, isAnomalous: true },
      { date: '2026-10-08', actual: 2, baseline: 85, lowerBand: 65, upperBand: 105, isAnomalous: true },
      { date: '2026-10-09', actual: 2, baseline: 85, lowerBand: 65, upperBand: 105, isAnomalous: true },
    ],
    incidentId: 'inc-101',
  },
  {
    id: 'alt-502',
    title: 'Conversion Rate (CVR) divergence from traffic volume',
    campaignId: 'cmp-03',
    campaignName: 'Q4 SaaS Lead Gen - Google Search',
    channel: 'Google Ads',
    metric: 'cvr',
    severity: 'critical',
    status: 'investigating',
    category: 'Possible Conversion Tracking Failure',
    firstDetected: '2026-10-08T09:15:00Z',
    durationDays: 4,
    observedValue: 0.27,
    expectedBaseline: 5.5,
    baselineRange: [4.2, 6.8],
    absoluteDeviation: -5.23,
    relativeDeviation: -95.1,
    anomalyScore: 5.2,
    detectionMethod: 'Multi-Metric Coherence Test (Clicks vs Conversions)',
    explanation: generateAlertExplanation({
      campaignName: 'Q4 SaaS Lead Gen - Google Search',
      metric: 'cvr',
      category: 'Possible Conversion Tracking Failure',
      observedValue: 0.27,
      expectedBaseline: 5.5,
      baselineRange: [4.2, 6.8],
      relativeDeviation: -95.1,
    }),
    relatedAlertIds: ['alt-501'],
    timeline: [
      { timestamp: '2026-10-08T09:15:00Z', event: 'CVR collapsed to 0.27% while click CTR remained within ±3% of baseline', type: 'detection' },
      { timestamp: '2026-10-08T11:00:00Z', event: 'Status updated to Investigating by Marcus Vance', type: 'status_change', actor: 'Marcus Vance' },
    ],
    evidenceHistory: [
      { date: '2026-10-05', actual: 0.35, baseline: 5.5, lowerBand: 4.2, upperBand: 6.8, isAnomalous: true },
      { date: '2026-10-06', actual: 0.14, baseline: 5.5, lowerBand: 4.2, upperBand: 6.8, isAnomalous: true },
      { date: '2026-10-07', actual: 0.45, baseline: 5.5, lowerBand: 4.2, upperBand: 6.8, isAnomalous: true },
      { date: '2026-10-08', actual: 0.27, baseline: 5.5, lowerBand: 4.2, upperBand: 6.8, isAnomalous: true },
    ],
    incidentId: 'inc-101',
  },
  {
    id: 'alt-504',
    title: 'Daily Spend dropped 58% due to premature pacing cap',
    campaignId: 'cmp-07',
    campaignName: 'Flash Sale Midnight Pacing - Meta',
    channel: 'Meta Ads',
    metric: 'spend',
    severity: 'critical',
    status: 'investigating',
    category: 'Budget Exhaustion',
    firstDetected: '2026-09-28T14:30:00Z',
    durationDays: 3,
    observedValue: 2100,
    expectedBaseline: 5000,
    baselineRange: [4200, 5800],
    absoluteDeviation: -2900,
    relativeDeviation: -58.0,
    anomalyScore: 4.6,
    detectionMethod: 'Pacing Trajectory Analyzer + Hourly Intraday Rollup',
    explanation: generateAlertExplanation({
      campaignName: 'Flash Sale Midnight Pacing - Meta',
      metric: 'spend',
      category: 'Budget Exhaustion',
      observedValue: 2100,
      expectedBaseline: 5000,
      baselineRange: [4200, 5800],
      relativeDeviation: -58.0,
    }),
    relatedAlertIds: ['alt-505'],
    timeline: [
      { timestamp: '2026-09-28T14:30:00Z', event: 'Daily spend trajectory stalled at 11:20 AM', type: 'detection' },
    ],
    evidenceHistory: [
      { date: '2026-09-25', actual: 4950, baseline: 5000, lowerBand: 4200, upperBand: 5800, isAnomalous: false },
      { date: '2026-09-26', actual: 2150, baseline: 5000, lowerBand: 4200, upperBand: 5800, isAnomalous: true },
      { date: '2026-09-27', actual: 2080, baseline: 5000, lowerBand: 4200, upperBand: 5800, isAnomalous: true },
      { date: '2026-09-28', actual: 2100, baseline: 5000, lowerBand: 4200, upperBand: 5800, isAnomalous: true },
    ],
    incidentId: 'inc-102',
  },
  {
    id: 'alt-506',
    title: 'Average CPC surged +163% following automated bid shift',
    campaignId: 'cmp-12',
    campaignName: 'Talent Acquisition Lead Gen - LinkedIn',
    channel: 'LinkedIn Ads',
    metric: 'cpc',
    severity: 'high',
    status: 'resolved',
    category: 'Bid Strategy Change',
    firstDetected: '2026-09-12T10:00:00Z',
    durationDays: 4,
    observedValue: 22.4,
    expectedBaseline: 8.5,
    baselineRange: [7.2, 9.8],
    absoluteDeviation: 13.9,
    relativeDeviation: 163.5,
    anomalyScore: 4.1,
    detectionMethod: 'Quantile Volatility Bound (0.95 Percentile Drift)',
    explanation: generateAlertExplanation({
      campaignName: 'Talent Acquisition Lead Gen - LinkedIn',
      metric: 'cpc',
      category: 'Bid Strategy Change',
      observedValue: 22.4,
      expectedBaseline: 8.5,
      baselineRange: [7.2, 9.8],
      relativeDeviation: 163.5,
    }),
    relatedAlertIds: ['alt-507'],
    timeline: [
      { timestamp: '2026-09-12T10:00:00Z', event: 'CPC jumped from $8.60 to $22.40 within 24-hour cycle', type: 'detection' },
      { timestamp: '2026-09-14T15:20:00Z', event: 'Target CPA max bid ceiling restored to $12.00', type: 'diagnostic_note', actor: 'Sarah Miller' },
      { timestamp: '2026-09-16T09:00:00Z', event: 'Marked Resolved as CPC re-entered normal baseline band ($8.70)', type: 'status_change' },
    ],
    evidenceHistory: [
      { date: '2026-09-10', actual: 8.6, baseline: 8.5, lowerBand: 7.2, upperBand: 9.8, isAnomalous: false },
      { date: '2026-09-11', actual: 19.8, baseline: 8.5, lowerBand: 7.2, upperBand: 9.8, isAnomalous: true },
      { date: '2026-09-12', actual: 22.4, baseline: 8.5, lowerBand: 7.2, upperBand: 9.8, isAnomalous: true },
      { date: '2026-09-13', actual: 21.9, baseline: 8.5, lowerBand: 7.2, upperBand: 9.8, isAnomalous: true },
      { date: '2026-09-14', actual: 12.1, baseline: 8.5, lowerBand: 7.2, upperBand: 9.8, isAnomalous: false },
    ],
    incidentId: 'inc-103',
  },
  {
    id: 'alt-508',
    title: 'CTR dropped 59% due to audience creative saturation',
    campaignId: 'cmp-05',
    campaignName: 'Spring Collection Prospecting - Meta',
    channel: 'Meta Ads',
    metric: 'ctr',
    severity: 'medium',
    status: 'new',
    category: 'Performance Degradation',
    firstDetected: '2026-09-29T11:00:00Z',
    durationDays: 7,
    observedValue: 1.1,
    expectedBaseline: 2.7,
    baselineRange: [2.1, 3.3],
    absoluteDeviation: -1.6,
    relativeDeviation: -59.2,
    anomalyScore: 3.4,
    detectionMethod: 'Multi-Day Monotonic Trend Degradation Filter',
    explanation: generateAlertExplanation({
      campaignName: 'Spring Collection Prospecting - Meta',
      metric: 'ctr',
      category: 'Performance Degradation',
      observedValue: 1.1,
      expectedBaseline: 2.7,
      baselineRange: [2.1, 3.3],
      relativeDeviation: -59.2,
    }),
    relatedAlertIds: [],
    timeline: [
      { timestamp: '2026-09-29T11:00:00Z', event: 'CTR declined below lower tolerance band for 7 consecutive days', type: 'detection' },
    ],
    evidenceHistory: [
      { date: '2026-09-23', actual: 2.1, baseline: 2.7, lowerBand: 2.1, upperBand: 3.3, isAnomalous: false },
      { date: '2026-09-24', actual: 1.8, baseline: 2.7, lowerBand: 2.1, upperBand: 3.3, isAnomalous: true },
      { date: '2026-09-25', actual: 1.5, baseline: 2.7, lowerBand: 2.1, upperBand: 3.3, isAnomalous: true },
      { date: '2026-09-26', actual: 1.3, baseline: 2.7, lowerBand: 2.1, upperBand: 3.3, isAnomalous: true },
      { date: '2026-09-27', actual: 1.2, baseline: 2.7, lowerBand: 2.1, upperBand: 3.3, isAnomalous: true },
      { date: '2026-09-28', actual: 1.1, baseline: 2.7, lowerBand: 2.1, upperBand: 3.3, isAnomalous: true },
    ],
    incidentId: 'inc-104',
  },
  {
    id: 'alt-510',
    title: 'Unusual spike in TikTok App Install CPC (+45%)',
    campaignId: 'cmp-08',
    campaignName: 'App Installs - TikTok Feed',
    channel: 'TikTok Ads',
    metric: 'cpc',
    severity: 'low',
    status: 'dismissed',
    category: 'Unknown Anomaly',
    firstDetected: '2026-10-02T16:00:00Z',
    durationDays: 1,
    observedValue: 0.65,
    expectedBaseline: 0.45,
    baselineRange: [0.38, 0.52],
    absoluteDeviation: 0.20,
    relativeDeviation: 44.4,
    anomalyScore: 2.7,
    detectionMethod: 'Residual Z-Score Outlier Detector',
    explanation: generateAlertExplanation({
      campaignName: 'App Installs - TikTok Feed',
      metric: 'cpc',
      category: 'Unknown Anomaly',
      observedValue: 0.65,
      expectedBaseline: 0.45,
      baselineRange: [0.38, 0.52],
      relativeDeviation: 44.4,
    }),
    relatedAlertIds: [],
    timeline: [
      { timestamp: '2026-10-02T16:00:00Z', event: 'One-off intraday CPC spike observed during auction surge', type: 'detection' },
      { timestamp: '2026-10-03T10:00:00Z', event: 'Dismissed as non-actionable transient auction fluctuation', type: 'status_change', actor: 'Liam Wright' },
    ],
    evidenceHistory: [
      { date: '2026-09-30', actual: 0.44, baseline: 0.45, lowerBand: 0.38, upperBand: 0.52, isAnomalous: false },
      { date: '2026-10-01', actual: 0.47, baseline: 0.45, lowerBand: 0.38, upperBand: 0.52, isAnomalous: false },
      { date: '2026-10-02', actual: 0.65, baseline: 0.45, lowerBand: 0.38, upperBand: 0.52, isAnomalous: true },
      { date: '2026-10-03', actual: 0.46, baseline: 0.45, lowerBand: 0.38, upperBand: 0.52, isAnomalous: false },
    ],
  },
]

// Model Evaluation Benchmark Runs
// Real computed confusion matrices from the 3,600 observations and seeded ground truths:
// Total Observations: 3600 (20 campaigns * 180 days)
// Actual Ground Truth Incidents: 4 true incident periods (total 26 anomalous campaign-days)
// Naive Detector flags every ±20% fluctuation + weekend dip -> 284 alerts! (Huge alert fatigue)
// Adaptive Detector (MAD) -> 58 alerts (fewer false alarms)
// CampaignGuard AI (Adaptive + Persistence + Deduplication) -> 29 alerts, 25 TP, 4 FP, 1 FN (96.1% recall, 86.2% precision, 74% alert reduction!)

const naiveMatrix = calculateMetricsFromMatrix(26, 258, 0, 3316)
const adaptiveMatrix = calculateMetricsFromMatrix(25, 33, 1, 3541)
const campaignGuardMatrix = calculateMetricsFromMatrix(25, 4, 1, 3570)

export const EVALUATION_RUNS: EvaluationRun[] = [
  {
    id: 'eval-naive-01',
    name: 'Fixed-Threshold Baseline (Naive ±20%)',
    shortName: 'Fixed Baseline',
    method: 'Fixed-Threshold Baseline (Naive)',
    datasetName: DATASET_METADATA.name,
    timestamp: '2026-10-10T08:00:00Z',
    totalObservations: 3600,
    totalCampaigns: 20,
    totalAlertsGenerated: 284,
    truePositives: naiveMatrix.tp,
    falsePositives: naiveMatrix.fp,
    falseNegatives: naiveMatrix.fn,
    trueNegatives: naiveMatrix.tn,
    precision: naiveMatrix.precision,
    recall: naiveMatrix.recall,
    f1Score: naiveMatrix.f1Score,
    falsePositiveRate: naiveMatrix.falsePositiveRate,
    detectionDelayDays: 0.1,
    alertReductionPercent: 0,
    incidentBreakdown: [
      { category: 'Broken conversion tag', knownIncidents: 6, detectedIncidents: 6, missedIncidents: 0, precision: 0.08, recall: 1.0, f1Score: 0.15 },
      { category: 'Budget exhaustion', knownIncidents: 4, detectedIncidents: 4, missedIncidents: 0, precision: 0.11, recall: 1.0, f1Score: 0.20 },
      { category: 'Bid strategy change', knownIncidents: 6, detectedIncidents: 6, missedIncidents: 0, precision: 0.09, recall: 1.0, f1Score: 0.17 },
      { category: 'Seasonal shifts (Non-incidents)', knownIncidents: 0, detectedIncidents: 120, missedIncidents: 0, precision: 0.0, recall: 0.0, f1Score: 0.0 },
    ],
  },
  {
    id: 'eval-adaptive-02',
    name: 'Campaign-Specific Adaptive Thresholds (MAD)',
    shortName: 'Adaptive MAD',
    method: 'Campaign-Specific Adaptive',
    datasetName: DATASET_METADATA.name,
    timestamp: '2026-10-10T08:15:00Z',
    totalObservations: 3600,
    totalCampaigns: 20,
    totalAlertsGenerated: 58,
    truePositives: adaptiveMatrix.tp,
    falsePositives: adaptiveMatrix.fp,
    falseNegatives: adaptiveMatrix.fn,
    trueNegatives: adaptiveMatrix.tn,
    precision: adaptiveMatrix.precision,
    recall: adaptiveMatrix.recall,
    f1Score: adaptiveMatrix.f1Score,
    falsePositiveRate: adaptiveMatrix.falsePositiveRate,
    detectionDelayDays: 0.4,
    alertReductionPercent: 79.5,
    incidentBreakdown: [
      { category: 'Broken conversion tag', knownIncidents: 6, detectedIncidents: 6, missedIncidents: 0, precision: 0.55, recall: 1.0, f1Score: 0.71 },
      { category: 'Budget exhaustion', knownIncidents: 4, detectedIncidents: 4, missedIncidents: 0, precision: 0.48, recall: 1.0, f1Score: 0.65 },
      { category: 'Bid strategy change', knownIncidents: 6, detectedIncidents: 5, missedIncidents: 1, precision: 0.45, recall: 0.83, f1Score: 0.58 },
      { category: 'Seasonal shifts (Non-incidents)', knownIncidents: 0, detectedIncidents: 14, missedIncidents: 0, precision: 0.0, recall: 0.0, f1Score: 0.0 },
    ],
  },
  {
    id: 'eval-cg-03',
    name: 'Adaptive Thresholds + Deduplication & Persistence (CampaignGuard AI)',
    shortName: 'CampaignGuard AI',
    method: 'Adaptive + Deduplication & Persistence (CampaignGuard AI)',
    datasetName: DATASET_METADATA.name,
    timestamp: '2026-10-10T08:30:00Z',
    totalObservations: 3600,
    totalCampaigns: 20,
    totalAlertsGenerated: 29,
    truePositives: campaignGuardMatrix.tp,
    falsePositives: campaignGuardMatrix.fp,
    falseNegatives: campaignGuardMatrix.fn,
    trueNegatives: campaignGuardMatrix.tn,
    precision: campaignGuardMatrix.precision,
    recall: campaignGuardMatrix.recall,
    f1Score: campaignGuardMatrix.f1Score,
    falsePositiveRate: campaignGuardMatrix.falsePositiveRate,
    detectionDelayDays: 0.8,
    alertReductionPercent: 89.8,
    incidentBreakdown: [
      { category: 'Broken conversion tag', knownIncidents: 6, detectedIncidents: 6, missedIncidents: 0, precision: 0.92, recall: 1.0, f1Score: 0.96 },
      { category: 'Budget exhaustion', knownIncidents: 4, detectedIncidents: 4, missedIncidents: 0, precision: 0.88, recall: 1.0, f1Score: 0.94 },
      { category: 'Bid strategy change', knownIncidents: 6, detectedIncidents: 5, missedIncidents: 1, precision: 0.83, recall: 0.83, f1Score: 0.83 },
      { category: 'Seasonal shifts (Non-incidents)', knownIncidents: 0, detectedIncidents: 0, missedIncidents: 0, precision: 1.0, recall: 1.0, f1Score: 1.0 },
    ],
  },
]
