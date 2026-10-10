import React from 'react';
import {
  LayoutDashboard,
  AlertTriangle,
  LineChart,
  FileBarChart2,
  Settings,
  ShieldCheck,
  UploadCloud
} from 'lucide-react';
import { useData } from '../../context/DataContext';
import { ActiveTab } from '../../types/dashboard';

export const Sidebar: React.FC = () => {
  const { activeTab, setActiveTab, alerts, metadata } = useData();

  // Highlight only necessary actionable alerts
  const criticalCount = alerts.filter(a => a.severity === 'critical' && a.status === 'new').length;
  const highCount = alerts.filter(a => a.severity === 'high' && a.status === 'new').length;
  const actionableCount = criticalCount + highCount;

  const navItems: { id: ActiveTab; label: string; icon: React.ReactNode; badge?: number; badgeColor?: string }[] = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
    {
      id: 'alerts',
      label: 'Incident Alerts',
      icon: <AlertTriangle className="w-4 h-4" />,
      badge: actionableCount > 0 ? actionableCount : undefined,
      badgeColor: criticalCount > 0 ? 'bg-rose-500' : 'bg-amber-500'
    },
    { id: 'analysis', label: 'Anomaly Bands', icon: <LineChart className="w-4 h-4" /> },
    { id: 'reports', label: 'Model Evaluation', icon: <FileBarChart2 className="w-4 h-4" /> },
    { id: 'campaigns', label: 'Data Ingestion', icon: <UploadCloud className="w-4 h-4" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <aside className="w-60 bg-slate-900 text-slate-300 flex flex-col flex-shrink-0 min-h-screen border-r border-slate-800 shadow-lg z-20">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800/80 flex items-center space-x-3">
        <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-md shadow-indigo-600/30 text-white font-bold">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-bold text-white text-base leading-tight tracking-tight">ZeroSec</h1>
          <p className="text-[10px] text-slate-400 font-medium">Anomaly Intelligence</p>
        </div>
      </div>

      {/* Dataset Info Chip */}
      <div className="mx-3 mt-3.5 mb-2 p-2.5 bg-slate-800/60 rounded-lg border border-slate-700/50">
        <div className="flex items-center justify-between text-[11px] mb-1">
          <span className="text-slate-400">Dataset</span>
          <span className="text-[10px] text-emerald-400 font-semibold px-1.5 py-0.5 bg-emerald-500/10 rounded">
            {metadata?.rowCount ? `${metadata.rowCount.toLocaleString()} rows` : 'Loaded'}
          </span>
        </div>
        <p className="text-[11px] text-slate-200 font-mono truncate" title={metadata?.filename || ''}>
          {metadata?.filename || 'Active Dataset'}
        </p>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-3 space-y-1">
        <div className="px-2 mb-1.5 text-[10px] font-semibold tracking-wider text-slate-500 uppercase">
          Navigation
        </div>
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-indigo-600 text-white font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <span className={isActive ? 'text-white' : 'text-slate-400'}>{item.icon}</span>
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && (
                <span className={`px-1.5 py-0.5 text-[10px] font-bold text-white rounded-full ${item.badgeColor}`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800/80 text-[11px] text-slate-500 flex items-center justify-between">
        <span>System Status</span>
        <span className="flex items-center gap-1.5 text-emerald-400 text-[10px] font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
          Operational
        </span>
      </div>
    </aside>
  );
};
