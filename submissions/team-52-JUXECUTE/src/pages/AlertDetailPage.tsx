import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Copy,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  ShieldAlert,
  Clock,
  Activity,
  FileCheck,
  XCircle,
  RotateCcw,
} from 'lucide-react'
import { Card, CardHeader } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { ExplainableAlertCard } from '../components/alerts/ExplainableAlertCard'
import { ConfirmationModal } from '../components/ui/ConfirmationModal'
import { useToast } from '../components/ui/ToastContext'
import { AlertService } from '../services/alertService'
import { Alert, AlertStatus } from '../types/alert'
import { formatDate, formatDateTime, formatDeviation } from '../utils/formatters'
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'

export const AlertDetailPage: React.FC = () => {
  const { alertId } = useParams<{ alertId: string }>()
  const navigate = useNavigate()
  const toast = useToast()

  const [alert, setAlert] = useState<Alert | null>(null)
  const [loading, setLoading] = useState(true)

  // Confirmation modal state
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean
    title: string
    message: string
    newStatus: AlertStatus
    variant?: 'danger' | 'primary'
  }>({
    isOpen: false,
    title: '',
    message: '',
    newStatus: 'resolved',
    variant: 'primary',
  })

  useEffect(() => {
    async function load() {
      if (!alertId) return
      try {
        setLoading(true)
        const a = await AlertService.getAlertById(alertId)
        setAlert(a)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [alertId])

  if (loading || !alert) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3867F5]" />
        <p className="text-xs text-slate-500">Retrieving alert evidence dossier...</p>
      </div>
    )
  }

  const handleStatusChange = async (status: AlertStatus) => {
    if (status === 'dismissed' || status === 'resolved') {
      setConfirmModal({
        isOpen: true,
        title: status === 'dismissed' ? 'Dismiss Anomaly Alert?' : 'Resolve Anomaly Alert?',
        message:
          status === 'dismissed'
            ? 'Dismissing will mark this anomaly as a recognized non-issue or benign event. It will be excluded from critical incident escalations.'
            : 'Resolving will record that the operational root cause (e.g. tag repair, budget increase) has been addressed.',
        newStatus: status,
        variant: status === 'dismissed' ? 'danger' : 'primary',
      })
      return
    }

    await applyStatusUpdate(status)
  }

  const applyStatusUpdate = async (status: AlertStatus) => {
    const updated = await AlertService.updateAlertStatus(alert.id, status)
    if (updated) {
      setAlert(updated)
      toast.success(`Alert marked as ${status.toUpperCase()}`)
    }
    setConfirmModal((prev) => ({ ...prev, isOpen: false }))
  }

  const handleCopySummary = () => {
    const text = AlertService.copyAlertSummary(alert)
    navigator.clipboard.writeText(text)
    toast.success('Alert summary copied to clipboard!')
  }

  const evidenceChartData = (alert.evidenceHistory || []).map((d) => ({
    date: d.date,
    actual: d.actual,
    baseline: d.baseline,
    lower: d.lowerBand,
    upper: d.upperBand,
    bandBase: d.lowerBand,
    bandRange: Math.max(0, d.upperBand - d.lowerBand),
    isAnomaly: d.isAnomalous,
  }))

  return (
    <div className="space-y-6">
      {/* Back and Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/alerts')}
            icon={<ArrowLeft className="w-3.5 h-3.5" />}
          >
            All Alerts
          </Button>

          <div>
            <div className="flex items-center gap-2">
              <Badge
                variant={
                  alert.severity === 'critical'
                    ? 'critical'
                    : alert.severity === 'high'
                    ? 'warning'
                    : 'primary'
                }
                size="md"
                dot
              >
                {alert.severity.toUpperCase()}
              </Badge>
              <h2 className="text-xl font-bold text-[#172033] line-clamp-1">{alert.title}</h2>
            </div>
            <div className="flex items-center gap-2 text-xs text-[#697586] mt-0.5">
              <span className="font-mono text-slate-800 font-semibold">{alert.id}</span>
              <span>•</span>
              <button
                onClick={() => navigate(`/campaigns/${alert.campaignId}`)}
                className="text-[#3867F5] hover:underline font-medium cursor-pointer"
              >
                {alert.campaignName}
              </button>
              <span>•</span>
              <span>Detected {formatDateTime(alert.firstDetected)}</span>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopySummary}
            icon={<Copy className="w-3.5 h-3.5" />}
          >
            Copy Summary
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/campaigns/${alert.campaignId}`)}
            icon={<ExternalLink className="w-3.5 h-3.5" />}
          >
            View Campaign
          </Button>

          {alert.status !== 'investigating' && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleStatusChange('investigating')}
            >
              Mark Investigating
            </Button>
          )}

          {alert.status !== 'resolved' && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleStatusChange('resolved')}
              icon={<CheckCircle2 className="w-3.5 h-3.5" />}
            >
              Resolve Alert
            </Button>
          )}

          {alert.status === 'resolved' && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleStatusChange('new')}
              icon={<RotateCcw className="w-3.5 h-3.5" />}
            >
              Reopen Alert
            </Button>
          )}

          {alert.status !== 'dismissed' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleStatusChange('dismissed')}
              className="text-slate-500 hover:text-rose-600"
            >
              Dismiss
            </Button>
          )}
        </div>
      </div>

      {/* Metric Breakdown Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <Card className="p-3.5">
          <span className="text-[11px] font-medium text-[#697586]">Observed Value</span>
          <div className="text-xl font-black text-rose-600 mt-1">{alert.observedValue}</div>
          <span className="text-[10px] text-slate-400">Metric: {alert.metric.toUpperCase()}</span>
        </Card>

        <Card className="p-3.5">
          <span className="text-[11px] font-medium text-[#697586]">Expected Baseline</span>
          <div className="text-xl font-bold text-slate-900 mt-1">{alert.expectedBaseline}</div>
          <span className="text-[10px] text-slate-400">
            Band: {alert.baselineRange[0]} – {alert.baselineRange[1]}
          </span>
        </Card>

        <Card className="p-3.5">
          <span className="text-[11px] font-medium text-[#697586]">Deviation</span>
          <div className="text-xl font-black text-rose-600 mt-1">
            {formatDeviation(alert.relativeDeviation)}
          </div>
          <span className="text-[10px] text-slate-400">Abs: {alert.absoluteDeviation}</span>
        </Card>

        <Card className="p-3.5">
          <span className="text-[11px] font-medium text-[#697586]">Anomaly Score</span>
          <div className="text-xl font-bold text-slate-900 mt-1">
            {alert.anomalyScore.toFixed(1)}{' '}
            <span className="text-xs font-normal text-slate-500">MAD</span>
          </div>
          <span className="text-[10px] text-slate-400">Threshold: 3.0 MAD</span>
        </Card>

        <Card className="p-3.5">
          <span className="text-[11px] font-medium text-[#697586]">Duration Active</span>
          <div className="text-xl font-bold text-slate-900 mt-1">{alert.durationDays} Days</div>
          <span className="text-[10px] text-slate-400">Persistent Event</span>
        </Card>

        <Card className="p-3.5">
          <span className="text-[11px] font-medium text-[#697586]">Alert Status</span>
          <div className="mt-1">
            <Badge
              variant={
                alert.status === 'resolved'
                  ? 'healthy'
                  : alert.status === 'investigating'
                  ? 'primary'
                  : alert.status === 'dismissed'
                  ? 'neutral'
                  : 'outline'
              }
              size="md"
            >
              {alert.status.toUpperCase()}
            </Badge>
          </div>
          <span className="text-[10px] text-slate-400">In Local Session</span>
        </Card>
      </div>

      {/* Core Feature: Reusable Explainable Diagnostic Card */}
      <ExplainableAlertCard alert={alert} />

      {/* Evidence Trajectory Chart */}
      <Card>
        <CardHeader
          title="Anomaly Evidence Trajectory"
          subtitle="Observed metric compared with adaptive confidence band before and during anomaly"
        />

        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={evidenceChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E4E9F1" />
              <XAxis
                dataKey="date"
                tickFormatter={(d) => formatDate(d, 'MMM d')}
                tick={{ fontSize: 11, fill: '#697586' }}
                axisLine={{ stroke: '#E4E9F1' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#697586' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="bandBase"
                stackId="band"
                stroke="none"
                fill="transparent"
              />
              <Area
                type="monotone"
                dataKey="bandRange"
                stackId="band"
                stroke="none"
                fill="#E0E7FF"
                fillOpacity={0.6}
                name="Confidence Envelope"
              />
              <Line
                type="monotone"
                dataKey="baseline"
                stroke="#94A3B8"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                dot={false}
                name="Expected Baseline"
              />
              <Line
                type="monotone"
                dataKey="actual"
                stroke="#DC3545"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#DC3545' }}
                name="Actual Observation"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Incident Timeline & Associated Events */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader
            title="Incident Lifecycle Timeline"
            subtitle="Chronological audit history of detections and operator actions"
          />
          <div className="space-y-4 text-xs">
            {(alert.timeline || []).map((item, idx) => (
              <div key={idx} className="flex gap-3 relative">
                {idx !== (alert.timeline?.length || 0) - 1 && (
                  <div className="absolute top-6 left-3 w-0.5 bottom-0 -mb-4 bg-slate-200" />
                )}
                <div className="w-6 h-6 rounded-full bg-blue-100 text-[#3867F5] flex items-center justify-center shrink-0 z-10">
                  <Clock className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 pb-2">
                  <div className="flex items-center justify-between text-slate-500 text-[11px]">
                    <span>{formatDateTime(item.timestamp)}</span>
                    {item.actor && (
                      <span className="font-semibold text-slate-700">{item.actor}</span>
                    )}
                  </div>
                  <p className="font-medium text-slate-900 mt-0.5">{item.event}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Correlation & Root Cause Mapping"
            subtitle="Multi-metric diagnostic context"
          />
          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
              <span className="font-bold text-slate-800">Primary Classification</span>
              <p className="text-slate-600">{alert.category}</p>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
              <span className="font-bold text-slate-800">Detection Algorithm</span>
              <p className="text-slate-600 font-mono text-[11px]">{alert.detectionMethod}</p>
            </div>

            {alert.incidentId && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-between">
                <div>
                  <span className="font-bold text-blue-900">Linked Master Incident</span>
                  <p className="text-blue-700 text-[11px]">
                    Incident ID: {alert.incidentId} (Grouped Multi-Metric Anomaly)
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate('/incidents')}
                  className="bg-white text-xs"
                >
                  Inspect Incident →
                </Button>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        variant={confirmModal.variant}
        confirmText="Confirm Status Change"
        onConfirm={() => applyStatusUpdate(confirmModal.newStatus)}
        onCancel={() => setConfirmModal((prev) => ({ ...prev, isOpen: false }))}
      />
    </div>
  )
}
