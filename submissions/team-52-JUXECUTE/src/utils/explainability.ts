import { AlertCategory, AlertExplanation, MetricType } from '../types/alert'
import { formatCurrency, formatNumber, formatPercent } from './formatters'

interface ExplainabilityInput {
  campaignName: string
  metric: MetricType
  category: AlertCategory
  observedValue: number
  expectedBaseline: number
  baselineRange: [number, number]
  relativeDeviation: number // percentage e.g. -45.0
  clicks?: number
  spend?: number
  conversions?: number
}

function formatMetricVal(metric: MetricType, val: number): string {
  if (metric === 'spend' || metric === 'cpc') return formatCurrency(val)
  if (metric === 'ctr' || metric === 'cvr') return formatPercent(val / 100)
  return formatNumber(val)
}

export function generateAlertExplanation(input: ExplainabilityInput): AlertExplanation {
  const {
    campaignName,
    metric,
    category,
    observedValue,
    expectedBaseline,
    baselineRange,
    relativeDeviation,
  } = input

  const metricLabel = metric.toUpperCase()
  const direction = relativeDeviation < 0 ? 'drop' : 'surge'
  const absDev = Math.abs(relativeDeviation)
  const devString = `${absDev.toFixed(1)}% ${relativeDeviation < 0 ? 'below' : 'above'}`
  const formattedObserved = formatMetricVal(metric, observedValue)
  const formattedExpected = formatMetricVal(metric, expectedBaseline)
  const formattedRange = `${formatMetricVal(metric, baselineRange[0])} – ${formatMetricVal(metric, baselineRange[1])}`

  let whatChanged = `${metricLabel} exhibited an abnormal ${direction} for ${campaignName}.`
  let whatExpected = `Expected historical baseline was ${formattedExpected} (typical normal band: ${formattedRange}).`
  let whatObserved = `Observed daily ${metricLabel} was ${formattedObserved}, deviating by ${devString} historical baseline.`
  let deviationMagnitude = `${devString} median (${relativeDeviation > 0 ? '+' : ''}${relativeDeviation.toFixed(1)}%).`
  let whyFlagged = `The metric breached the campaign-specific adaptive MAD threshold for sustained daily observation.`
  let recommendedFirstStep = `Inspect campaign logs and delivery status before altering bidding rules.`
  let confidence = 0.88

  switch (category) {
    case 'Possible Conversion Tracking Failure':
      whatChanged = `Conversions plummeted sharply while click volume remained steady for ${campaignName}.`
      whatObserved = `Conversions dropped to ${formattedObserved} (expected ~${formattedExpected}), while traffic continued delivering.`
      whyFlagged = `Disproportionate divergence between clicks and conversions strongly indicates an instrumentation failure rather than ad audience fatigue.`
      recommendedFirstStep = `Verify Google Tag Manager / Meta Pixel event fires, postbacks, and destination thank-you page URLs.`
      confidence = 0.96
      break

    case 'Budget Exhaustion':
      whatChanged = `Daily spend capped out significantly earlier than normal schedule for ${campaignName}.`
      whatObserved = `Recorded spend was ${formattedObserved} vs target baseline ${formattedExpected}, causing traffic delivery to halt prematurely.`
      whyFlagged = `Aggressive morning delivery or runaway bidding drained daily budget before peak afternoon conversion hours.`
      recommendedFirstStep = `Check campaign pacing settings, dayparting schedules, and whether automated bid caps were exceeded.`
      confidence = 0.92
      break

    case 'Bid Strategy Change':
      whatChanged = `Rapid shift in cost per click and bidding volatility detected for ${campaignName}.`
      whatObserved = `Observed ${metricLabel} of ${formattedObserved} drifted ${devString} target baseline.`
      whyFlagged = `Bidding algorithm adjustment or aggressive keyword bid modifier caused abrupt auction price inflation.`
      recommendedFirstStep = `Review audit change history for Target CPA/ROAS adjustments, Smart Bidding learning status, or competitor bidding pressure.`
      confidence = 0.89
      break

    case 'Performance Degradation':
      whatChanged = `Persistent downward trend in user engagement and click-through efficiency for ${campaignName}.`
      whatObserved = `${metricLabel} registered ${formattedObserved}, sustaining a ${devString} baseline across recent periods.`
      whyFlagged = `Statistically significant multi-day performance decline exceeding the adaptive volatility band.`
      recommendedFirstStep = `Review ad creative fatigue metrics (frequency > 3.5), audience saturation, and landing page load speeds.`
      confidence = 0.85
      break

    case 'Seasonal or Expected Variation':
      whatChanged = `Metric shift aligns with established day-of-week or calendar holiday patterns.`
      whatObserved = `${metricLabel} reached ${formattedObserved}, within seasonal historical expectation for this calendar window.`
      whyFlagged = `Flagged for informational verification only; suppressed from critical alerts by CampaignGuard deduplication.`
      recommendedFirstStep = `No immediate operational change required. Validate against year-over-year seasonality benchmarks.`
      confidence = 0.94
      break

    case 'Unknown Anomaly':
    default:
      whatChanged = `Unexpected statistical divergence in ${metricLabel} for ${campaignName}.`
      whyFlagged = `Residual deviation exceeded the campaign's 3.0 modified Z-score boundary.`
      recommendedFirstStep = `Cross-reference ad network status dashboard, external tracking, and landing page uptime.`
      confidence = 0.75
      break
  }

  return {
    whatChanged,
    whatExpected,
    whatObserved,
    deviationMagnitude,
    whyFlagged,
    recommendedFirstStep,
    confidence,
  }
}
