import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingDown,
  TrendingUp,
  Settings,
  Activity,
  History,
  Shield,
  Layers,
  Sparkles,
} from 'lucide-react'
import { Card, CardHeader } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { TimeSeriesMetricChart } from '../components/charts/TimeSeriesMetricChart'
import { CampaignService } from '../services/campaignService'
import { Campaign, MetricDataPoint } from '../types/campaign'
import { Alert } from '../types/alert'
import { formatCurrency, formatNumber, formatPercent, formatDate, formatDateTime } from '../utils/formatters'

export const CampaignDetailPage: React.FC = () => {
  const { campaignId } = useParams<{ campaignId: string }>()
  const navigate = useNavigate()

  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [metrics, setMetrics] = useState<MetricDataPoint[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [activeTab, setActiveTab] = useState<'overview' | 'performance' | 'history' | 'config'>('overview')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      if (!campaignId) return
      try {
        setLoading(true)
        const [c, m, a] = await Promise.all([
          CampaignService.getCampaignById(campaignId),
          CampaignService.getCampaignMetrics(campaignId, '180d'),
          CampaignService.getCampaignAlerts(campaignId),
        ])
        setCampaign(c)
        setMetrics(m)
        setAlerts(a)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [campaignId])

  if (loading || !campaign) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3867F5]" />
        <p className="text-xs text-slate-500">Loading campaign diagnostic telemetry...</p>
      </div>
    )
  }

  const isCritical = campaign.status === 'critical'
  const isWarning = campaign.status === 'warning'

  return (
    <div className="space-y-6">
      {/* Header with Back button and Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/campaigns')}
            icon={<ArrowLeft className="w-3.5 h-3.5" />}
          >
            All Campaigns
          </Button>

          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-[#172033]">{campaign.name}</h2>
              <Badge
                variant={
                  isCritical ? 'critical' : isWarning ? 'warning' : 'healthy'
                }
                size="md"
                dot
              >
                {campaign.status.toUpperCase()}
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-xs text-[#697586] mt-0.5">
              <span className="font-mono text-slate-700 font-semibold">{campaign.id}</span>
              <span>•</span>
              <span>{campaign.channel}</span>
              <span>•</span>
              <span>Created {formatDate(campaign.createdDate)}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {campaign.activeIncidentsCount > 0 && (
            <Button
              variant="danger"
              size="sm"
              onClick={() => navigate('/incidents')}
              icon={<AlertTriangle className="w-3.5 h-3.5" />}
            >
              Active Incident ({campaign.activeIncidentsCount})
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/alerts')}
          >
            View Alerts ({campaign.totalAlertsCount})
          </Button>
        </div>
      </div>

      {/* Metric Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <Card className="p-3.5">
          <span className="text-[11px] font-medium text-[#697586]">Daily Spend</span>
          <div className="text-lg font-bold text-slate-900 mt-1">
            {formatCurrency(campaign.spendToday)}
          </div>
          <span className="text-[10px] text-slate-400">Budget: {formatCurrency(campaign.dailyBudget)}</span>
        </Card>

        <Card className="p-3.5">
          <span className="text-[11px] font-medium text-[#697586]">Clicks Today</span>
          <div className="text-lg font-bold text-slate-900 mt-1">
            {formatNumber(campaign.clicksToday)}
          </div>
          <span className="text-[10px] text-slate-400">Total 180d: {formatNumber(campaign.totalClicks180d)}</span>
        </Card>

        <Card className="p-3.5">
          <span className="text-[11px] font-medium text-[#697586]">Conversions</span>
          <div className={`text-lg font-bold mt-1 ${isCritical ? 'text-rose-600' : 'text-slate-900'}`}>
            {formatNumber(campaign.conversionsToday)}
          </div>
          <span className="text-[10px] text-slate-400">Total 180d: {formatNumber(campaign.totalConversions180d)}</span>
        </Card>

        <Card className="p-3.5">
          <span className="text-[11px] font-medium text-[#697586]">Click-Through (CTR)</span>
          <div className="text-lg font-bold text-slate-900 mt-1">
            {formatPercent(campaign.ctrToday, 2)}
          </div>
          <span className="text-[10px] text-slate-400">180d Avg: {formatPercent(campaign.avgCtr180d, 2)}</span>
        </Card>

        <Card className="p-3.5">
          <span className="text-[11px] font-medium text-[#697586]">Cost per Click</span>
          <div className="text-lg font-bold text-slate-900 mt-1">
            {formatCurrency(campaign.cpcToday)}
          </div>
          <span className="text-[10px] text-slate-400">180d Avg: {formatCurrency(campaign.avgCpc180d)}</span>
        </Card>

        <Card className="p-3.5">
          <span className="text-[11px] font-medium text-[#697586]">Target CPA</span>
          <div className="text-lg font-bold text-slate-900 mt-1">
            {formatCurrency(campaign.targetCpa)}
          </div>
          <span className="text-[10px] text-slate-400">CVR: {formatPercent(campaign.cvrToday, 2)}</span>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#E4E9F1] text-xs font-semibold space-x-6">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 flex items-center gap-2 cursor-pointer transition-colors border-b-2 ${
            activeTab === 'overview'
              ? 'border-[#3867F5] text-[#3867F5]'
              : 'border-transparent text-[#697586] hover:text-[#172033]'
          }`}
        >
          <Activity className="w-4 h-4" />
          Overview & Diagnostics
        </button>
        <button
          onClick={() => setActiveTab('performance')}
          className={`pb-3 flex items-center gap-2 cursor-pointer transition-colors border-b-2 ${
            activeTab === 'performance'
              ? 'border-[#3867F5] text-[#3867F5]'
              : 'border-transparent text-[#697586] hover:text-[#172033]'
          }`}
        >
          <Layers className="w-4 h-4" />
          Full Performance Series
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`pb-3 flex items-center gap-2 cursor-pointer transition-colors border-b-2 ${
            activeTab === 'history'
              ? 'border-[#3867F5] text-[#3867F5]'
              : 'border-transparent text-[#697586] hover:text-[#172033]'
          }`}
        >
          <History className="w-4 h-4" />
          Anomaly History ({alerts.length})
        </button>
        <button
          onClick={() => setActiveTab('config')}
          className={`pb-3 flex items-center gap-2 cursor-pointer transition-colors border-b-2 ${
            activeTab === 'config'
              ? 'border-[#3867F5] text-[#3867F5]'
              : 'border-transparent text-[#697586] hover:text-[#172033]'
          }`}
        >
          <Settings className="w-4 h-4" />
          Detection Configuration
        </button>
      </div>

      {/* Tab 1: Overview & Diagnostics */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Performance Chart with Bands */}
          <Card>
            <TimeSeriesMetricChart
              data={metrics.slice(-30)}
              title={`${campaign.name} — Recent 30-Day Telemetry`}
              subtitle="Observed metric compared with adaptive confidence band (MAD)"
            />
          </Card>

          {/* Diagnostic steps & Recent alerts */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2">
              <CardHeader
                title="Recommended Diagnostic Steps"
                subtitle="Campaign-specific automated triage suggestions"
              />
              <div className="space-y-3 text-xs">
                {isCritical ? (
                  <>
                    <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-900">
                      <p className="font-bold flex items-center gap-1.5 mb-1">
                        <AlertTriangle className="w-4 h-4 text-rose-600" /> 1. Conversion Instrumentation Audit
                      </p>
                      <p className="text-slate-700 leading-relaxed">
                        Conversions are severely disassociated from click traffic. Verify Google Tag Manager / Meta Pixel fires and check the thank-you redirect page for HTTP 404 or JS console errors.
                      </p>
                    </div>
                    <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-800">
                      <p className="font-bold mb-1">2. Pacing & Budget Review</p>
                      <p className="text-slate-600 leading-relaxed">
                        Confirm if daily spend was exhausted ahead of target schedule or if broad targeting bids inflated morning auction costs.
                      </p>
                    </div>
                  </>
                ) : (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900">
                    <p className="font-bold flex items-center gap-1.5 mb-1">
                      <CheckCircle className="w-4 h-4 text-emerald-600" /> Operational Equilibrium Maintained
                    </p>
                    <p className="text-slate-700 leading-relaxed">
                      All monitored metrics (Spend, Clicks, Conversions, CTR, CPC) are tracking inside normal historical tolerance intervals. No manual action required.
                    </p>
                  </div>
                )}
              </div>
            </Card>

            <Card>
              <CardHeader
                title="Recent Campaign Alerts"
                subtitle="Alerts triggered on this campaign"
              />
              {alerts.length === 0 ? (
                <p className="text-xs text-slate-500 py-6 text-center">
                  No anomalous incidents detected for this campaign.
                </p>
              ) : (
                <div className="space-y-2.5">
                  {alerts.slice(0, 3).map((a) => (
                    <div
                      key={a.id}
                      onClick={() => navigate(`/alerts/${a.id}`)}
                      className="p-3 rounded-xl border border-slate-200 hover:border-blue-400 bg-slate-50/50 cursor-pointer transition-all"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <Badge
                          variant={a.severity === 'critical' ? 'critical' : 'warning'}
                          size="sm"
                        >
                          {a.severity}
                        </Badge>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {formatDate(a.firstDetected)}
                        </span>
                      </div>
                      <p className="text-xs font-semibold text-slate-900 line-clamp-1">{a.title}</p>
                      <p className="text-[11px] text-slate-500 mt-1">
                        Deviation: {a.relativeDeviation > 0 ? '+' : ''}{a.relativeDeviation.toFixed(1)}% ({a.anomalyScore} MAD)
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {/* Tab 2: Full Performance Series */}
      {activeTab === 'performance' && (
        <Card>
          <TimeSeriesMetricChart
            data={metrics}
            title={`${campaign.name} — Full 180-Day History`}
            subtitle="Complete baseline and anomaly trajectory"
            height={420}
          />
        </Card>
      )}

      {/* Tab 3: Anomaly History */}
      {activeTab === 'history' && (
        <Card noPadding>
          <div className="p-4 border-b border-[#E4E9F1]">
            <h4 className="text-sm font-semibold text-slate-900">Historical Alert Log</h4>
            <p className="text-xs text-slate-500">Record of all flagged anomalies and resolutions</p>
          </div>
          <div className="divide-y divide-[#E4E9F1]">
            {alerts.map((alt) => (
              <div
                key={alt.id}
                onClick={() => navigate(`/alerts/${alt.id}`)}
                className="p-4 hover:bg-slate-50/80 cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={alt.severity === 'critical' ? 'critical' : 'warning'} size="sm">
                      {alt.severity}
                    </Badge>
                    <span className="font-semibold text-xs text-slate-900">{alt.title}</span>
                  </div>
                  <p className="text-xs text-slate-600">{alt.explanation.whatChanged}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-xs font-mono text-slate-500">{formatDate(alt.firstDetected)}</span>
                  <Button variant="ghost" size="sm" className="text-[#3867F5]">
                    Investigate →
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Tab 4: Configuration */}
      {activeTab === 'config' && (
        <Card>
          <CardHeader
            title="Campaign-Specific Anomaly Detection Settings"
            subtitle="Current active threshold rules and adaptive parameters (Read-Only Demo Mode)"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <span className="font-bold text-slate-900">Baseline Window</span>
              <p className="text-slate-600">
                28 calendar days with day-of-week rolling decomposition
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <span className="font-bold text-slate-900">Sensitivity Threshold</span>
              <p className="text-slate-600">
                3.0 Median Absolute Deviations (MAD) from dynamic median
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <span className="font-bold text-slate-900">Persistence Requirement</span>
              <p className="text-slate-600">
                Minimum 2 consecutive abnormal daily points required before critical escalation
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <span className="font-bold text-slate-900">Deduplication Interval</span>
              <p className="text-slate-600">
                24-hour suppression window to prevent repeated notifications for ongoing incidents
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
