import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  Filter,
  RotateCcw,
  Layers,
  ChevronDown,
  ArrowUpDown,
  ExternalLink,
  AlertOctagon,
} from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { CampaignService } from '../services/campaignService'
import { Campaign, ChannelType, CampaignHealth } from '../types/campaign'
import { formatCurrency, formatNumber, formatPercent, formatDate } from '../utils/formatters'

export const CampaignsPage: React.FC = () => {
  const navigate = useNavigate()
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)

  // Filters state
  const [search, setSearch] = useState('')
  const [channelFilter, setChannelFilter] = useState<string>('all')
  const [verticalFilter, setVerticalFilter] = useState<string>('all')
  const [landingPageFilter, setLandingPageFilter] = useState<string>('all')
  const [healthFilter, setHealthFilter] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'name' | 'spend' | 'clicks' | 'conversions' | 'cvr'>('spend')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 10

  useEffect(() => {
    async function load() {
      try {
        setLoading(true)
        const data = await CampaignService.getCampaigns()
        setCampaigns(data)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Dynamic unique channels and landing pages from dataset
  const channels = useMemo(() => Array.from(new Set(campaigns.map((c) => c.channel))), [campaigns])
  const landingPages = useMemo(
    () => Array.from(new Set(campaigns.map((c) => c.landingPageGroup).filter(Boolean))),
    [campaigns]
  )

  // Filter and sort
  const filteredCampaigns = useMemo(() => {
    let result = [...campaigns]

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (c) => c.name.toLowerCase().includes(q) || c.id.toLowerCase().includes(q)
      )
    }

    if (channelFilter !== 'all') {
      result = result.filter((c) => c.channel === channelFilter)
    }

    if (verticalFilter !== 'all') {
      result = result.filter((c) => c.vertical === verticalFilter)
    }

    if (landingPageFilter !== 'all') {
      result = result.filter((c) => c.landingPageGroup === landingPageFilter)
    }

    if (healthFilter !== 'all') {
      result = result.filter((c) => c.status === healthFilter)
    }

    result.sort((a, b) => {
      const mult = sortOrder === 'desc' ? -1 : 1
      if (sortBy === 'name') return mult * a.name.localeCompare(b.name)
      if (sortBy === 'spend') return mult * (a.spendToday - b.spendToday)
      if (sortBy === 'clicks') return mult * (a.clicksToday - b.clicksToday)
      if (sortBy === 'conversions') return mult * (a.conversionsToday - b.conversionsToday)
      if (sortBy === 'cvr') return mult * (a.cvrToday - b.cvrToday)
      return 0
    })

    return result
  }, [campaigns, search, channelFilter, verticalFilter, landingPageFilter, healthFilter, sortBy, sortOrder])

  // Pagination
  const totalPages = Math.ceil(filteredCampaigns.length / pageSize) || 1
  const paginatedCampaigns = filteredCampaigns.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  )

  const handleResetFilters = () => {
    setSearch('')
    setChannelFilter('all')
    setVerticalFilter('all')
    setLandingPageFilter('all')
    setHealthFilter('all')
    setSortBy('spend')
    setSortOrder('desc')
    setCurrentPage(1)
  }

  const toggleSort = (field: typeof sortBy) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#172033]">Campaign Explorer</h2>
          <p className="text-xs text-[#697586] mt-0.5">
            Monitor, inspect, and evaluate multi-channel performance across all 20 active campaigns (180-Day Chronological Dataset)
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <Card noPadding className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search Input */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by campaign name or ID (e.g. C07, C02)..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setCurrentPage(1)
              }}
              className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#3867F5]"
            />
          </div>

          {/* Channel Dropdown */}
          <div className="flex items-center gap-1.5 bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg px-2.5 py-1 text-xs">
            <span className="text-[#697586] font-medium">Channel:</span>
            <select
              value={channelFilter}
              onChange={(e) => {
                setChannelFilter(e.target.value)
                setCurrentPage(1)
              }}
              className="bg-transparent text-xs font-semibold text-[#172033] focus:outline-none cursor-pointer"
            >
              <option value="all">All Channels</option>
              {channels.map((ch) => (
                <option key={ch} value={ch}>
                  {ch}
                </option>
              ))}
            </select>
          </div>

          {/* Vertical Dropdown */}
          <div className="flex items-center gap-1.5 bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg px-2.5 py-1 text-xs">
            <span className="text-[#697586] font-medium">Vertical:</span>
            <select
              value={verticalFilter}
              onChange={(e) => {
                setVerticalFilter(e.target.value)
                setCurrentPage(1)
              }}
              className="bg-transparent text-xs font-semibold text-[#172033] focus:outline-none cursor-pointer"
            >
              <option value="all">All Verticals</option>
              <option value="ecommerce">E-Commerce</option>
              <option value="b2b">B2B (Lead Gen)</option>
            </select>
          </div>

          {/* Landing Page Group */}
          <div className="flex items-center gap-1.5 bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg px-2.5 py-1 text-xs">
            <span className="text-[#697586] font-medium">LP Group:</span>
            <select
              value={landingPageFilter}
              onChange={(e) => {
                setLandingPageFilter(e.target.value)
                setCurrentPage(1)
              }}
              className="bg-transparent text-xs font-semibold text-[#172033] focus:outline-none cursor-pointer"
            >
              <option value="all">All LP Groups</option>
              {landingPages.map((lp) => (
                <option key={lp} value={lp}>
                  {lp}
                </option>
              ))}
            </select>
          </div>

          {/* Health Filter */}
          <div className="flex items-center gap-1.5 bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg px-2.5 py-1 text-xs">
            <span className="text-[#697586] font-medium">Health:</span>
            <select
              value={healthFilter}
              onChange={(e) => {
                setHealthFilter(e.target.value)
                setCurrentPage(1)
              }}
              className="bg-transparent text-xs font-semibold text-[#172033] focus:outline-none cursor-pointer"
            >
              <option value="all">All Statuses</option>
              <option value="healthy">Healthy</option>
              <option value="warning">Warning</option>
              <option value="critical">Critical</option>
              <option value="investigating">Investigating</option>
            </select>
          </div>

          {/* Reset Filters button */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleResetFilters}
            icon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Reset Filters
          </Button>
        </div>
      </Card>

      {/* Campaigns Table */}
      <Card noPadding>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-[#F5F7FB] text-[#697586] border-b border-[#E4E9F1] font-semibold">
              <tr>
                <th className="py-3 px-4">
                  <button
                    onClick={() => toggleSort('name')}
                    className="flex items-center gap-1 hover:text-[#172033] cursor-pointer"
                  >
                    Campaign <ArrowUpDown className="w-3 h-3" />
                  </button>
                </th>
                <th className="py-3 px-4">Channel</th>
                <th className="py-3 px-4">
                  <button
                    onClick={() => toggleSort('spend')}
                    className="flex items-center gap-1 hover:text-[#172033] cursor-pointer"
                  >
                    Daily Spend <ArrowUpDown className="w-3 h-3" />
                  </button>
                </th>
                <th className="py-3 px-4">
                  <button
                    onClick={() => toggleSort('clicks')}
                    className="flex items-center gap-1 hover:text-[#172033] cursor-pointer"
                  >
                    Clicks <ArrowUpDown className="w-3 h-3" />
                  </button>
                </th>
                <th className="py-3 px-4">
                  <button
                    onClick={() => toggleSort('conversions')}
                    className="flex items-center gap-1 hover:text-[#172033] cursor-pointer"
                  >
                    Conversions <ArrowUpDown className="w-3 h-3" />
                  </button>
                </th>
                <th className="py-3 px-4">
                  <button
                    onClick={() => toggleSort('cvr')}
                    className="flex items-center gap-1 hover:text-[#172033] cursor-pointer"
                  >
                    CVR <ArrowUpDown className="w-3 h-3" />
                  </button>
                </th>
                <th className="py-3 px-4">Health Status</th>
                <th className="py-3 px-4">Active Incidents</th>
                <th className="py-3 px-4">Last Anomaly</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E4E9F1] text-slate-800">
              {paginatedCampaigns.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-500">
                    No campaigns found matching selected filters.
                  </td>
                </tr>
              ) : (
                paginatedCampaigns.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/campaigns/${c.id}`)}
                    className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">{c.name}</div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[10px] text-slate-400 font-mono">{c.id}</span>
                        {c.vertical && (
                          <span
                            className={`text-[9px] font-semibold px-1.5 py-0.2 rounded uppercase ${
                              c.vertical === 'b2b'
                                ? 'bg-purple-50 text-purple-700 border border-purple-200'
                                : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            }`}
                          >
                            {c.vertical}
                          </span>
                        )}
                        {c.landingPageGroup && (
                          <span className="text-[9px] bg-slate-100 text-slate-600 px-1.5 py-0.2 rounded font-mono">
                            {c.landingPageGroup}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium text-[11px]">
                        {c.channel}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-medium">
                      {formatCurrency(c.spendToday)}
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      {formatNumber(c.clicksToday)}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold">
                      {formatNumber(c.conversionsToday)}
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      {formatPercent(c.cvrToday, 2)}
                    </td>
                    <td className="py-3.5 px-4">
                      <Badge
                        variant={
                          c.status === 'healthy'
                            ? 'healthy'
                            : c.status === 'warning'
                            ? 'warning'
                            : c.status === 'critical'
                            ? 'critical'
                            : 'primary'
                        }
                        size="sm"
                        dot
                      >
                        {c.status.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4">
                      {c.activeIncidentsCount > 0 ? (
                        <span className="inline-flex items-center gap-1 font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                          <AlertOctagon className="w-3 h-3" /> {c.activeIncidentsCount} Active
                        </span>
                      ) : (
                        <span className="text-slate-400 font-medium">None</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500">
                      {c.lastAnomalyDate ? formatDate(c.lastAnomalyDate) : 'None'}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          navigate(`/campaigns/${c.id}`)
                        }}
                        className="text-[#3867F5]"
                      >
                        Details →
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
            {Math.min(currentPage * pageSize, filteredCampaigns.length)} of{' '}
            {filteredCampaigns.length} campaigns
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
