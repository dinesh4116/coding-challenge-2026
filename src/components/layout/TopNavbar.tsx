import React, { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  Menu,
  Search,
  Calendar,
  Bell,
  Sparkles,
  ExternalLink,
  ChevronDown,
  CheckCircle,
  LogOut,
  Settings as SettingsIcon,
  Shield,
  User as UserIcon,
} from 'lucide-react'
import { Badge } from '../ui/Badge'
import { INITIAL_ALERTS } from '../../mocks/demoData'
import { useAuth } from '../../auth/AuthContext'
import { useToast } from '../ui/ToastContext'

interface TopNavbarProps {
  onMobileMenuToggle: () => void
  selectedDateRange: string
  onDateRangeChange: (range: string) => void
}

export const TopNavbar: React.FC<TopNavbarProps> = ({
  onMobileMenuToggle,
  selectedDateRange,
  onDateRangeChange,
}) => {
  const location = useLocation()
  const navigate = useNavigate()
  const toast = useToast()
  const { user, logout } = useAuth()

  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [isNotificationOpen, setIsNotificationOpen] = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    toast.info('Signed out of CampaignGuard AI')
    navigate('/login')
  }

  // Map route to page title & breadcrumbs
  const getPageInfo = () => {
    const p = location.pathname
    if (p === '/') return { title: 'Campaign Overview', breadcrumb: 'Dashboard' }
    if (p.startsWith('/campaigns/')) return { title: 'Campaign Detail', breadcrumb: 'Campaign Explorer / Detail' }
    if (p === '/campaigns') return { title: 'Campaign Explorer', breadcrumb: 'Campaigns' }
    if (p.startsWith('/alerts/')) return { title: 'Alert Investigation', breadcrumb: 'Alerts Center / Detail' }
    if (p === '/alerts') return { title: 'Alerts Center', breadcrumb: 'Alert Management' }
    if (p === '/incidents') return { title: 'Incident Analysis', breadcrumb: 'Diagnostics & Root Cause' }
    if (p === '/evaluation') return { title: 'Model Evaluation Lab', breadcrumb: 'Evaluation & Benchmarks' }
    if (p === '/reports') return { title: 'Reports & Export', breadcrumb: 'Performance Reports' }
    if (p === '/settings') return { title: 'System Settings', breadcrumb: 'Configuration' }
    return { title: 'CampaignGuard AI', breadcrumb: 'Home' }
  }

  const { title, breadcrumb } = getPageInfo()

  const recentAlerts = INITIAL_ALERTS.slice(0, 4)

  return (
    <header className="sticky top-0 z-20 bg-white border-b border-[#E4E9F1] px-4 md:px-6 h-16 flex items-center justify-between shadow-2xs">
      {/* Left: Mobile hamburger & breadcrumb */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMobileMenuToggle}
          className="md:hidden p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-[#697586]">
            <span>CampaignGuard</span>
            <span>/</span>
            <span className="text-[#172033] font-semibold">{breadcrumb}</span>
          </div>
          <h1 className="text-base md:text-lg font-bold text-[#172033] tracking-tight leading-tight">
            {title}
          </h1>
        </div>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-2.5 md:gap-3">
        {/* Synthetic Demo Indicator with hover tooltip */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold select-none group relative cursor-help">
          <Sparkles className="w-3.5 h-3.5 text-amber-600 animate-pulse" />
          <span>Demo Data (180d)</span>

          {/* Hover Tooltip */}
          <div className="absolute right-0 top-full mt-1.5 w-64 p-3 bg-slate-900 text-white text-xs rounded-xl shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-50">
            <p className="font-semibold text-amber-400 mb-1">Demonstration Mode</p>
            <p className="text-slate-300 text-[11px] leading-relaxed">
              Displaying realistic synthetic campaign metrics with seeded ground-truth anomalies. Connect a live Python FastAPI backend in Settings.
            </p>
          </div>
        </div>

        {/* Global Date Range selector */}
        <div className="relative">
          <div className="flex items-center gap-1 bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg px-2.5 py-1.5 text-xs font-medium text-[#172033]">
            <Calendar className="w-3.5 h-3.5 text-[#697586]" />
            <select
              value={selectedDateRange}
              onChange={(e) => onDateRangeChange(e.target.value)}
              className="bg-transparent border-none text-xs font-medium text-[#172033] focus:outline-none cursor-pointer pr-1"
              aria-label="Date range selector"
            >
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
              <option value="180d">Full 180 Days</option>
            </select>
          </div>
        </div>

        {/* Quick Search Trigger */}
        <div className="relative">
          <button
            onClick={() => setIsSearchOpen(!isSearchOpen)}
            className="flex items-center gap-2 px-2.5 py-1.5 text-xs text-[#697586] bg-[#F5F7FB] hover:bg-slate-100 border border-[#E4E9F1] rounded-lg transition-colors cursor-pointer"
            aria-label="Search campaigns and alerts"
          >
            <Search className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Search...</span>
            <kbd className="hidden md:inline text-[10px] bg-white border border-slate-200 px-1.5 py-0.5 rounded text-slate-500 font-mono">
              Ctrl+K
            </kbd>
          </button>

          {/* Quick Search Dropdown */}
          {isSearchOpen && (
            <div className="absolute right-0 mt-2 w-72 sm:w-80 bg-white border border-[#E4E9F1] rounded-xl shadow-xl p-3 z-50 animate-in fade-in zoom-in-95 duration-100">
              <div className="relative mb-2">
                <Search className="w-4 h-4 absolute left-2.5 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search campaigns, alerts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  autoFocus
                  className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#3867F5]"
                />
              </div>

              <div className="space-y-1 max-h-48 overflow-y-auto">
                <div className="text-[10px] font-semibold text-slate-400 uppercase px-2 py-1">
                  Quick Navigation
                </div>
                <button
                  onClick={() => {
                    navigate('/campaigns')
                    setIsSearchOpen(false)
                  }}
                  className="w-full text-left px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-100 rounded-md flex items-center justify-between cursor-pointer"
                >
                  <span>All Campaigns</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </button>
                <button
                  onClick={() => {
                    navigate('/alerts')
                    setIsSearchOpen(false)
                  }}
                  className="w-full text-left px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-100 rounded-md flex items-center justify-between cursor-pointer"
                >
                  <span>Active Alerts (5)</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </button>
                <button
                  onClick={() => {
                    navigate('/evaluation')
                    setIsSearchOpen(false)
                  }}
                  className="w-full text-left px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-100 rounded-md flex items-center justify-between cursor-pointer"
                >
                  <span>Model Evaluation Lab</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Notification Bell Dropdown */}
        <div className="relative">
          <button
            onClick={() => setIsNotificationOpen(!isNotificationOpen)}
            className="relative p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label="View notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500 animate-ping" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500" />
          </button>

          {/* Notifications Flyout */}
          {isNotificationOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-white border border-[#E4E9F1] rounded-xl shadow-xl overflow-hidden z-50 animate-in fade-in duration-100">
              <div className="p-3 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-900">
                  Recent Anomaly Alerts
                </span>
                <Badge variant="critical" size="sm">
                  {recentAlerts.length} Unresolved
                </Badge>
              </div>
              <div className="divide-y divide-slate-100 max-h-72 overflow-y-auto">
                {recentAlerts.map((alt) => (
                  <Link
                    key={alt.id}
                    to={`/alerts/${alt.id}`}
                    onClick={() => setIsNotificationOpen(false)}
                    className="p-3 block hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] font-semibold text-slate-900 truncate">
                        {alt.campaignName}
                      </span>
                      <Badge
                        variant={alt.severity === 'critical' ? 'critical' : 'warning'}
                        size="sm"
                      >
                        {alt.severity}
                      </Badge>
                    </div>
                    <p className="text-[11px] text-slate-600 line-clamp-1">{alt.title}</p>
                    <p className="text-[10px] text-slate-400 mt-1">
                      Score: {alt.anomalyScore} MAD • {alt.metric.toUpperCase()}
                    </p>
                  </Link>
                ))}
              </div>
              <div className="p-2.5 bg-slate-50 border-t border-slate-100 text-center">
                <Link
                  to="/alerts"
                  onClick={() => setIsNotificationOpen(false)}
                  className="text-xs font-medium text-[#3867F5] hover:underline"
                >
                  View All Alerts in Center →
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* User Profile dropdown */}
        <div className="relative pl-2 border-l border-[#E4E9F1]">
          <button
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            className="flex items-center gap-2 p-1 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer select-none"
            aria-label="User profile menu"
          >
            <div className="w-8 h-8 rounded-full bg-[#14233B] text-white font-bold text-xs flex items-center justify-center border border-slate-700 shadow-2xs">
              {user?.avatarInitials || 'CG'}
            </div>
            <div className="hidden sm:block text-left text-xs leading-tight">
              <span className="font-semibold text-slate-900 block max-w-[120px] truncate">
                {user?.name || 'Ad Ops Analyst'}
              </span>
              <span className="text-[10px] text-slate-500 block">
                {user?.isDemoUser ? 'Demo Access' : 'Analyst'}
              </span>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
          </button>

          {/* User Menu Flyout */}
          {isUserMenuOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-white border border-[#E4E9F1] rounded-xl shadow-xl p-3 z-50 animate-in fade-in zoom-in-95 duration-100 space-y-3">
              <div className="pb-2 border-b border-slate-100">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-8 h-8 rounded-full bg-[#14233B] text-white font-bold text-xs flex items-center justify-center">
                    {user?.avatarInitials || 'CG'}
                  </div>
                  <div className="truncate">
                    <p className="font-bold text-xs text-slate-900 truncate">
                      {user?.name || 'Ad Ops Analyst'}
                    </p>
                    <p className="text-[11px] text-slate-500 font-mono truncate">
                      {user?.email || 'analyst@campaignguard.ai'}
                    </p>
                  </div>
                </div>
                <div className="mt-2">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                      user?.isDemoUser
                        ? 'bg-amber-100 text-amber-800 border border-amber-200'
                        : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    }`}
                  >
                    {user?.isDemoUser ? 'PS-04 Hackathon Demo Access' : 'Authenticated Analyst'}
                  </span>
                </div>
              </div>

              <div className="space-y-1 text-xs">
                <button
                  onClick={() => {
                    navigate('/settings')
                    setIsUserMenuOpen(false)
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded-md hover:bg-slate-100 text-slate-700 flex items-center gap-2 cursor-pointer transition-colors"
                >
                  <SettingsIcon className="w-3.5 h-3.5 text-slate-400" />
                  <span>System Settings</span>
                </button>
                <button
                  onClick={() => {
                    navigate('/evaluation')
                    setIsUserMenuOpen(false)
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded-md hover:bg-slate-100 text-slate-700 flex items-center gap-2 cursor-pointer transition-colors"
                >
                  <Shield className="w-3.5 h-3.5 text-slate-400" />
                  <span>Model Evaluation Lab</span>
                </button>
              </div>

              <div className="pt-2 border-t border-slate-100">
                <button
                  onClick={handleLogout}
                  className="w-full px-2.5 py-2 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 font-semibold text-xs flex items-center justify-center gap-2 cursor-pointer transition-colors border border-rose-200/60"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
