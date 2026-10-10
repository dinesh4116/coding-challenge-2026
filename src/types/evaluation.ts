export interface IncidentCategoryEvaluation {
  category: string
  knownIncidents: number
  detectedIncidents: number
  missedIncidents: number
  precision: number
  recall: number
  f1Score: number
}

export interface EvaluationRun {
  id: string
  name: string
  method: 'Fixed-Threshold Baseline (Naive)' | 'Campaign-Specific Adaptive' | 'Adaptive + Deduplication & Persistence (CampaignGuard AI)'
  shortName: string
  datasetName: string
  timestamp: string
  totalObservations: number
  totalCampaigns: number
  totalAlertsGenerated: number
  truePositives: number
  falsePositives: number
  falseNegatives: number
  trueNegatives: number
  precision: number
  recall: number
  f1Score: number
  falsePositiveRate: number
  detectionDelayDays: number
  incidentBreakdown: IncidentCategoryEvaluation[]
  alertReductionPercent: number // e.g. 74% reduction in alert fatigue
}

export interface EvaluationMetricsSummary {
  precision: number
  recall: number
  f1Score: number
  falsePositiveRate: number
  truePositives: number
  falsePositives: number
  falseNegatives: number
  trueNegatives: number
  totalAlerts: number
}
