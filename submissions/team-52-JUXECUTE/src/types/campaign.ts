export type ChannelType =
  | 'Google Search'
  | 'Google Shopping'
  | 'Google PMax'
  | 'Meta'
  | 'Microsoft Search'
  | 'Google Demand Gen'
  | 'LinkedIn'
  | 'YouTube'
  | 'TikTok'
  | 'Pinterest'
  | 'Google Display'
  | string

export type CampaignHealth = 'healthy' | 'warning' | 'critical' | 'investigating'

export interface Campaign {
  id: string
  name: string
  channel: ChannelType
  vertical?: 'ecommerce' | 'b2b'
  landingPageGroup?: string
  status: CampaignHealth
  dailyBudget: number
  targetCpa: number
  spendToday: number
  totalSpend180d: number
  clicksToday: number
  totalClicks180d: number
  conversionsToday: number
  totalConversions180d: number
  revenueToday?: number
  totalRevenue180d?: number
  ctrToday: number
  avgCtr180d: number
  cpcToday: number
  avgCpc180d: number
  cvrToday: number
  avgCvr180d: number
  activeIncidentsCount: number
  totalAlertsCount: number
  lastAnomalyDate: string | null
  createdDate: string
}

export interface MetricDataPoint {
  date: string
  spend: number
  clicks: number
  impressions: number
  conversions: number
  revenue?: number
  ctr: number
  cpc: number
  cvr: number
  baselineSpend: number
  baselineClicks: number
  baselineConversions: number
  baselineRevenue?: number
  baselineCtr: number
  baselineCpc: number
  baselineCvr: number
  lowerBandSpend: number
  upperBandSpend: number
  lowerBandClicks: number
  upperBandClicks: number
  lowerBandConversions: number
  upperBandConversions: number
  isAnomaly: boolean
  anomalyMetric?: 'spend' | 'clicks' | 'conversions' | 'revenue' | 'ctr' | 'cpc' | 'cvr' | string
  anomalySeverity?: 'critical' | 'high' | 'medium' | 'low'
  anomalyScore?: number
}

export interface CampaignConfig {
  campaignId: string
  baselineWindowDays: number
  anomalyScoreThreshold: number
  persistenceDurationDays: number
  minVolumeSpend: number
  minVolumeClicks: number
  deduplicationWindowHours: number
  adaptiveSensitivity: 'conservative' | 'balanced' | 'aggressive'
}
