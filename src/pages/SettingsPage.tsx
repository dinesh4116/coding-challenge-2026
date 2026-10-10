import React, { useState, useEffect } from 'react'
import {
  Settings,
  Bell,
  Database,
  Sliders,
  Save,
  RotateCcw,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Server,
} from 'lucide-react'
import { Card, CardHeader } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { DATASET_METADATA } from '../mocks/demoData'
import { getApiConfig, saveApiConfig, ApiClient } from '../services/apiClient'
import { useToast } from '../components/ui/ToastContext'

const STORAGE_KEY_DETECTION_SETTINGS = 'campaignguard_detection_settings'
const STORAGE_KEY_ALERT_PREFS = 'campaignguard_alert_prefs'

interface DetectionConfig {
  baselineWindowDays: number
  anomalyScoreThreshold: number
  persistenceDurationDays: number
  minVolumeSpend: number
  deduplicationWindowHours: number
  seasonalityAdjustment: boolean
}

const defaultDetectionConfig: DetectionConfig = {
  baselineWindowDays: 28,
  anomalyScoreThreshold: 3.0,
  persistenceDurationDays: 2,
  minVolumeSpend: 100,
  deduplicationWindowHours: 24,
  seasonalityAdjustment: true,
}

interface AlertPrefs {
  minSeverityNotification: 'critical' | 'high' | 'medium' | 'low'
  routingMode: 'immediate' | 'digest'
  digestGrouping: 'campaign' | 'severity' | 'channel'
  inAppSound: boolean
}

const defaultAlertPrefs: AlertPrefs = {
  minSeverityNotification: 'high',
  routingMode: 'immediate',
  digestGrouping: 'campaign',
  inAppSound: true,
}

export const SettingsPage: React.FC = () => {
  const toast = useToast()

  // Detection settings
  const [detection, setDetection] = useState<DetectionConfig>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_DETECTION_SETTINGS)
      if (stored) return { ...defaultDetectionConfig, ...JSON.parse(stored) }
    } catch {}
    return defaultDetectionConfig
  })

  // Alert preferences
  const [alertPrefs, setAlertPrefs] = useState<AlertPrefs>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_ALERT_PREFS)
      if (stored) return { ...defaultAlertPrefs, ...JSON.parse(stored) }
    } catch {}
    return defaultAlertPrefs
  })

  // Backend / API Config
  const [apiConfig, setApiConfigState] = useState(getApiConfig)
  const [backendStatus, setBackendStatus] = useState<string>('Checking...')

  // CSV upload state
  const [uploadFeedback, setUploadFeedback] = useState<{
    status: 'idle' | 'valid' | 'invalid'
    message: string
  }>({
    status: 'idle',
    message: '',
  })

  useEffect(() => {
    async function check() {
      const health = await ApiClient.checkHealth()
      setBackendStatus(health.status)
    }
    check()
  }, [])

  const handleSaveDetection = () => {
    localStorage.setItem(STORAGE_KEY_DETECTION_SETTINGS, JSON.stringify(detection))
    toast.success('Detection threshold settings saved locally!')
  }

  const handleSaveAlertPrefs = () => {
    localStorage.setItem(STORAGE_KEY_ALERT_PREFS, JSON.stringify(alertPrefs))
    toast.success('Notification routing preferences saved!')
  }

  const handleSaveApi = () => {
    saveApiConfig(apiConfig)
    toast.success('API backend configuration updated!')
  }

  // Handle CSV file validation
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.csv')) {
      setUploadFeedback({
        status: 'invalid',
        message: 'Invalid file format. Please upload a standard comma-separated .csv file.',
      })
      toast.error('File must be a .csv format')
      return
    }

    const reader = new FileReader()
    reader.onload = (event) => {
      const content = event.target?.result as string
      if (!content) return

      const lines = content.split(/\r\n|\n/).filter((l) => l.trim().length > 0)
      if (lines.length < 2) {
        setUploadFeedback({
          status: 'invalid',
          message: 'CSV file is empty or missing data rows.',
        })
        return
      }

      const headers = lines[0].toLowerCase().split(',').map((h) => h.trim().replace(/"/g, ''))
      const required = ['campaign_id', 'date', 'spend', 'clicks', 'conversions']
      const missing = required.filter((r) => !headers.includes(r))

      if (missing.length > 0) {
        setUploadFeedback({
          status: 'invalid',
          message: `Validation failed. Missing required columns: ${missing.join(', ')}. Existing working dataset preserved.`,
        })
        toast.error(`Missing required columns: ${missing.join(', ')}`)
      } else {
        setUploadFeedback({
          status: 'valid',
          message: `Validation successful! Verified ${lines.length - 1} records across required marketing columns (${required.join(', ')}). Ready for ingestion.`,
        })
        toast.success(`Dataset schema validated: ${lines.length - 1} rows parsed`)
      }
    }
    reader.readAsText(file)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-[#172033]">Settings & Configuration</h2>
        <p className="text-xs text-[#697586] mt-0.5">
          Configure adaptive anomaly detection sensitivity, notification routing, and external API integrations
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section 1: Detection Settings */}
        <Card className="space-y-4">
          <CardHeader
            title="Adaptive Detection Parameters"
            subtitle="Local demonstration settings (Controls threshold sensitivity & fatigue filter)"
          />

          <div className="space-y-3.5 text-xs">
            <div>
              <label className="font-semibold text-slate-800 block mb-1">
                Historical Baseline Rolling Window (Days)
              </label>
              <select
                value={detection.baselineWindowDays}
                onChange={(e) =>
                  setDetection({ ...detection, baselineWindowDays: Number(e.target.value) })
                }
                className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg p-2 font-medium text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#3867F5]"
              >
                <option value={14}>14 Calendar Days</option>
                <option value={28}>28 Calendar Days (Recommended: 4 Full Weekly Cycles)</option>
                <option value={60}>60 Calendar Days (Long-term Quarterly Baseline)</option>
              </select>
            </div>

            <div>
              <label className="font-semibold text-slate-800 block mb-1">
                Anomaly Score Threshold (MAD Multiplier)
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="2.0"
                  max="5.0"
                  step="0.1"
                  value={detection.anomalyScoreThreshold}
                  onChange={(e) =>
                    setDetection({ ...detection, anomalyScoreThreshold: Number(e.target.value) })
                  }
                  className="flex-1 accent-[#3867F5]"
                />
                <span className="font-mono font-bold text-slate-900 w-16 text-right">
                  {detection.anomalyScoreThreshold.toFixed(1)} MAD
                </span>
              </div>
              <span className="text-[10px] text-slate-500">
                Higher values suppress mild fluctuations; lower values catch subtler deviations.
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-semibold text-slate-800 block mb-1">
                  Persistence Filter (Days)
                </label>
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={detection.persistenceDurationDays}
                  onChange={(e) =>
                    setDetection({ ...detection, persistenceDurationDays: Number(e.target.value) })
                  }
                  className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg p-2 font-medium text-slate-900"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-800 block mb-1">
                  Deduplication Window (Hours)
                </label>
                <input
                  type="number"
                  min="6"
                  max="72"
                  value={detection.deduplicationWindowHours}
                  onChange={(e) =>
                    setDetection({ ...detection, deduplicationWindowHours: Number(e.target.value) })
                  }
                  className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg p-2 font-medium text-slate-900"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="seasonalityAdj"
                checked={detection.seasonalityAdjustment}
                onChange={(e) =>
                  setDetection({ ...detection, seasonalityAdjustment: e.target.checked })
                }
                className="accent-[#3867F5] w-4 h-4 rounded"
              />
              <label htmlFor="seasonalityAdj" className="font-medium text-slate-800">
                Automatic Day-of-Week Seasonality Adjustment (Suppresses normal weekend drops)
              </label>
            </div>

            <div className="pt-2">
              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveDetection}
                icon={<Save className="w-3.5 h-3.5" />}
              >
                Save Detection Settings
              </Button>
            </div>
          </div>
        </Card>

        {/* Section 2: Alert Routing Preferences */}
        <Card className="space-y-4">
          <CardHeader
            title="Alert Notification Preferences"
            subtitle="Configure local notification routing & fatigue control"
          />

          <div className="space-y-3.5 text-xs">
            <div>
              <label className="font-semibold text-slate-800 block mb-1">
                Minimum Severity Notification Threshold
              </label>
              <select
                value={alertPrefs.minSeverityNotification}
                onChange={(e) =>
                  setAlertPrefs({ ...alertPrefs, minSeverityNotification: e.target.value as any })
                }
                className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg p-2 font-medium text-slate-900"
              >
                <option value="critical">Critical Only (Maximum Fatigue Prevention)</option>
                <option value="high">High & Critical (Standard Performance Ops)</option>
                <option value="medium">Medium, High & Critical</option>
                <option value="low">All Severities (Including Informational)</option>
              </select>
            </div>

            <div>
              <label className="font-semibold text-slate-800 block mb-1">
                Routing Delivery Mode
              </label>
              <select
                value={alertPrefs.routingMode}
                onChange={(e) =>
                  setAlertPrefs({ ...alertPrefs, routingMode: e.target.value as any })
                }
                className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg p-2 font-medium text-slate-900"
              >
                <option value="immediate">Immediate Real-Time Trigger</option>
                <option value="digest">Consolidated Hourly Digest</option>
              </select>
            </div>

            <div>
              <label className="font-semibold text-slate-800 block mb-1">
                Preferred Digest Grouping Hierarchy
              </label>
              <select
                value={alertPrefs.digestGrouping}
                onChange={(e) =>
                  setAlertPrefs({ ...alertPrefs, digestGrouping: e.target.value as any })
                }
                className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg p-2 font-medium text-slate-900"
              >
                <option value="campaign">Group by Campaign</option>
                <option value="severity">Group by Severity Tier</option>
                <option value="channel">Group by Advertising Network</option>
              </select>
            </div>

            <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-amber-900 text-[11px] leading-relaxed">
              <strong>Notice:</strong> In demonstration mode, alerts are delivered via the in-app Alerts Center and Notification Tray. No external email/SMS messages are dispatched.
            </div>

            <div className="pt-2">
              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveAlertPrefs}
                icon={<Save className="w-3.5 h-3.5" />}
              >
                Save Alert Preferences
              </Button>
            </div>
          </div>
        </Card>

        {/* Section 3: Dataset Telemetry & Upload */}
        <Card className="space-y-4">
          <CardHeader
            title="Dataset Telemetry & Custom CSV Upload"
            subtitle="Benchmark dataset specifications and file schema validation"
          />

          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
              <div className="flex justify-between">
                <span className="text-slate-500">Current Dataset:</span>
                <span className="font-bold text-slate-900">{DATASET_METADATA.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Monitored Scope:</span>
                <span className="font-semibold text-slate-800">
                  {DATASET_METADATA.campaignCount} Campaigns • {DATASET_METADATA.totalDays} Days
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Date Range:</span>
                <span className="font-mono text-slate-700">
                  {DATASET_METADATA.dateRangeStart} to {DATASET_METADATA.dateRangeEnd}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Dataset Mode:</span>
                <Badge variant="purple" size="sm">
                  Synthetic Ground-Truth Benchmark
                </Badge>
              </div>
            </div>

            {/* Custom CSV Upload */}
            <div className="p-4 border-2 border-dashed border-[#E4E9F1] rounded-xl text-center space-y-2">
              <Upload className="w-6 h-6 text-[#3867F5] mx-auto" />
              <div>
                <p className="font-bold text-slate-800">Upload Campaign Dataset (.CSV)</p>
                <p className="text-[11px] text-slate-500">
                  Required columns: campaign_id, date, spend, clicks, conversions
                </p>
              </div>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                className="text-xs text-slate-500 file:mr-2 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-[#3867F5] hover:file:bg-blue-100 cursor-pointer"
              />
            </div>

            {/* Upload Feedback */}
            {uploadFeedback.status !== 'idle' && (
              <div
                className={`p-3 rounded-xl border flex items-start gap-2 text-xs leading-relaxed ${
                  uploadFeedback.status === 'valid'
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                    : 'bg-rose-50 border-rose-200 text-rose-900'
                }`}
              >
                {uploadFeedback.status === 'valid' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                )}
                <span>{uploadFeedback.message}</span>
              </div>
            )}
          </div>
        </Card>

        {/* Section 4: Backend API Integration */}
        <Card className="space-y-4">
          <CardHeader
            title="FastAPI Backend Integration"
            subtitle="Connect frontend to a production Python API backend"
          />

          <div className="space-y-3.5 text-xs">
            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-[#3867F5]" />
                <span className="font-semibold text-slate-800">Backend Connection Status:</span>
              </div>
              <Badge
                variant={backendStatus === 'connected' ? 'healthy' : 'warning'}
                size="sm"
              >
                {backendStatus.toUpperCase()}
              </Badge>
            </div>

            <div>
              <label className="font-semibold text-slate-800 block mb-1">
                FastAPI Base URL
              </label>
              <input
                type="text"
                value={apiConfig.baseUrl}
                onChange={(e) => setApiConfigState({ ...apiConfig, baseUrl: e.target.value })}
                placeholder="http://localhost:8000"
                className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg p-2 font-mono text-xs text-slate-900"
              />
            </div>

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="useDemoData"
                checked={apiConfig.useDemoData}
                onChange={(e) =>
                  setApiConfigState({ ...apiConfig, useDemoData: e.target.checked })
                }
                className="accent-[#3867F5] w-4 h-4 rounded"
              />
              <label htmlFor="useDemoData" className="font-medium text-slate-800">
                Use Synthetic Demo Data (Disable to route calls to live FastAPI endpoints)
              </label>
            </div>

            <div className="pt-2">
              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveApi}
                icon={<Save className="w-3.5 h-3.5" />}
              >
                Save Backend Configuration
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
