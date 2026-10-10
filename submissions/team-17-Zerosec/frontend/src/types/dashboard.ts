export type Severity = 'critical' | 'high' | 'medium' | 'low';

export type IncidentCategory = 
  | 'tracking_failure' 
  | 'budget_exhaustion' 
  | 'bid_strategy_change' 
  | 'seasonal_shift' 
  | 'unknown';

export type AlertStatus = 'new' | 'acknowledged' | 'resolved';

export interface CampaignMetricRecord {
  date: string;
  campaign: string;
  spend: number;
  conversions: number;
  impressions: number;
  clicks: number;
  cpa: number;
  cvr: number;
  ctr: number;
  is_incident?: boolean;
  incident_type?: string;
  raw?: Record<string, any>;
}

export interface ColumnMapping {
  dateField: string;
  campaignField: string;
  spendField: string;
  conversionsField: string;
  impressionsField?: string;
  clicksField?: string;
  isIncidentField?: string;
  incidentTypeField?: string;
}

export interface AnomalyAlert {
  id: string;
  date: string;
  campaign: string;
  metric: 'Conversions' | 'Spend' | 'CPA' | 'CVR' | 'CTR';
  observedValue: number;
  expectedBaseline: number;
  upperBand: number;
  lowerBand: number;
  percentChange: number;
  severity: Severity;
  category: IncidentCategory;
  explanation: string;
  anomalyScore: number; // 0 to 100
  status: AlertStatus;
  diagnosticSteps: string[];
  isGroundTruth?: boolean;
  isFalsePositive?: boolean;
}

export interface CampaignSummary {
  campaign: string;
  totalSpend: number;
  totalConversions: number;
  totalImpressions: number;
  totalClicks: number;
  avgCpa: number;
  avgCvr: number;
  anomalyScore: number;
  healthStatus: 'healthy' | 'warning' | 'critical';
  totalAlerts: number;
  criticalAlerts: number;
  lastIncidentDate?: string;
}

export interface ModelMetrics {
  totalAlerts: number;
  confirmedIncidents: number; // True Positives
  falsePositives: number;
  missedIncidents: number; // False Negatives
  trueNegatives: number;
  precision: number | null;
  recall: number | null;
  falsePositiveRate: number | null;
  f1Score: number | null;
  hasGroundTruth: boolean;
}

export interface DetectionConfig {
  baselineWindow: number; // e.g. 14 days
  zScoreThreshold: number; // e.g. 2.5
  minSpendThreshold: number; // e.g. 50
  suppressConsecutiveAlerts: boolean;
  cooldownPeriodDays: number;
  enableMultiMetricCorrelation: boolean;
  backendApiUrl?: string;
}

export interface DatasetMetadata {
  filename: string;
  source: 'demo' | 'uploaded';
  rowCount: number;
  campaignCount: number;
  minDate: string;
  maxDate: string;
  uploadedAt: string;
  headers: string[];
  mappedColumns: ColumnMapping;
}

export interface BackendSummary {
  campaigns_analyzed: number;
  records_analyzed: number;
  input_rows: number;
  date_start: string;
  date_end: string;
  days_covered: number;
  anomalies_detected: number;
  duplicates_removed: number;
  findings: number;
  grouped_alerts: number;
  new_alerts: number;
  reopened_alerts: number;
  escalated_alerts: number;
  suppressed_alerts: number;
  notifications_sent: number;
  immediate_notifications: number;
  digest_notifications: number;
  alerts_total: number;
}

export interface BackendEvaluation {
  available: boolean;
  reason?: string | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  precision_immediate: number | null;
  alerts_evaluated: number;
  immediate_alerts_evaluated: number;
  true_positive_alerts?: number | null;
  false_positive_alerts?: number | null;
  false_positive_alert_ids?: string[];
  incidents_total?: number | null;
  incidents_detected?: number | null;
  matching_rule?: string;
  notes?: string[];
  naive_baseline?: {
    total_alerts: number;
    precision: number | null;
    recall: number | null;
    f1_score: number | null;
    note?: string;
  };
}

export type BackendStatus = 'connected' | 'offline' | 'checking';

export type ActiveTab = 'overview' | 'campaigns' | 'alerts' | 'analysis' | 'reports' | 'settings';
