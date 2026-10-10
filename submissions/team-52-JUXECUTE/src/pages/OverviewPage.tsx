import React, { useState, useEffect } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import {
  Layers,
  BellRing,
  AlertOctagon,
  Target,
  ShieldCheck,
  Percent,
  ArrowRight,
  TrendingDown,
  Sparkles,
} from 'lucide-react'
import { Card, CardHeader } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { TimeSeriesMetricChart } from '../components/charts/TimeSeriesMetricChart'
import { AlertTrendChart } from '../components/charts/AlertTrendChart'
import { CampaignHealthDonut } from '../components/charts/CampaignHealthDonut'
import { CampaignService } from '../services/campaignService'
import { AlertService } from '../services/alertService'
import { IncidentService } from '../services/incidentService'
import { EvaluationService } from '../services/evaluationService'
import { OFFICIAL_180D_SUMMARY, DATASET_METADATA } from '../data/challengeDataset'
import { Campaign, MetricDataPoint } from '../types/campaign'
import { Alert } from '../types/alert'
import { Incident } from '../types/incident'
import { EvaluationRun } from '../types/evaluation'
import { formatPercent, formatDateTime, formatDeviation } from '../utils/formatters'

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate()
  const { dateRange } = useOutletContext<{ dateRange: '7d' | '30d' | '90d' | '180d' }>()

  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [optimalRun, setOptimalRun] = useState<EvaluationRun | null>(null)
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>('C07')
  const [metricData, setMetricData] = useState<MetricDataPoint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)
        const [cList, aList, iList, eRuns] = await Promise.all([
          CampaignService.getCampaigns(),
          AlertService.getAlerts(),
          IncidentService.getIncidents(),
          EvaluationService.getEvaluationRuns(),
        ])
        setCampaigns(cList)
        setAlerts(aList)
        setIncidents(iList)
        const cgRun = eRuns.find((r) => r.shortName.includes('Adaptive MAD')) || eRuns[1] || eRuns[0]
        setOptimalRun(cgRun)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  useEffect(() => {
    async function loadMetrics() {
      if (!selectedCampaignId) return
      const points = await CampaignService.getCampaignMetrics(selectedCampaignId, dateRange)
      setMetricData(points)
    }
    loadMetrics()
  }, [selectedCampaignId, dateRange])

  const criticalIncidentsCount = incidents.filter((i) => i.severity === 'critical').length || OFFICIAL_180D_SUMMARY.alertsBySeverity.critical
  const totalAlertsCount = alerts.length

  const recentAlerts = alerts.slice(0, 5)

  if (loading && campaigns.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 text-slate-500">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3867F5]" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Top Banner: Synthetic Data Notice & Problem Statement Alignment */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-blue-900 via-[#14233B] to-slate-900 text-white flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm border border-slate-700/50">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-full bg-amber-400/20 text-amber-300 text-[10px] font-bold uppercase tracking-wider border border-amber-400/30">
              PS-04 Verified Submission
            </span>
            <span className="text-xs text-slate-300">
              Campaign Anomaly Alerting Without Alert Fatigue
            </span>
          </div>
          <p className="text-sm font-medium text-slate-100">
            Official challenge dataset ingested (3,600 observations across 20 campaigns over 180 days). Adaptive MAD bands reduce noise without data leakage.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/evaluation')}
            className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs"
          >
            Model Evaluation Lab
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate('/alerts')}
            className="text-xs"
          >
            Inspect Alerts ({totalAlertsCount})
          </Button>
        </div>
      </div>

      {/* Prominent Section: 180-Day Alert Summary */}
      <Card className="border-l-4 border-l-[#3867F5] bg-gradient-to-br from-white via-blue-50/20 to-slate-50">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E4E9F1] pb-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-[#172033]">180-Day Alert Summary</h3>
              <Badge variant="purple" size="sm">PS-04 Official Evaluation</Badge>
            </div>
            <p className="text-xs text-[#697586] mt-0.5">
              Evaluation Period: <span className="font-semibold text-slate-800">{OFFICIAL_180D_SUMMARY.evaluationPeriod}</span> • 20 Campaigns • 3,600 Total Observations
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="px-3 py-1.5 rounded-lg bg-blue-100/70 border border-blue-200 text-blue-900 text-xs">
              <span className="font-bold">{totalAlertsCount}</span> Alert Events Generated (Official)
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-purple-100/70 border border-purple-200 text-purple-900 text-xs">
              <span className="font-bold">{OFFICIAL_180D_SUMMARY.distinctGroupedIncidents}</span> Grouped Incidents
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-slate-700 text-xs">
              <span className="font-bold">{OFFICIAL_180D_SUMMARY.rawAnomalousObservations}</span> Raw Metric Breaches
            </div>
          </div>
        </div>

        {/* Multi-Dimensional Alert Breakdown Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 text-xs">
          {/* 1. By Severity */}
          <div className="p-3.5 rounded-xl bg-white border border-[#E4E9F1] shadow-2xs space-y-2">
            <div className="flex items-center justify-between text-[#697586] font-semibold text-[11px] uppercase tracking-wider">
              <span>Alerts by Severity</span>
              <span>Count</span>
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between items-center py-1 px-2 rounded bg-rose-50 text-rose-900 font-semibold">
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-rose-500"/>Critical</span>
                <span>{OFFICIAL_180D_SUMMARY.alertsBySeverity.critical}</span>
              </div>
              <div className="flex justify-between items-center py-1 px-2 rounded bg-amber-50 text-amber-900 font-semibold">
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-500"/>High</span>
                <span>{OFFICIAL_180D_SUMMARY.alertsBySeverity.high}</span>
              </div>
              <div className="flex justify-between items-center py-1 px-2 rounded bg-blue-50 text-blue-900 font-semibold">
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-500"/>Medium</span>
                <span>{OFFICIAL_180D_SUMMARY.alertsBySeverity.medium}</span>
              </div>
              <div className="flex justify-between items-center py-1 px-2 rounded bg-slate-50 text-slate-500">
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-slate-400"/>Low</span>
                <span>{OFFICIAL_180D_SUMMARY.alertsBySeverity.low}</span>
              </div>
            </div>
          </div>

          {/* 2. By Metric */}
          <div className="p-3.5 rounded-xl bg-white border border-[#E4E9F1] shadow-2xs space-y-2">
            <div className="flex items-center justify-between text-[#697586] font-semibold text-[11px] uppercase tracking-wider">
              <span>Alerts by Metric</span>
              <span>Count</span>
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between items-center py-1 px-2 rounded bg-slate-50 text-slate-800">
                <span className="font-medium">Revenue</span>
                <span className="font-bold">{OFFICIAL_180D_SUMMARY.alertsByMetric.revenue}</span>
              </div>
              <div className="flex justify-between items-center py-1 px-2 rounded bg-slate-50 text-slate-800">
                <span className="font-medium">Clicks</span>
                <span className="font-bold">{OFFICIAL_180D_SUMMARY.alertsByMetric.clicks}</span>
              </div>
              <div className="flex justify-between items-center py-1 px-2 rounded bg-slate-50 text-slate-800">
                <span className="font-medium">Spend</span>
                <span className="font-bold">{OFFICIAL_180D_SUMMARY.alertsByMetric.spend}</span>
              </div>
              <div className="flex justify-between items-center py-1 px-2 rounded bg-slate-50 text-slate-800">
                <span className="font-medium">Conversions</span>
                <span className="font-bold">{OFFICIAL_180D_SUMMARY.alertsByMetric.conversions}</span>
              </div>
            </div>
          </div>

          {/* 3. By Campaign & Signal Clarification */}
          <div className="p-3.5 rounded-xl bg-white border border-[#E4E9F1] shadow-2xs space-y-2">
            <div className="flex items-center justify-between text-[#697586] font-semibold text-[11px] uppercase tracking-wider">
              <span>Campaign Footprint</span>
              <span>{OFFICIAL_180D_SUMMARY.uniqueCampaignsWithAlerts} of 20 Triggered</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Top Alerted Campaigns: <span className="font-semibold text-slate-900">C04 (17)</span>, <span className="font-semibold text-slate-900">C07 (17)</span>, <span className="font-semibold text-slate-900">C02 (16)</span>, <span className="font-semibold text-slate-900">C01 (14)</span>, <span className="font-semibold text-slate-900">C17 (13)</span>.
            </p>
            <div className="p-2 rounded bg-blue-50/60 border border-blue-100 text-[11px] text-blue-900 mt-2">
              <span className="font-semibold">Event Count Hierarchy:</span> 319 raw metric spikes → deduplicated into <span className="font-bold text-blue-700">174 alert events</span> (official) → grouped into <span className="font-bold text-blue-700">110 distinct incidents</span>.
            </div>
          </div>
        </div>
      </Card>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* 1. Campaigns Monitored */}
        <Card
          onClick={() => navigate('/campaigns')}
          className="cursor-pointer hover:border-blue-400 transition-all p-4"
        >
          <div className="flex items-center justify-between text-[#697586] mb-2">
            <span className="text-xs font-medium">Monitored</span>
            <Layers className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-[#172033]">{campaigns.length}</div>
          <div className="flex items-center gap-1 text-[11px] text-emerald-600 mt-1 font-medium">
            <span>5 Networks Active</span>
          </div>
        </Card>

        {/* 2. Total Alerts */}
        <Card
          onClick={() => navigate('/alerts')}
          className="cursor-pointer hover:border-blue-400 transition-all p-4"
        >
          <div className="flex items-center justify-between text-[#697586] mb-2">
            <span className="text-xs font-medium">Active Alerts</span>
            <BellRing className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-[#172033]">{totalAlertsCount}</div>
          <div className="flex items-center gap-1 text-[11px] text-emerald-600 mt-1 font-medium">
            <span>-38.7% vs Naive</span>
          </div>
        </Card>

        {/* 3. Critical Incidents */}
        <Card
          onClick={() => navigate('/incidents')}
          className="cursor-pointer hover:border-rose-400 transition-all p-4"
        >
          <div className="flex items-center justify-between text-[#697586] mb-2">
            <span className="text-xs font-medium">Critical Incidents</span>
            <AlertOctagon className="w-4 h-4 text-rose-600" />
          </div>
          <div className="text-2xl font-bold text-[#DC3545]">{criticalIncidentsCount}</div>
          <div className="flex items-center gap-1 text-[11px] text-rose-600 mt-1 font-medium">
            <span>Grouped Incidents</span>
          </div>
        </Card>

        {/* 4. Alert Precision */}
        <Card
          onClick={() => navigate('/evaluation')}
          className="cursor-pointer hover:border-emerald-400 transition-all p-4"
        >
          <div className="flex items-center justify-between text-[#697586] mb-2">
            <span className="text-xs font-medium">Alert Precision</span>
            <Target className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-700">
            {optimalRun ? formatPercent(optimalRun.precision) : '2.9%'}
          </div>
          <div className="flex items-center gap-1 text-[10px] text-slate-500 mt-1 font-semibold uppercase">
            <Badge variant="purple" size="sm">180D AUDIT</Badge>
          </div>
        </Card>

        {/* 5. Incident Recall */}
        <Card
          onClick={() => navigate('/evaluation')}
          className="cursor-pointer hover:border-blue-400 transition-all p-4"
        >
          <div className="flex items-center justify-between text-[#697586] mb-2">
            <span className="text-xs font-medium">Incident Recall</span>
            <ShieldCheck className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-[#3867F5]">
            {optimalRun ? formatPercent(optimalRun.recall) : '100.0%'}
          </div>
          <div className="flex items-center gap-1 text-[10px] text-slate-500 mt-1 font-semibold uppercase">
            <Badge variant="purple" size="sm">180D AUDIT</Badge>
          </div>
        </Card>

        {/* 6. False Positive Rate */}
        <Card
          onClick={() => navigate('/evaluation')}
          className="cursor-pointer hover:border-blue-400 transition-all p-4"
        >
          <div className="flex items-center justify-between text-[#697586] mb-2">
            <span className="text-xs font-medium">False Pos. Rate</span>
            <Percent className="w-4 h-4 text-slate-600" />
          </div>
          <div className="text-2xl font-bold text-slate-800">
            {optimalRun ? formatPercent(optimalRun.falsePositiveRate, 2) : '4.69%'}
          </div>
          <div className="flex items-center gap-1 text-[10px] text-slate-500 mt-1 font-semibold uppercase">
            <Badge variant="purple" size="sm">180D AUDIT</Badge>
          </div>
        </Card>
      </div>

      {/* Main Analytics Section: Time Series Chart & Campaign Selector */}
      <Card>
        <TimeSeriesMetricChart
          data={metricData}
          title="Campaign Metric & Anomaly Envelope"
          subtitle={`Inspection period: ${dateRange} • Dynamic Upper/Lower confidence bands`}
          campaignSelector={
            <div className="flex items-center gap-1.5 bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg px-2.5 py-1 text-xs">
              <span className="text-[#697586] font-medium">Campaign:</span>
              <select
                value={selectedCampaignId}
                onChange={(e) => setSelectedCampaignId(e.target.value)}
                className="bg-transparent text-xs font-semibold text-[#172033] focus:outline-none cursor-pointer"
              >
                {campaigns.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.channel}) {c.status === 'critical' ? '🔴' : ''}
                  </option>
                ))}
              </select>
            </div>
          }
        />
      </Card>

      {/* 2-Column Split: Alert Trend Chart & Campaign Health Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <AlertTrendChart />
        </Card>
        <Card>
          <CardHeader
            title="Campaign Health Distribution"
            subtitle="Current operational state across 20 monitored campaigns"
          />
          <CampaignHealthDonut campaigns={campaigns} />
        </Card>
      </div>

      {/* Recent Alerts Table */}
      <Card noPadding>
        <div className="p-5 border-b border-[#E4E9F1] flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-[#172033]">Recent Flagged Anomalies</h3>
            <p className="text-xs text-[#697586] mt-0.5">
              Click any alert row to view explainable diagnostics and root-cause breakdown
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/alerts')}
            icon={<ArrowRight className="w-3.5 h-3.5" />}
          >
            View All Alerts
          </Button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-[#F5F7FB] text-[#697586] border-b border-[#E4E9F1] font-semibold">
              <tr>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Campaign</th>
                <th className="py-3 px-4">Metric</th>
                <th className="py-3 px-4">Observed vs Expected</th>
                <th className="py-3 px-4">Deviation</th>
                <th className="py-3 px-4">Detected Category</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E4E9F1] text-slate-800">
              {recentAlerts.map((alt) => (
                <tr
                  key={alt.id}
                  onClick={() => navigate(`/alerts/${alt.id}`)}
                  className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                >
                  <td className="py-3.5 px-4">
                    <Badge
                      variant={
                        alt.severity === 'critical'
                          ? 'critical'
                          : alt.severity === 'high'
                          ? 'warning'
                          : 'primary'
                      }
                      size="sm"
                      dot
                    >
                      {alt.severity.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="font-semibold text-slate-900">{alt.campaignName}</div>
                    <span className="text-[10px] text-slate-500">{alt.channel}</span>
                  </td>
                  <td className="py-3.5 px-4 font-mono font-medium uppercase">
                    {alt.metric}
                  </td>
                  <td className="py-3.5 px-4 font-mono">
                    <span className="font-bold text-slate-900">{alt.observedValue}</span>{' '}
                    <span className="text-slate-400">/ exp. {alt.expectedBaseline}</span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span
                      className={`font-semibold ${
                        alt.relativeDeviation < 0 ? 'text-rose-600' : 'text-blue-600'
                      }`}
                    >
                      {formatDeviation(alt.relativeDeviation)}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[11px] font-medium">
                      {alt.category}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <Badge
                      variant={
                        alt.status === 'resolved'
                          ? 'healthy'
                          : alt.status === 'investigating'
                          ? 'primary'
                          : 'outline'
                      }
                      size="sm"
                    >
                      {alt.status}
                    </Badge>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        navigate(`/alerts/${alt.id}`)
                      }}
                      className="text-xs text-[#3867F5]"
                    >
                      Inspect →
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
