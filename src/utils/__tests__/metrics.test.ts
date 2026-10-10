import { describe, it, expect } from 'vitest'
import {
  calculatePrecision,
  calculateRecall,
  calculateF1Score,
  calculateFPR,
  calculateMetricsFromMatrix,
  safeDivide,
} from '../metrics'
import { generateAlertExplanation } from '../explainability'
import { formatCurrency, formatDeviation, formatPercent } from '../formatters'

describe('Evaluation Metrics Utilities', () => {
  it('safeDivide handles division by zero and NaN safely', () => {
    expect(safeDivide(10, 0)).toBe(0)
    expect(safeDivide(10, 0, 99)).toBe(99)
    expect(safeDivide(NaN, 5)).toBe(0)
    expect(safeDivide(10, 2)).toBe(5)
  })

  it('calculatePrecision calculates TP / (TP + FP)', () => {
    expect(calculatePrecision(25, 4)).toBeCloseTo(0.862, 3)
    expect(calculatePrecision(0, 0)).toBe(0)
    expect(calculatePrecision(10, 0)).toBe(1.0)
  })

  it('calculateRecall calculates TP / (TP + FN)', () => {
    expect(calculateRecall(25, 1)).toBeCloseTo(0.9615, 3)
    expect(calculateRecall(0, 0)).toBe(0)
    expect(calculateRecall(10, 0)).toBe(1.0)
  })

  it('calculateF1Score calculates harmonic mean of precision and recall', () => {
    const precision = calculatePrecision(25, 4)
    const recall = calculateRecall(25, 1)
    const f1 = calculateF1Score(precision, recall)
    expect(f1).toBeGreaterThan(0.9)
    expect(calculateF1Score(0, 0)).toBe(0)
  })

  it('calculateFPR calculates FP / (FP + TN)', () => {
    expect(calculateFPR(4, 3570)).toBeCloseTo(0.0011, 4)
    expect(calculateFPR(0, 0)).toBe(0)
  })

  it('calculateMetricsFromMatrix computes full confusion metrics correctly', () => {
    const res = calculateMetricsFromMatrix(25, 4, 1, 3570)
    expect(res.tp).toBe(25)
    expect(res.fp).toBe(4)
    expect(res.fn).toBe(1)
    expect(res.tn).toBe(3570)
    expect(res.total).toBe(3600)
    expect(res.precision).toBeCloseTo(0.862, 3)
    expect(res.recall).toBeCloseTo(0.9615, 3)
  })
})

describe('Explainability Engine', () => {
  it('generates explainable diagnostic for conversion tracking failure', () => {
    const explanation = generateAlertExplanation({
      campaignName: 'Q4 SaaS Lead Gen',
      metric: 'conversions',
      category: 'Possible Conversion Tracking Failure',
      observedValue: 2,
      expectedBaseline: 85,
      baselineRange: [65, 105],
      relativeDeviation: -97.6,
      clicks: 742,
    })

    expect(explanation.whatChanged).toContain('Conversions plummeted sharply')
    expect(explanation.whatObserved).toContain('2')
    expect(explanation.whyFlagged).toContain('Disproportionate divergence between clicks and conversions')
    expect(explanation.recommendedFirstStep).toContain('Google Tag Manager')
    expect(explanation.confidence).toBeGreaterThan(0.9)
  })

  it('generates explainable diagnostic for budget exhaustion', () => {
    const explanation = generateAlertExplanation({
      campaignName: 'Flash Sale Meta',
      metric: 'spend',
      category: 'Budget Exhaustion',
      observedValue: 2100,
      expectedBaseline: 5000,
      baselineRange: [4200, 5800],
      relativeDeviation: -58.0,
    })

    expect(explanation.whatChanged).toContain('Daily spend capped out')
    expect(explanation.recommendedFirstStep).toContain('pacing')
  })
})

describe('Formatting Utilities', () => {
  it('formats currencies, deviations, and percentages accurately', () => {
    expect(formatCurrency(1250)).toBe('$1,250')
    expect(formatDeviation(-45.2)).toBe('-45.2%')
    expect(formatDeviation(12.5)).toBe('+12.5%')
    expect(formatPercent(0.862)).toBe('86.2%')
  })
})

describe('PS-04 Dataset Semantics & Reproducibility Audit', () => {
  it('verifies the complete 180-day dataset is processed across 20 campaigns', async () => {
    const { DATASET_METADATA, OFFICIAL_180D_SUMMARY, CAMPAIGNS } = await import(
      '../../data/challengeDataset'
    )
    expect(DATASET_METADATA.campaignCount).toBe(20)
    expect(DATASET_METADATA.totalDays).toBe(180)
    expect(DATASET_METADATA.totalDataPoints).toBe(3600)
    expect(DATASET_METADATA.dateRangeStart).toBe('2026-03-01')
    expect(DATASET_METADATA.dateRangeEnd).toBe('2026-08-27')
    expect(CAMPAIGNS.length).toBe(20)
    expect(OFFICIAL_180D_SUMMARY.totalObservations).toBe(3600)
  })

  it('guarantees alert count consistency between ALERTS, summary, and reports', async () => {
    const { ALERTS, OFFICIAL_180D_SUMMARY, INCIDENTS } = await import(
      '../../data/challengeDataset'
    )
    expect(ALERTS.length).toBe(174)
    expect(OFFICIAL_180D_SUMMARY.totalAlertEvents).toBe(174)
    expect(OFFICIAL_180D_SUMMARY.uniqueCampaignsWithAlerts).toBe(17)
    expect(OFFICIAL_180D_SUMMARY.distinctGroupedIncidents).toBe(110)
    expect(INCIDENTS.length).toBe(110)
    expect(OFFICIAL_180D_SUMMARY.rawAnomalousObservations).toBe(319)
  })

  it('verifies B2B revenue zero-by-design rule prevents false alarms', async () => {
    const { CAMPAIGNS, ALERTS } = await import('../../data/challengeDataset')
    const b2bCampaigns = CAMPAIGNS.filter((c) => c.vertical === 'b2b')
    expect(b2bCampaigns.length).toBe(4) // C13, C14, C15, C16
    // B2B campaigns must NEVER trigger revenue alerts because revenue is $0 by design
    const b2bRevenueAlerts = ALERTS.filter(
      (a) => a.metric === 'revenue' && b2bCampaigns.some((b) => b.id === a.campaignId)
    )
    expect(b2bRevenueAlerts.length).toBe(0)
  })

  it('verifies low-volume Poisson safeguard suppresses small integer fluctuations', async () => {
    const { ALERTS } = await import('../../data/challengeDataset')
    // No alert should be generated when baseline conversions < 4 and absolute delta <= 2
    const invalidLowVolAlerts = ALERTS.filter(
      (a) => a.metric === 'conversions' && a.expectedBaseline < 4 && Math.abs(a.absoluteDeviation) <= 2
    )
    expect(invalidLowVolAlerts.length).toBe(0)
  })

  it('verifies historical baselines do not leak future observations', async () => {
    const { CAMPAIGN_METRICS_MAP } = await import('../../data/challengeDataset')
    // First 14 days of any campaign must not have anomalous alerts because baseline window is 14 days
    const c07Points = CAMPAIGN_METRICS_MAP['C07']
    expect(c07Points).toBeDefined()
    expect(c07Points.length).toBe(180)
    for (let i = 0; i < 14; i++) {
      expect(c07Points[i].isAnomaly).toBe(false)
    }
  })

  it('verifies campaign-specific adaptive MAD bands differ across campaigns', async () => {
    const { CAMPAIGN_METRICS_MAP } = await import('../../data/challengeDataset')
    const c01Day50 = CAMPAIGN_METRICS_MAP['C01'][50]
    const c07Day50 = CAMPAIGN_METRICS_MAP['C07'][50]
    // Baseline and bands must be campaign-specific
    expect(c01Day50.baselineClicks).not.toBe(c07Day50.baselineClicks)
    expect(c01Day50.upperBandClicks).not.toBe(c07Day50.upperBandClicks)
  })

  it('verifies verified candidate incidents and missed incident reporting', async () => {
    const { VERIFIED_CANDIDATE_INCIDENTS, MISSED_INCIDENTS_AUDIT } = await import(
      '../../services/evaluationService'
    )
    expect(VERIFIED_CANDIDATE_INCIDENTS.length).toBe(5)
    expect(VERIFIED_CANDIDATE_INCIDENTS.every((i) => i.detectedByAdaptive)).toBe(true)
    expect(MISSED_INCIDENTS_AUDIT.length).toBeGreaterThanOrEqual(3)
    expect(MISSED_INCIDENTS_AUDIT.every((m) => m.whyMissedOrFiltered && m.potentialImprovement)).toBe(
      true
    )
  })
})

