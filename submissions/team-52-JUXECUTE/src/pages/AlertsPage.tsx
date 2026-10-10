import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  RotateCcw,
  BellRing,
  ArrowUpDown,
  Filter,
  CheckCircle2,
  Clock,
  Sparkles,
  ExternalLink,
  Download,
} from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { AlertService } from '../services/alertService'
import { ReportService } from '../services/reportService'
import { Alert, AlertSeverity, AlertStatus, MetricType } from '../types/alert'
import { formatDeviation, formatDate } from '../utils/formatters'
import { useToast } from '../components/ui/ToastContext'

export const AlertsPage: React.FC = () => {
  const navigate = useNavigate()
  const toast = useToast()

  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)

  // Filter States
  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [metricFilter, setMetricFilter] = useState<string>('all')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'severity' | 'deviation'>('newest')
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 10

  const loadAlerts = async () => {
    try {
      setLoading(true)
      const data = await AlertService.getAlerts()
      setAlerts(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAlerts()
  }, [])

  // Filter logic
  const filteredAlerts = useMemo(() => {
    let result = [...alerts]

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (a) =>
          (a.title || '').toLowerCase().includes(q) ||
          (a.campaignName || '').toLowerCase().includes(q) ||
          (a.id || '').toLowerCase().includes(q)
      )
    }

    if (severityFilter !== 'all') {
      result = result.filter((a) => a.severity === severityFilter)
    }

    if (statusFilter !== 'all') {
      result = result.filter((a) => a.status === statusFilter)
    }

    if (metricFilter !== 'all') {
      result = result.filter((a) => a.metric === metricFilter)
    }

    if (categoryFilter !== 'all') {
      result = result.filter((a) => a.category === categoryFilter)
    }

    // Sort
    result.sort((a, b) => {
      if (sortBy === 'newest') {
        return new Date(b.firstDetected).getTime() - new Date(a.firstDetected).getTime()
      }
      if (sortBy === 'oldest') {
        return new Date(a.firstDetected).getTime() - new Date(b.firstDetected).getTime()
      }
      if (sortBy === 'severity') {
        const order: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 }
        return (order[b.severity] || 0) - (order[a.severity] || 0)
      }
      if (sortBy === 'deviation') {
        return Math.abs(b.relativeDeviation) - Math.abs(a.relativeDeviation)
      }
      return 0
    })

    return result
  }, [alerts, search, severityFilter, statusFilter, metricFilter, categoryFilter, sortBy])

  const totalPages = Math.ceil(filteredAlerts.length / pageSize) || 1
  const paginatedAlerts = filteredAlerts.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  )

  const handleResetFilters = () => {
    setSearch('')
    setSeverityFilter('all')
    setStatusFilter('all')
    setMetricFilter('all')
    setCategoryFilter('all')
    setSortBy('newest')
    setCurrentPage(1)
    toast.info('Alert filters reset')
  }

  const handleExportCsv = () => {
    ReportService.exportAlertsCsv(filteredAlerts)
    toast.success(`Exported ${filteredAlerts.length} alerts to CSV`)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#172033]">Alerts Center</h2>
          <p className="text-xs text-[#697586] mt-0.5">
            Showing {filteredAlerts.length} of {alerts.length} generated alert events across the 180-day challenge period (Official Count: 174)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCsv}
            icon={<Download className="w-3.5 h-3.5" />}
          >
            Export Filtered CSV
          </Button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <Card noPadding className="p-4">
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search alerts or campaigns..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setCurrentPage(1)
              }}
              className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#3867F5]"
            />
          </div>

          {/* Severity */}
          <div className="flex items-center gap-1.5 bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg px-2.5 py-1 text-xs">
            <span className="text-[#697586] font-medium">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value)
                setCurrentPage(1)
              }}
              className="bg-transparent text-xs font-semibold text-[#172033] focus:outline-none cursor-pointer"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Status */}
          <div className="flex items-center gap-1.5 bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg px-2.5 py-1 text-xs">
            <span className="text-[#697586] font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setCurrentPage(1)
              }}
              className="bg-transparent text-xs font-semibold text-[#172033] focus:outline-none cursor-pointer"
            >
              <option value="all">All Statuses</option>
              <option value="new">New</option>
              <option value="investigating">Investigating</option>
              <option value="resolved">Resolved</option>
              <option value="dismissed">Dismissed</option>
            </select>
          </div>

          {/* Metric */}
          <div className="flex items-center gap-1.5 bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg px-2.5 py-1 text-xs">
            <span className="text-[#697586] font-medium">Metric:</span>
            <select
              value={metricFilter}
              onChange={(e) => {
                setMetricFilter(e.target.value)
                setCurrentPage(1)
              }}
              className="bg-transparent text-xs font-semibold text-[#172033] focus:outline-none cursor-pointer"
            >
              <option value="all">All Metrics</option>
              <option value="revenue">Revenue</option>
              <option value="clicks">Clicks</option>
              <option value="spend">Spend</option>
              <option value="conversions">Conversions</option>
              <option value="cpc">CPC</option>
              <option value="ctr">CTR</option>
              <option value="cvr">CVR</option>
            </select>
          </div>

          {/* Sort By */}
          <div className="flex items-center gap-1.5 bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg px-2.5 py-1 text-xs">
            <span className="text-[#697586] font-medium">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-transparent text-xs font-semibold text-[#172033] focus:outline-none cursor-pointer"
            >
              <option value="newest">Newest First</option>
              <option value="severity">Highest Severity</option>
              <option value="deviation">Largest Deviation</option>
              <option value="oldest">Oldest First</option>
            </select>
          </div>

          {/* Reset Filters */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleResetFilters}
            icon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Reset
          </Button>
        </div>
      </Card>

      {/* Alert List Table */}
      <Card noPadding>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-[#F5F7FB] text-[#697586] border-b border-[#E4E9F1] font-semibold">
              <tr>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Alert Title</th>
                <th className="py-3 px-4">Campaign</th>
                <th className="py-3 px-4">Metric</th>
                <th className="py-3 px-4">Observed vs Expected</th>
                <th className="py-3 px-4">Deviation</th>
                <th className="py-3 px-4">Score (MAD)</th>
                <th className="py-3 px-4">First Detected</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E4E9F1] text-slate-800">
              {paginatedAlerts.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-500">
                    No alerts match the active filters.
                  </td>
                </tr>
              ) : (
                paginatedAlerts.map((alt) => (
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
                    <td className="py-3.5 px-4 max-w-xs">
                      <div className="font-semibold text-slate-900 line-clamp-1">{alt.title}</div>
                      <span className="text-[10px] text-slate-400 font-mono">{alt.id}</span>
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
                      <span className="text-slate-400">/ {alt.expectedBaseline}</span>
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
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-700">
                      {alt.anomalyScore.toFixed(1)}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500">
                      <div>{formatDate(alt.firstDetected)}</div>
                      <span className="text-[10px] text-slate-400">{alt.durationDays}d duration</span>
                    </td>
                    <td className="py-3.5 px-4">
                      <Badge
                        variant={
                          alt.status === 'resolved'
                            ? 'healthy'
                            : alt.status === 'investigating'
                            ? 'primary'
                            : alt.status === 'dismissed'
                            ? 'neutral'
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
                        className="text-[#3867F5]"
                      >
                        Investigate →
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Table Pagination */}
        <div className="p-4 border-t border-[#E4E9F1] flex items-center justify-between text-xs text-[#697586]">
          <div>
            Showing {(currentPage - 1) * pageSize + 1} to{' '}
            {Math.min(currentPage * pageSize, filteredAlerts.length)} of{' '}
            {filteredAlerts.length} alerts
          </div>
          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </Button>
            <span className="px-2 font-medium">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            >
              Next
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
