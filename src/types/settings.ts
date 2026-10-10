import { AlertSeverity } from './alert'

export interface DetectionSettings {
  baselineWindowDays: number
  anomalyScoreThreshold: number
  persistenceDurationDays: number
  minVolumeSpend: number
  minVolumeClicks: number
  deduplicationWindowHours: number
  seasonalityAdjustment: boolean
  adaptiveSensitivity: 'conservative' | 'balanced' | 'aggressive'
}

export interface AlertPreferences {
  minSeverityNotification: AlertSeverity
  routingMode: 'immediate' | 'digest'
  digestGrouping: 'campaign' | 'severity' | 'channel'
  soundEnabled: boolean
  emailNotificationMock: boolean
  slackWebhookMock: string
}

export interface DatasetMetadata {
  name: string
  campaignCount: number
  totalDays: number
  dateRangeStart: string
  dateRangeEnd: string
  totalDataPoints: number
  lastUpdated: string
  isSynthetic: boolean
  validationStatus: 'valid' | 'warning' | 'invalid'
  validationMessage?: string
}
