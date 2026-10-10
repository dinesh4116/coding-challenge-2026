import {
  CampaignMetricRecord,
  AnomalyAlert,
  DetectionConfig,
  IncidentCategory,
  ModelMetrics,
  Severity
} from '../types/dashboard';

/**
 * Computes mean and standard deviation for an array of numbers.
 */
function getStats(values: number[]): { mean: number; stdDev: number; median: number; mad: number } {
  if (values.length === 0) return { mean: 0, stdDev: 0, median: 0, mad: 0 };
  const sum = values.reduce((a, b) => a + b, 0);
  const mean = sum / values.length;

  const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / Math.max(1, values.length - 1);
  const stdDev = Math.sqrt(variance);

  // Median and MAD for robust statistics
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const median = sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;

  const absoluteDeviations = sorted.map(v => Math.abs(v - median)).sort((a, b) => a - b);
  const mad = sorted.length % 2 !== 0 ? absoluteDeviations[mid] : (absoluteDeviations[mid - 1] + absoluteDeviations[mid]) / 2;

  return { mean, stdDev, median, mad };
}

/**
 * Modular Anomaly Detection Engine.
 * Analyzes multi-metric time series per campaign using rolling historical baselines.
 */
export function detectAnomalies(
  records: CampaignMetricRecord[],
  config: DetectionConfig
): { alerts: AnomalyAlert[]; metrics: ModelMetrics } {
  const alerts: AnomalyAlert[] = [];

  // Group records by campaign
  const recordsByCampaign: Record<string, CampaignMetricRecord[]> = {};
  records.forEach(rec => {
    if (!recordsByCampaign[rec.campaign]) {
      recordsByCampaign[rec.campaign] = [];
    }
    recordsByCampaign[rec.campaign].push(rec);
  });

  // Cooldown tracker per campaign: campaign -> lastAlertDate
  const lastAlertDateMap: Record<string, string> = {};

  Object.entries(recordsByCampaign).forEach(([campaign, cmpRecords]) => {
    // Ensure chronological order
    const sorted = [...cmpRecords].sort((a, b) => a.date.localeCompare(b.date));

    // Rolling window detection
    for (let i = config.baselineWindow; i < sorted.length; i++) {
      const current = sorted[i];
      const baselineWindowRecords = sorted.slice(i - config.baselineWindow, i);

      // Extract baseline metrics
      const spendBaseline = getStats(baselineWindowRecords.map(r => r.spend));
      const convBaseline = getStats(baselineWindowRecords.map(r => r.conversions));
      const cpaBaseline = getStats(baselineWindowRecords.filter(r => r.conversions > 0).map(r => r.cpa));

      // Calculate z-scores or percentage deviations
      const expectedSpend = Math.max(1, spendBaseline.mean);
      const expectedConv = Math.max(0.1, convBaseline.mean);
      const expectedCpa = cpaBaseline.mean > 0 ? cpaBaseline.mean : (expectedSpend / expectedConv);

      const spendDevPct = ((current.spend - expectedSpend) / expectedSpend) * 100;
      const convDevPct = ((current.conversions - expectedConv) / expectedConv) * 100;
      const cpaDevPct = expectedCpa > 0 ? ((current.cpa - expectedCpa) / expectedCpa) * 100 : 0;

      // Z-scores
      const convZScore = convBaseline.stdDev > 0 ? Math.abs((current.conversions - convBaseline.mean) / convBaseline.stdDev) : 0;
      const spendZScore = spendBaseline.stdDev > 0 ? Math.abs((current.spend - spendBaseline.mean) / spendBaseline.stdDev) : 0;

      // Check alert fatigue cooldown
      const lastAlert = lastAlertDateMap[campaign];
      if (config.suppressConsecutiveAlerts && lastAlert) {
        const daysDiff = (new Date(current.date).getTime() - new Date(lastAlert).getTime()) / (1000 * 3600 * 24);
        if (daysDiff < config.cooldownPeriodDays) {
          continue; // Suppress duplicate sustained alert to reduce fatigue
        }
      }

      let detectedCategory: IncidentCategory | null = null;
      let targetMetric: 'Conversions' | 'Spend' | 'CPA' | 'CVR' = 'Conversions';
      let observedVal = current.conversions;
      let expectedVal = expectedConv;
      let percentChange = convDevPct;
      let severity: Severity = 'medium';
      let anomalyScore = 0;
      let explanation = '';
      let diagnosticSteps: string[] = [];

      // -------------------------------------------------------------
      // Incident Classification Rules (Multi-Metric Signal Correlation)
      // -------------------------------------------------------------

      // 1. BROKEN CONVERSION TAG (Tracking Failure)
      // Spend is active, but conversions drop dramatically (>= 75% drop)
      if (
        current.spend >= config.minSpendThreshold &&
        expectedConv >= 5 &&
        current.conversions <= expectedConv * 0.25
      ) {
        detectedCategory = 'tracking_failure';
        targetMetric = 'Conversions';
        observedVal = current.conversions;
        expectedVal = expectedConv;
        percentChange = convDevPct;
        severity = current.conversions === 0 ? 'critical' : 'high';
        anomalyScore = Math.min(100, Math.round(75 + convZScore * 8));

        explanation = `Conversions dropped by ${Math.abs(Math.round(convDevPct))}% (${current.conversions} obs vs ${Math.round(expectedConv)} expected) while spend remained active (₹${current.spend.toFixed(2)}), strongly indicating a potential tracking tag or analytics signal failure.`;

        diagnosticSteps = [
          'Verify Google Tag Manager / GA4 conversion tag triggers and firing status.',
          'Check target website landing page URL status (HTTP 200 OK vs 404/500 errors).',
          'Inspect recent code deployments or CMP cookie consent banner updates.',
          'Test a test transaction/lead submission in browser DevTools Network tab.'
        ];
      }
      // 2. BUDGET EXHAUSTION
      // Historical spend was active (> ₹100/day), but current spend drops to ~0
      else if (
        expectedSpend >= 100 &&
        current.spend <= expectedSpend * 0.15 &&
        current.conversions <= 1
      ) {
        detectedCategory = 'budget_exhaustion';
        targetMetric = 'Spend';
        observedVal = current.spend;
        expectedVal = expectedSpend;
        percentChange = spendDevPct;
        severity = 'high';
        anomalyScore = Math.min(100, Math.round(70 + spendZScore * 7));

        explanation = `Daily spend collapsed by ${Math.abs(Math.round(spendDevPct))}% (₹${current.spend.toFixed(2)} obs vs ₹${expectedSpend.toFixed(2)} baseline), indicating early mid-month budget exhaustion or credit cap reach.`;

        diagnosticSteps = [
          'Check campaign monthly budget caps and daily pacing thresholds.',
          'Verify billing payment method, credit line limits, and payment declines in ad manager.',
          'Check ad schedule or automated rule execution logs.',
          'Ensure ad group status is active and not paused by user or policy system.'
        ];
      }
      // 3. BID STRATEGY CHANGE / CPA SPIKE
      // CPA spikes significantly (> 90%) or spend surges without proportional conversions
      else if (
        current.spend >= config.minSpendThreshold &&
        cpaDevPct >= 90 &&
        (spendZScore >= config.zScoreThreshold || convZScore >= config.zScoreThreshold)
      ) {
        detectedCategory = 'bid_strategy_change';
        targetMetric = 'CPA';
        observedVal = current.cpa;
        expectedVal = expectedCpa;
        percentChange = cpaDevPct;
        severity = cpaDevPct >= 150 ? 'critical' : 'medium';
        anomalyScore = Math.min(100, Math.round(65 + Math.max(spendZScore, convZScore) * 8));

        explanation = `Cost per Acquisition (CPA) spiked by +${Math.round(cpaDevPct)}% (₹${current.cpa.toFixed(2)} obs vs ₹${expectedCpa.toFixed(2)} baseline), likely caused by automated bid strategy learning shifts or aggressive target CPA/ROAS adjustments.`;

        diagnosticSteps = [
          'Review recent campaign bid strategy changes (Target CPA/ROAS adjustments).',
          'Inspect ad group keyword bid multipliers and competitor auction overlap metrics.',
          'Check search term impression share and waste search term spikes.',
          'Allow 5-7 days for Smart Bidding machine learning recalibration before manual reset.'
        ];
      }
      // 4. HARMLLESS SEASONAL SHIFT (Expected Lift)
      // Both spend AND conversions increase proportionally (>= 30% lift, CVR stable)
      else if (
        spendDevPct >= 30 &&
        convDevPct >= 25 &&
        Math.abs(spendDevPct - convDevPct) < 40
      ) {
        // Suppress alert or classify as low severity seasonal shift to prevent alert fatigue!
        detectedCategory = 'seasonal_shift';
        targetMetric = 'Spend';
        observedVal = current.spend;
        expectedVal = expectedSpend;
        percentChange = spendDevPct;
        severity = 'low';
        anomalyScore = Math.min(45, Math.round(30 + spendZScore * 3));

        explanation = `Parallel spend (+${Math.round(spendDevPct)}%) and conversion (+${Math.round(convDevPct)}%) expansion detected, matching expected seasonal promotional volume. No intervention required.`;

        diagnosticSteps = [
          'Monitor return on ad spend (ROAS) performance.',
          'Ensure inventory and fulfillment support increased order volume.'
        ];
      }

      // If an actionable anomaly was identified (ignoring suppressed noise)
      if (detectedCategory && detectedCategory !== 'seasonal_shift') {
        const stdDevValue = targetMetric === 'Conversions' ? convBaseline.stdDev : spendBaseline.stdDev;
        const upperBand = Number((expectedVal + 2 * stdDevValue).toFixed(2));
        const lowerBand = Math.max(0, Number((expectedVal - 2 * stdDevValue).toFixed(2)));

        alerts.push({
          id: `alt-${campaign.replace(/[^a-zA-Z0-9]/g, '').toLowerCase()}-${current.date}`,
          date: current.date,
          campaign,
          metric: targetMetric,
          observedValue: Number(observedVal.toFixed(2)),
          expectedBaseline: Number(expectedVal.toFixed(2)),
          upperBand,
          lowerBand,
          percentChange: Number(percentChange.toFixed(1)),
          severity,
          category: detectedCategory,
          explanation,
          anomalyScore,
          status: 'new',
          diagnosticSteps,
          isGroundTruth: current.is_incident,
          isFalsePositive: current.is_incident === false
        });

        lastAlertDateMap[campaign] = current.date;
      }
    }
  });

  // Calculate Precision / Recall / FPR against Ground Truth if available
  const hasGroundTruth = records.some(r => r.is_incident !== undefined);
  let confirmedIncidents = 0; // True Positives
  let falsePositives = 0;
  let missedIncidents = 0; // False Negatives
  let trueNegatives = 0;

  if (hasGroundTruth) {
    // Map alerts by date and campaign
    const alertMap = new Set(alerts.map(a => `${a.campaign}__${a.date}`));

    records.forEach(rec => {
      const isAlerted = alertMap.has(`${rec.campaign}__${rec.date}`);
      const isActualIncident = rec.is_incident === true;

      if (isAlerted && isActualIncident) {
        confirmedIncidents++;
      } else if (isAlerted && !isActualIncident) {
        falsePositives++;
      } else if (!isAlerted && isActualIncident) {
        missedIncidents++;
      } else {
        trueNegatives++;
      }
    });
  }

  const totalPositives = confirmedIncidents + falsePositives;
  const totalActualIncidents = confirmedIncidents + missedIncidents;
  const totalActualNegatives = falsePositives + trueNegatives;

  const precision = hasGroundTruth && totalPositives > 0 ? confirmedIncidents / totalPositives : null;
  const recall = hasGroundTruth && totalActualIncidents > 0 ? confirmedIncidents / totalActualIncidents : null;
  const falsePositiveRate = hasGroundTruth && totalActualNegatives > 0 ? falsePositives / totalActualNegatives : null;
  const f1Score = precision && recall && (precision + recall) > 0 ? (2 * precision * recall) / (precision + recall) : null;

  const metrics: ModelMetrics = {
    totalAlerts: alerts.length,
    confirmedIncidents,
    falsePositives,
    missedIncidents,
    trueNegatives,
    precision: precision !== null ? Number((precision * 100).toFixed(1)) : null,
    recall: recall !== null ? Number((recall * 100).toFixed(1)) : null,
    falsePositiveRate: falsePositiveRate !== null ? Number((falsePositiveRate * 100).toFixed(1)) : null,
    f1Score: f1Score !== null ? Number((f1Score * 100).toFixed(1)) : null,
    hasGroundTruth
  };

  return { alerts: alerts.sort((a, b) => b.date.localeCompare(a.date)), metrics };
}
