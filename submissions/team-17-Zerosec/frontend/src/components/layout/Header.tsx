import React from 'react';
import {
  Calendar,
  Bell,
  RefreshCw,
  UploadCloud
} from 'lucide-react';
import { useData } from '../../context/DataContext';

export const Header: React.FC = () => {
  const {
    activeTab,
    setActiveTab,
    selectedDateRange,
    setSelectedDateRange,
    alerts,
    handleResetData,
    isLoading
  } = useData();

  // Count only critical & high severity unresolved alerts
  const actionableAlerts = alerts.filter(
    a => a.status === 'new' && (a.severity === 'critical' || a.severity === 'high')
  );

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-6 py-3.5 flex items-center justify-between">
        {/* Left Title */}
        <div className="flex items-center space-x-3">
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                Campaign Intelligence
              </h2>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                Active Monitoring
              </span>
            </div>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center space-x-3">
          {/* Date Range Selector */}
          <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-medium">
            <Calendar className="w-3.5 h-3.5 ml-2 mr-1 text-slate-500" />
            <button
              onClick={() => setSelectedDateRange('all')}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                selectedDateRange === 'all'
                  ? 'bg-white text-indigo-600 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All Time
            </button>
            <button
              onClick={() => setSelectedDateRange('90d')}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                selectedDateRange === '90d'
                  ? 'bg-white text-indigo-600 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              90 Days
            </button>
            <button
              onClick={() => setSelectedDateRange('30d')}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                selectedDateRange === '30d'
                  ? 'bg-white text-indigo-600 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              30 Days
            </button>
          </div>

          {/* Upload CSV */}
          <button
            onClick={() => setActiveTab('campaigns')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all ${
              activeTab === 'campaigns'
                ? 'bg-indigo-600 text-white shadow-indigo-200'
                : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 hover:border-slate-400'
            }`}
          >
            <UploadCloud className={`w-3.5 h-3.5 ${activeTab === 'campaigns' ? 'text-white' : 'text-indigo-600'}`} />
            <span>Import CSV</span>
          </button>

          {/* Reset / Reload Button */}
          <button
            onClick={handleResetData}
            disabled={isLoading}
            className="p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors border border-slate-200"
            title="Refresh Dataset"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-indigo-600' : ''}`} />
          </button>

          {/* Notification Bell */}
          <button
            onClick={() => setActiveTab('alerts')}
            className="relative p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors border border-slate-200"
            title="Active Incidents"
          >
            <Bell className="w-3.5 h-3.5" />
            {actionableAlerts.length > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-rose-500 text-white font-bold text-[9px] rounded-full flex items-center justify-center animate-pulse">
                {actionableAlerts.length}
              </span>
            )}
          </button>

          {/* Profile */}
          <div className="flex items-center pl-2 border-l border-slate-200 space-x-2">
            <div className="w-7 h-7 rounded-full bg-slate-900 text-white font-semibold text-xs flex items-center justify-center shadow-sm">
              AD
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
