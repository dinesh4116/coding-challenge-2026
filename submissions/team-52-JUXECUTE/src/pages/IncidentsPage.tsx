import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertOctagon,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Layers,
  Sparkles,
} from 'lucide-react'
import { Card, CardHeader } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { IncidentService } from '../services/incidentService'
import { Incident, IncidentStatus } from '../types/incident'
import { formatCurrency, formatDate } from '../utils/formatters'
import { useToast } from '../components/ui/ToastContext'

export const IncidentsPage: React.FC = () => {
  const navigate = useNavigate()
  const toast = useToast()

  const [incidents, setIncidents] = useState<Incident[]>([])
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null)
  const [loading, setLoading] = useState(true)

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [search, setSearch] = useState('')

  useEffect(() => {
    async function load() {
      try {
        setLoading(true)
        const list = await IncidentService.getIncidents()
        setIncidents(list)
        if (list.length > 0) {
          setSelectedIncident(list[0])
        }
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const filteredIncidents = incidents.filter((inc) => {
    if (search.trim()) {
      const q = search.toLowerCase()
      const match =
        inc.title.toLowerCase().includes(q) ||
        inc.campaignName.toLowerCase().includes(q) ||
        inc.id.toLowerCase().includes(q)
      if (!match) return false
    }
    if (categoryFilter !== 'all' && inc.category !== categoryFilter) return false
    if (statusFilter !== 'all' && inc.status !== statusFilter) return false
    return true
  })

  const handleUpdateStatus = async (status: IncidentStatus) => {
    if (!selectedIncident) return
    const updated = await IncidentService.updateIncidentStatus(selectedIncident.id, status)
    if (updated) {
      setSelectedIncident(updated)
      setIncidents((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
      toast.success(`Incident status updated to ${status.toUpperCase()}`)
    }
  }

  const categories = [
    'Possible Conversion Tracking Failure',
    'Shared Landing Page Outage',
    'Campaign Delivery Halt / Account Pause',
    'Traffic Surge / Bidding Disruption',
    'Promotional / Seasonal Flash Event',
    'Budget Exhaustion',
    'Performance Degradation',
    'Unknown Anomaly',
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#172033]">Incident Analysis & Diagnostics</h2>
          <p className="text-xs text-[#697586] mt-0.5">
            {incidents.length} Distinct Grouped Incidents across the 180-day challenge period (fatigue-reduced multi-day & shared-LP clusters)
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="purple" size="sm">
            Deterministic Rule Engine Active
          </Badge>
        </div>
      </div>

      {/* Filter Bar */}
      <Card noPadding className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search incidents by name, campaign, or ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#3867F5]"
            />
          </div>

          <div className="flex items-center gap-1.5 bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg px-2.5 py-1 text-xs">
            <span className="text-[#697586] font-medium">Category:</span>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-transparent text-xs font-semibold text-[#172033] focus:outline-none cursor-pointer max-w-xs truncate"
            >
              <option value="all">All Incident Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5 bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg px-2.5 py-1 text-xs">
            <span className="text-[#697586] font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-transparent text-xs font-semibold text-[#172033] focus:outline-none cursor-pointer"
            >
              <option value="all">All Statuses</option>
              <option value="active">Active</option>
              <option value="investigating">Investigating</option>
              <option value="resolved">Resolved</option>
              <option value="suppressed">Suppressed (Noise Filter)</option>
            </select>
          </div>
        </div>
      </Card>

      {/* 2-Column Layout: Incident Master List & Detailed Investigation Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Incidents List */}
        <div className="lg:col-span-5 space-y-3">
          {filteredIncidents.length === 0 ? (
            <Card className="text-center py-12 text-xs text-slate-500">
              No incidents match the active search criteria.
            </Card>
          ) : (
            filteredIncidents.map((inc) => {
              const isSelected = selectedIncident?.id === inc.id
              return (
                <div
                  key={inc.id}
                  onClick={() => setSelectedIncident(inc)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer bg-white ${
                    isSelected
                      ? 'border-[#3867F5] ring-2 ring-blue-100 shadow-sm'
                      : 'border-[#E4E9F1] hover:border-slate-300 shadow-2xs'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <Badge
                      variant={
                        inc.severity === 'critical'
                          ? 'critical'
                          : inc.severity === 'high'
                          ? 'warning'
                          : inc.isSuppressedSeasonal
                          ? 'healthy'
                          : 'primary'
                      }
                      size="sm"
                      dot
                    >
                      {inc.severity.toUpperCase()}
                    </Badge>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {formatDate(inc.startDate)}
                    </span>
                  </div>

                  <h4 className="text-xs font-bold text-slate-900 line-clamp-1">{inc.title}</h4>
                  <p className="text-[11px] text-slate-500 mt-0.5 truncate">{inc.campaignName}</p>

                  <div className="mt-2.5 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px]">
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium truncate max-w-[200px]">
                      {inc.category}
                    </span>
                    <span className="font-semibold text-slate-600 uppercase text-[10px]">
                      {inc.status}
                    </span>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Right Column: Detailed Investigation Panel */}
        <div className="lg:col-span-7">
          {selectedIncident ? (
            <Card className="space-y-5">
              {/* Incident Header */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pb-4 border-b border-[#E4E9F1]">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge
                      variant={
                        selectedIncident.severity === 'critical'
                          ? 'critical'
                          : selectedIncident.severity === 'high'
                          ? 'warning'
                          : 'primary'
                      }
                      size="sm"
                    >
                      {selectedIncident.severity.toUpperCase()}
                    </Badge>
                    <span className="text-xs font-mono text-slate-500">
                      {selectedIncident.id}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900">{selectedIncident.title}</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Target Campaign: <span className="font-semibold text-slate-800">{selectedIncident.campaignName}</span> ({selectedIncident.channel})
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {selectedIncident.status !== 'resolved' && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleUpdateStatus('resolved')}
                      icon={<CheckCircle2 className="w-3.5 h-3.5" />}
                    >
                      Resolve Incident
                    </Button>
                  )}
                  {selectedIncident.status === 'resolved' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleUpdateStatus('active')}
                    >
                      Reopen
                    </Button>
                  )}
                </div>
              </div>

              {/* Classification & Evidence Callout */}
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 space-y-2 text-xs">
                <div className="flex items-center justify-between text-slate-800 font-bold">
                  <span className="flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-[#3867F5]" /> Operational Diagnosis
                  </span>
                  <Badge variant="purple" size="sm">
                    {selectedIncident.category}
                  </Badge>
                </div>
                <p className="text-slate-700 leading-relaxed font-medium">
                  {selectedIncident.classificationRationale}
                </p>
              </div>

              {/* Observed Evidence Summary */}
              <div className="space-y-1.5 text-xs">
                <span className="font-bold text-slate-900 uppercase tracking-wider text-[10px]">
                  Observed Telemetry Evidence
                </span>
                <div className="p-3 bg-white rounded-lg border border-slate-200 text-slate-700 leading-relaxed">
                  {selectedIncident.evidenceSummary}
                </div>
              </div>

              {/* Recommended Investigation Step */}
              <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl space-y-1 text-xs">
                <span className="font-bold text-[#1E40AF] uppercase tracking-wider text-[10px] flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#3867F5]" /> Recommended Investigation Step
                </span>
                <p className="text-[#1E3A8A] font-medium leading-relaxed">
                  {selectedIncident.recommendedInvestigationStep}
                </p>
              </div>

              {/* Metric Impact & Est Cost */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-slate-500 text-[11px]">Affected Metrics</span>
                  <div className="flex items-center gap-1.5 mt-1">
                    {selectedIncident.affectedMetrics.map((m) => (
                      <span key={m} className="px-2 py-0.5 bg-slate-200 font-mono rounded text-[11px] font-semibold text-slate-800">
                        {m.toUpperCase()}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-slate-500 text-[11px]">Est. Cost / Exposure</span>
                  <div className="text-sm font-bold text-slate-900 mt-1">
                    {formatCurrency(selectedIncident.estimatedCostImpact)}
                  </div>
                </div>
              </div>

              {/* Related Alerts */}
              {selectedIncident.relatedAlertIds.length > 0 && (
                <div className="space-y-2 text-xs">
                  <span className="font-bold text-slate-900 uppercase tracking-wider text-[10px]">
                    Correlated Alerts ({selectedIncident.relatedAlertIds.length})
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {selectedIncident.relatedAlertIds.map((aid) => (
                      <button
                        key={aid}
                        onClick={() => navigate(`/alerts/${aid}`)}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#F5F7FB] border border-[#E4E9F1] hover:border-blue-400 text-xs font-mono font-medium text-slate-800 cursor-pointer"
                      >
                        <span>{aid}</span>
                        <ExternalLink className="w-3 h-3 text-slate-400" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Timeline */}
              <div className="space-y-2 text-xs pt-2 border-t border-[#E4E9F1]">
                <span className="font-bold text-slate-900 uppercase tracking-wider text-[10px]">
                  Incident Timeline
                </span>
                <div className="space-y-2">
                  {selectedIncident.timeline.map((t, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-slate-600">
                      <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-mono text-[11px] text-slate-500 font-medium">{t.date}:</span>{' '}
                        <span>{t.note}</span>
                        {t.actor && (
                          <span className="text-[10px] text-slate-400 ml-1">({t.actor})</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          ) : (
            <Card className="text-center py-20 text-xs text-slate-500">
              Select an incident to view investigation details.
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
