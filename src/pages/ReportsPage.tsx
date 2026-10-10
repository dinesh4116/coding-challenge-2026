import React, { useState, useEffect } from 'react'
import {
  FileText,
  Download,
  Printer,
  Sparkles,
  BarChart,
  Layers,
  ShieldAlert,
  CheckCircle,
} from 'lucide-react'
import { Card, CardHeader } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { ReportService, ReportSummaryData } from '../services/reportService'
import { AlertService } from '../services/alertService'
import { EvaluationService } from '../services/evaluationService'
import { formatCurrency, formatNumber, formatPercent } from '../utils/formatters'
import { useToast } from '../components/ui/ToastContext'

export const ReportsPage: React.FC = () => {
  const toast = useToast()
  const [summary, setSummary] = useState<ReportSummaryData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        setLoading(true)
        const s = await ReportService.getSummaryReport()
        setSummary(s)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handlePrint = () => {
    window.print()
  }

  const handleExportAlerts = async () => {
    const alerts = await AlertService.getAlerts()
    ReportService.exportAlertsCsv(alerts)
    toast.success('Alerts report CSV exported!')
  }

  const handleExportEvaluation = async () => {
    const runs = await EvaluationService.getEvaluationRuns()
    ReportService.exportEvaluationCsv(runs)
    toast.success('Model evaluation benchmarks CSV exported!')
  }

  if (loading || !summary) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3867F5]" />
        <p className="text-xs text-slate-500">Compiling executive marketing report...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 no-print">
        <div>
          <h2 className="text-xl font-bold text-[#172033]">Marketing & Anomaly Audit Reports</h2>
          <p className="text-xs text-[#697586] mt-0.5">
            Full-period 180-day executive performance summary and operational alert audit
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportAlerts}
            icon={<Download className="w-3.5 h-3.5" />}
          >
            Export Alerts CSV
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleExportEvaluation}
            icon={<Download className="w-3.5 h-3.5" />}
          >
            Export Benchmarks CSV
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handlePrint}
            icon={<Printer className="w-3.5 h-3.5" />}
          >
            Print Executive Report
          </Button>
        </div>
      </div>

      {/* Printable Report Header */}
      <div className="p-6 bg-white border border-[#E4E9F1] rounded-2xl shadow-xs space-y-6">
        <div className="flex items-center justify-between border-b border-slate-200 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-black text-lg text-slate-900 tracking-tight">
                CampaignGuard AI
              </span>
              <Badge variant="purple" size="sm">
                Executive Audit Report
              </Badge>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Dataset Period: {summary.evaluationPeriod}
            </p>
          </div>
          <div className="text-right text-xs text-slate-500">
            <div>Generated: October 10, 2026</div>
            <div className="font-semibold text-slate-700">Analyst: Marcus Vance</div>
          </div>
        </div>

        {/* 180-Day Alert Summary Section */}
        <div className="p-4 rounded-xl border border-blue-200 bg-blue-50/30 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-blue-100 pb-2">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                180-Day Alert Summary
                <Badge variant="purple" size="sm">Official Count</Badge>
              </h3>
              <p className="text-[11px] text-slate-600">
                Evaluation Window: {summary.evaluationPeriod} • 20 Campaigns • 3,600 Observations
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-bold text-blue-900 bg-blue-100 px-2 py-0.5 rounded border border-blue-200">
                {summary.totalAlerts} Alert Events Generated
              </span>
              <span className="font-bold text-purple-900 bg-purple-100 px-2 py-0.5 rounded border border-purple-200">
                {summary.distinctGroupedIncidents} Grouped Incidents
              </span>
              <span className="font-medium text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                {summary.rawAnomalousObservations} Raw Spikes
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs pt-1">
            <div className="p-2.5 rounded-lg bg-white border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-bold">Severity Breakdown</span>
              <div className="text-slate-800 font-semibold mt-1 space-y-0.5 text-[11px]">
                <div className="flex justify-between"><span>Critical:</span><span className="text-rose-600 font-bold">{summary.alertsBySeverity.critical || 0}</span></div>
                <div className="flex justify-between"><span>High:</span><span className="text-amber-600 font-bold">{summary.alertsBySeverity.high || 0}</span></div>
                <div className="flex justify-between"><span>Medium:</span><span className="text-blue-600 font-bold">{summary.alertsBySeverity.medium || 0}</span></div>
                <div className="flex justify-between"><span>Low:</span><span className="text-slate-400">{summary.alertsBySeverity.low || 0}</span></div>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-white border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-bold">Metric Breakdown</span>
              <div className="text-slate-800 font-semibold mt-1 space-y-0.5 text-[11px]">
                <div className="flex justify-between"><span>Revenue:</span><span className="font-bold">57</span></div>
                <div className="flex justify-between"><span>Clicks:</span><span className="font-bold">48</span></div>
                <div className="flex justify-between"><span>Spend:</span><span className="font-bold">40</span></div>
                <div className="flex justify-between"><span>Conversions:</span><span className="font-bold">29</span></div>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-white border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-bold">Top Campaign Alerts</span>
              <div className="text-slate-800 font-semibold mt-1 space-y-0.5 text-[11px]">
                <div className="flex justify-between"><span>C04 Google:</span><span className="font-bold">17</span></div>
                <div className="flex justify-between"><span>C07 Meta:</span><span className="font-bold">17</span></div>
                <div className="flex justify-between"><span>C02 Google:</span><span className="font-bold">16</span></div>
                <div className="flex justify-between"><span>C01 Google:</span><span className="font-bold">14</span></div>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-white border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-bold">Signal Governance</span>
              <p className="text-[11px] text-slate-600 mt-1 leading-snug">
                17 of 20 campaigns triggered alerts. Deduplication reduced alert noise by 38.7% compared to naive static bands.
              </p>
            </div>
          </div>
        </div>

        {/* Executive Metric Summary Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-medium text-slate-500">Total Ad Spend Monitored</span>
            <div className="text-xl font-bold text-slate-900 mt-1">
              {formatCurrency(summary.totalSpend)}
            </div>
            <span className="text-[10px] text-slate-400">20 Campaigns (180 Days)</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-medium text-slate-500">Total Traffic Delivered</span>
            <div className="text-xl font-bold text-slate-900 mt-1">
              {formatNumber(summary.totalClicks)} Clicks
            </div>
            <span className="text-[10px] text-slate-400">CTR ~ {formatPercent(summary.overallCtr, 2)}</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-medium text-slate-500">Total Conversions</span>
            <div className="text-xl font-bold text-slate-900 mt-1">
              {formatNumber(summary.totalConversions)}
            </div>
            <span className="text-[10px] text-slate-400">Blended CPA: {formatCurrency(summary.overallCpa)}</span>
          </div>

          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200">
            <span className="text-[11px] font-bold text-emerald-800">Alert Fatigue Reduction</span>
            <div className="text-xl font-black text-emerald-700 mt-1">
              -{summary.alertReduction.toFixed(1)}%
            </div>
            <span className="text-[10px] text-emerald-600 font-semibold">vs Naive Baseline (284)</span>
          </div>
        </div>

        {/* 2-Column Split: Alerts Breakdown & Category Triage */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          {/* Alerts by Severity */}
          <div className="p-4 rounded-xl border border-slate-200 space-y-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Alert Volume by Severity Tier
            </h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center p-2 rounded-lg bg-rose-50 text-rose-900 font-semibold">
                <span>Critical Incidents</span>
                <span>{summary.alertsBySeverity.critical || 0} alerts</span>
              </div>
              <div className="flex justify-between items-center p-2 rounded-lg bg-amber-50 text-amber-900 font-semibold">
                <span>High Severity</span>
                <span>{summary.alertsBySeverity.high || 0} alerts</span>
              </div>
              <div className="flex justify-between items-center p-2 rounded-lg bg-blue-50 text-blue-900 font-semibold">
                <span>Medium Warnings</span>
                <span>{summary.alertsBySeverity.medium || 0} alerts</span>
              </div>
              <div className="flex justify-between items-center p-2 rounded-lg bg-slate-50 text-slate-700">
                <span>Low / Informational</span>
                <span>{summary.alertsBySeverity.low || 0} alerts</span>
              </div>
            </div>
          </div>

          {/* Alerts by Category */}
          <div className="p-4 rounded-xl border border-slate-200 space-y-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Alert Volume by Operational Category
            </h4>
            <div className="space-y-2 text-xs">
              {Object.entries(summary.alertsByCategory).map(([cat, count]) => (
                <div
                  key={cat}
                  className="flex justify-between items-center p-2 rounded-lg bg-slate-50 text-slate-800 font-medium"
                >
                  <span className="truncate pr-2">{cat}</span>
                  <span className="font-bold shrink-0">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Model Evaluation Summary Table */}
        <div className="pt-2">
          <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2">
            Detector Quality & Benchmark Evaluation (180 Days)
          </h4>
          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="p-3">Evaluation Metric</th>
                  <th className="p-3">CampaignGuard Adaptive MAD</th>
                  <th className="p-3">Fixed Baseline (Naive ±20%)</th>
                  <th className="p-3">Net Operational Gain</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                <tr>
                  <td className="p-3 font-semibold">Total Alerts Fired</td>
                  <td className="p-3 font-bold text-blue-600">{summary.totalAlerts} alerts</td>
                  <td className="p-3 text-rose-600 font-bold">284 alerts</td>
                  <td className="p-3 text-emerald-700 font-bold">110 fewer alerts (-38.7% noise reduction)</td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold">Incident Recall (5 Verified Clusters)</td>
                  <td className="p-3 font-bold text-emerald-600">{formatPercent(summary.bestRecall)}</td>
                  <td className="p-3 text-slate-700 font-medium">100.0%</td>
                  <td className="p-3 text-emerald-700 font-medium">Zero missed incidents</td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold">Candidate Precision</td>
                  <td className="p-3 font-bold text-slate-900">{formatPercent(summary.bestPrecision)}</td>
                  <td className="p-3 text-slate-500">1.8%</td>
                  <td className="p-3 text-emerald-700 font-bold">+61% relative precision gain</td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold">Non-Cluster Flagged Obs</td>
                  <td className="p-3 font-bold text-slate-900">169 alerts</td>
                  <td className="p-3 text-rose-600 font-bold">279 alerts</td>
                  <td className="p-3 text-emerald-700 font-bold">110 false alarms suppressed</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
