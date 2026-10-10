import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  ShieldAlert,
  LayoutDashboard,
  Layers,
  BellRing,
  AlertOctagon,
  BarChart3,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Database,
  User,
  X,
  LogOut,
} from 'lucide-react'
import { DATASET_METADATA } from '../../mocks/demoData'
import { useAuth } from '../../auth/AuthContext'

interface SidebarProps {
  isCollapsed: boolean
  setIsCollapsed: (collapsed: boolean) => void
  isMobileOpen: boolean
  setIsMobileOpen: (open: boolean) => void
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  setIsCollapsed,
  isMobileOpen,
  setIsMobileOpen,
}) => {
  const { user, logout } = useAuth()
  const navItems = [
    { name: 'Overview', path: '/', icon: LayoutDashboard },
    { name: 'Campaign Explorer', path: '/campaigns', icon: Layers },
    { name: 'Alerts Center', path: '/alerts', icon: BellRing, badge: '5' },
    { name: 'Incident Analysis', path: '/incidents', icon: AlertOctagon, badge: '3' },
    { name: 'Model Evaluation', path: '/evaluation', icon: BarChart3 },
    { name: 'Reports', path: '/reports', icon: FileText },
    { name: 'Settings', path: '/settings', icon: Settings },
  ]

  const sidebarContent = (
    <div className="flex flex-col h-full bg-[#14233B] text-slate-300 border-r border-[#1e3458] select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-[#1e3458]">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-9 h-9 rounded-xl bg-[#3867F5] flex items-center justify-center text-white shrink-0 shadow-md shadow-blue-900/40">
            <ShieldAlert className="w-5 h-5 text-white" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col truncate">
              <span className="font-bold text-white tracking-tight text-sm leading-tight">
                CampaignGuard<span className="text-[#3867F5]">AI</span>
              </span>
              <span className="text-[10px] text-slate-400 font-medium tracking-wider uppercase">
                Anomaly Alerting
              </span>
            </div>
          )}
        </div>

        {/* Mobile close button */}
        <button
          onClick={() => setIsMobileOpen(false)}
          className="md:hidden text-slate-400 hover:text-white p-1 rounded-lg"
          aria-label="Close menu"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 py-4 px-3 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
          {!isCollapsed && 'Monitoring Suite'}
        </div>
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => setIsMobileOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all group ${
                  isActive
                    ? 'bg-[#3867F5] text-white shadow-xs font-semibold'
                    : 'text-slate-300 hover:bg-[#1c2f4e] hover:text-white'
                }`
              }
              title={isCollapsed ? item.name : undefined}
            >
              <Icon className="w-4 h-4 shrink-0 transition-transform group-hover:scale-105" />
              {!isCollapsed && (
                <div className="flex-1 flex items-center justify-between">
                  <span className="truncate">{item.name}</span>
                  {item.badge && (
                    <span className="bg-rose-500/90 text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </NavLink>
          )
        })}
      </div>

      {/* Dataset / Demo Status pill */}
      {!isCollapsed && (
        <div className="mx-3 mb-3 p-3 rounded-xl bg-[#0f1b2f] border border-[#1e3458]/70">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-300 mb-1">
            <Database className="w-3.5 h-3.5 text-[#3867F5]" />
            <span>Dataset Status</span>
          </div>
          <p className="text-[11px] text-amber-400 font-medium flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            Synthetic Demo (180d)
          </p>
          <p className="text-[10px] text-slate-400 mt-1">
            {DATASET_METADATA.campaignCount} Campaigns • 3,600 Obs
          </p>
        </div>
      )}

      {/* User profile & Collapse controls */}
      <div className="p-3 border-t border-[#1e3458] bg-[#0f1b2f]/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#3867F5] to-indigo-600 border border-blue-400/30 flex items-center justify-center shrink-0 text-white font-semibold text-xs shadow-xs">
              {user?.name
                ? user.name
                    .split(' ')
                    .map((n) => n[0])
                    .join('')
                    .slice(0, 2)
                    .toUpperCase()
                : <User className="w-4 h-4 text-slate-200" />}
            </div>
            {!isCollapsed && (
              <div className="truncate">
                <div className="flex items-center gap-1.5">
                  <p className="text-xs font-medium text-white truncate">
                    {user?.name || 'Evaluator User'}
                  </p>
                  {user?.isDemoUser && (
                    <span className="text-[9px] px-1 py-0.2 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded font-semibold">
                      DEMO
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-400 truncate">
                  {user?.role || 'Evaluation Analyst'}
                </p>
              </div>
            )}
          </div>

          <div className="flex items-center gap-1">
            {!isCollapsed && (
              <button
                onClick={logout}
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                title="Sign out"
                aria-label="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="hidden md:flex p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#1e3458] transition-colors cursor-pointer"
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? (
                <ChevronRight className="w-4 h-4" />
              ) : (
                <ChevronLeft className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop fixed sidebar */}
      <aside
        className={`hidden md:block shrink-0 transition-all duration-200 h-screen sticky top-0 z-30 ${
          isCollapsed ? 'w-18' : 'w-64'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile drawer backdrop */}
      {isMobileOpen && (
        <div
          className="md:hidden fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-40 transition-opacity"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Mobile drawer */}
      <aside
        className={`md:hidden fixed top-0 bottom-0 left-0 w-72 z-50 transform transition-transform duration-200 ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebarContent}
      </aside>
    </>
  )
}
