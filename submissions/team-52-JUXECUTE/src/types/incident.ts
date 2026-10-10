import { AlertCategory, AlertSeverity, MetricType } from './alert'

export type IncidentStatus = 'active' | 'investigating' | 'resolved' | 'suppressed'

export interface IncidentTimelineItem {
  date: string
  note: string
  metricImpact?: string
  actor?: string
}

export interface Incident {
  id: string
  title: string
  campaignId: string
  campaignName: string
  channel: string
  category: AlertCategory
  severity: AlertSeverity
  status: IncidentStatus
  startDate: string
  endDate?: string
  affectedMetrics: MetricType[]
  classificationRationale: string
  evidenceSummary: string
  recommendedInvestigationStep: string
  relatedAlertIds: string[]
  timeline: IncidentTimelineItem[]
  estimatedCostImpact: number // e.g. estimated wasted spend or lost revenue
  isSuppressedSeasonal?: boolean
}
