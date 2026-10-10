export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low'

export type AlertStatus = 'new' | 'investigating' | 'resolved' | 'dismissed'

export type AlertCategory =
  | 'Possible Conversion Tracking Failure'
  | 'Budget Exhaustion'
  | 'Delivery Outage / Account Freeze'
  | 'Traffic Surge / Bidding Disruption'
  | 'Promotional / Seasonal Flash Event'
  | 'Performance Degradation'
  | 'Seasonal or Expected Variation'
  | 'Unknown Anomaly'
  | string

export type MetricType =
  | 'spend'
  | 'clicks'
  | 'conversions'
  | 'revenue'
  | 'impressions'
  | 'ctr'
  | 'cpc'
  | 'cvr'
  | string

export interface AlertExplanation {
  whatChanged: string
  whatExpected: string
  whatObserved: string
  deviationMagnitude: string
  whyFlagged: string
  recommendedFirstStep: string
  confidence: number // e.g. 0.94 (94%)
}

export interface AlertTimelineEvent {
  timestamp: string
  event: string
  actor?: string
  type?: 'detection' | 'status_change' | 'diagnostic_note' | 'system'
}

export interface AlertEvidencePoint {
  date: string
  actual: number
  baseline: number
  lowerBand: number
  upperBand: number
  isAnomalous: boolean
}

export interface Alert {
  id: string
  title?: string
  campaignId: string
  campaignName: string
  channel: string
  vertical?: string
  landingPageGroup?: string
  date?: string
  metric: MetricType
  severity: AlertSeverity
  status: AlertStatus
  category: AlertCategory
  firstDetected: string // ISO string
  durationDays: number
  observedValue: number
  expectedBaseline: number
  baselineRange: [number, number] // [lower, upper]
  absoluteDeviation: number
  relativeDeviation: number // e.g., -45.5 for -45.5%
  anomalyScore: number // MAD-based or robust Z-score, e.g., 4.2
  detectionMethod: string
  explanation: AlertExplanation
  relatedAlertIds?: string[]
  timeline?: AlertTimelineEvent[]
  evidenceHistory?: AlertEvidencePoint[]
  incidentId?: string
  metricsAffected?: string[]
}

export interface AlertFilterOptions {
  severity?: AlertSeverity | 'all'
  status?: AlertStatus | 'all'
  category?: AlertCategory | 'all'
  campaignId?: string | 'all'
  metric?: MetricType | 'all'
  searchQuery?: string
  dateRange?: string // '7d' | '30d' | '90d' | '180d'
  sortBy?: 'newest' | 'oldest' | 'severity' | 'deviation'
}
