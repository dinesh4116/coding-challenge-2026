import React, { useState, useMemo } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  Search,
  Filter,
  CheckCircle2,
  ChevronRight,
  FileSpreadsheet,
  FileText,
  ArrowUpDown,
  ExternalLink,
  ChevronLeft,
  X
} from 'lucide-react';
import { useData } from '../../context/DataContext';
import { AnomalyAlert, Severity, AlertStatus } from '../../types/dashboard';
import { exportToCSV } from '../../utils/csvParser';

export const AlertsView: React.FC = () => {
  const {
    alerts,
    updateAlertStatus,
    campaignSummaries,
    setSelectedCampaign,
    setActiveTab,
    activeAlertModal,
    setActiveAlertModal
  } = useData();

  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [campaignFilter, setCampaignFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [filterActionableOnly, setFilterActionableOnly] = useState<boolean>(true); // DEFAULT: ONLY NECESSARY ACTIONABLE ALERTS
  const [sortField, setSortField] = useState<'date' | 'severity' | 'score' | 'change'>('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Filtered and Sorted Alerts
  const filteredAlerts = useMemo(() => {
    return alerts.filter(alert => {
      // By default, show only necessary alerts (critical & high actionable incidents)
      if (filterActionableOnly && alert.severity !== 'critical' && alert.severity !== 'high') {
        return false;
      }

      const matchesSearch =
        alert.campaign.toLowerCase().includes(searchTerm.toLowerCase()) ||
        alert.explanation.toLowerCase().includes(searchTerm.toLowerCase()) ||
        alert.metric.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesSeverity = severityFilter === 'all' || alert.severity === severityFilter;
      const matchesCampaign = campaignFilter === 'all' || alert.campaign === campaignFilter;
      const matchesStatus = statusFilter === 'all' || alert.status === statusFilter;

      return matchesSearch && matchesSeverity && matchesCampaign && matchesStatus;
    }).sort((a, b) => {
      let comparison = 0;
      if (sortField === 'date') {
        comparison = a.date.localeCompare(b.date);
      } else if (sortField === 'severity') {
        const severityRank = { critical: 4, high: 3, medium: 2, low: 1 };
        comparison = severityRank[a.severity] - severityRank[b.severity];
      } else if (sortField === 'score') {
        comparison = a.anomalyScore - b.anomalyScore;
      } else if (sortField === 'change') {
        comparison = Math.abs(a.percentChange) - Math.abs(b.percentChange);
      }
      return sortOrder === 'desc' ? -comparison : comparison;
    });
  }, [alerts, searchTerm, severityFilter, campaignFilter, statusFilter, filterActionableOnly, sortField, sortOrder]);

  // Pagination
  const totalPages = Math.ceil(filteredAlerts.length / pageSize) || 1;
  const paginatedAlerts = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredAlerts.slice(start, start + pageSize);
  }, [filteredAlerts, currentPage]);

  const handleExportAlertsCSV = () => {
    const rows = filteredAlerts.map(a => ({
      Alert_ID: a.id,
      Date: a.date,
      Campaign: a.campaign,
      Severity: a.severity.toUpperCase(),
      Category: a.category,
      Metric: a.metric,
      Observed_Value: a.observedValue,
      Expected_Baseline: a.expectedBaseline,
      Percent_Change: `${a.percentChange}%`,
      Anomaly_Score: a.anomalyScore,
      Status: a.status,
      Explanation: a.explanation
    }));
    exportToCSV(`campaign_alerts_${new Date().toISOString().split('T')[0]}.csv`, rows);
  };

  const handleExportRCAReport = () => {
    const dateStr = new Date().toISOString().split('T')[0];
    const reportContent = `# Incident Root Cause Analysis (RCA) Report
**Date:** ${dateStr}  
**Incidents Logged:** ${filteredAlerts.length}  

---

${filteredAlerts.map((a, idx) => `
### ${idx + 1}. [${a.severity.toUpperCase()}] ${a.campaign} (${a.date})
- **Metric:** ${a.metric} (Observed: ${a.observedValue} | Expected Baseline: ${a.expectedBaseline} | Change: ${a.percentChange}%)
- **Diagnosis:** ${a.explanation}
- **Status:** ${a.status.toUpperCase()}
- **Playbook Steps:**
${a.diagnosticSteps.map(s => `  - ${s}`).join('\n')}
`).join('\n')}
`;

    const blob = new Blob([reportContent], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `incident_rca_${dateStr}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const actionableCount = alerts.filter(a => a.severity === 'critical' || a.severity === 'high').length;

  return (
    <div className="space-y-4">
      {/* Header & Controls */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-base font-bold text-slate-900 tracking-tight">Active Alerts</h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
              {filteredAlerts.length} Showing
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Filtered to display necessary actionable campaign anomalies
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Priority Toggle: Only Necessary Alerts vs All Signals */}
          <div className="bg-slate-100 p-0.5 rounded-lg border border-slate-200 flex text-xs font-medium">
            <button
              onClick={() => { setFilterActionableOnly(true); setCurrentPage(1); }}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                filterActionableOnly
                  ? 'bg-white text-indigo-600 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Actionable Only ({actionableCount})
            </button>
            <button
              onClick={() => { setFilterActionableOnly(false); setCurrentPage(1); }}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                !filterActionableOnly
                  ? 'bg-white text-indigo-600 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All Signals ({alerts.length})
            </button>
          </div>

          <button
            onClick={handleExportRCAReport}
            className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-300 font-medium text-xs rounded-lg transition-colors flex items-center space-x-1.5"
            title="Export Markdown RCA Report"
          >
            <FileText className="w-3.5 h-3.5 text-slate-500" />
            <span>RCA Report</span>
          </button>
          <button
            onClick={handleExportAlertsCSV}
            className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs rounded-lg transition-colors flex items-center space-x-1.5"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5">
          {/* Search */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search..."
              value={searchTerm}
              onChange={e => { setSearchTerm(e.target.value); setCurrentPage(1); }}
              className="w-full pl-8 pr-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Severity */}
          <div className="flex items-center space-x-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={severityFilter}
              onChange={e => { setSeverityFilter(e.target.value); setCurrentPage(1); }}
              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Campaign */}
          <div>
            <select
              value={campaignFilter}
              onChange={e => { setCampaignFilter(e.target.value); setCurrentPage(1); }}
              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="all">All Campaigns ({campaignSummaries.length})</option>
              {campaignSummaries.map(s => (
                <option key={s.campaign} value={s.campaign}>{s.campaign}</option>
              ))}
            </select>
          </div>

          {/* Status */}
          <div>
            <select
              value={statusFilter}
              onChange={e => { setStatusFilter(e.target.value); setCurrentPage(1); }}
              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="all">All Statuses</option>
              <option value="new">New (Unresolved)</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100/70 text-slate-600 font-semibold border-b border-slate-200 uppercase text-[11px]">
              <tr>
                <th className="py-2.5 px-3.5 cursor-pointer" onClick={() => { setSortField('severity'); setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc'); }}>
                  <div className="flex items-center space-x-1">
                    <span>Severity</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th className="py-2.5 px-3.5 cursor-pointer" onClick={() => { setSortField('date'); setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc'); }}>
                  <div className="flex items-center space-x-1">
                    <span>Date</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th className="py-2.5 px-3.5">Campaign</th>
                <th className="py-2.5 px-3.5">Metric & Deviation</th>
                <th className="py-2.5 px-3.5">Diagnosis</th>
                <th className="py-2.5 px-3.5">Status</th>
                <th className="py-2.5 px-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-slate-700">
              {paginatedAlerts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-slate-400">
                    <CheckCircle2 className="w-7 h-7 text-slate-300 mx-auto mb-1.5" />
                    <p className="font-semibold text-slate-600 text-xs">No active alerts matching filter</p>
                    <p className="text-[11px]">All monitored campaigns within normal bounds.</p>
                  </td>
                </tr>
              ) : (
                paginatedAlerts.map(alert => (
                  <tr key={alert.id} className="hover:bg-slate-50/80 transition-colors">
                    {/* Severity Badge */}
                    <td className="py-3 px-3.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        alert.severity === 'critical'
                          ? 'bg-rose-100 text-rose-800 border border-rose-200'
                          : alert.severity === 'high'
                          ? 'bg-amber-100 text-amber-800 border border-amber-200'
                          : alert.severity === 'medium'
                          ? 'bg-yellow-100 text-yellow-800 border border-yellow-200'
                          : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                      }`}>
                        {alert.severity.toUpperCase()}
                      </span>
                    </td>

                    {/* Date */}
                    <td className="py-3 px-3.5 font-mono text-slate-600 whitespace-nowrap text-[11px]">
                      {alert.date}
                    </td>

                    {/* Campaign Name */}
                    <td className="py-3 px-3.5 font-semibold text-slate-900 max-w-xs truncate" title={alert.campaign}>
                      {alert.campaign}
                    </td>

                    {/* Metric & Deviation */}
                    <td className="py-3 px-3.5 whitespace-nowrap">
                      <span className="font-mono font-bold text-slate-900">{alert.metric}</span>
                      <span className={`ml-1.5 text-[11px] font-bold ${
                        alert.percentChange < 0 ? 'text-rose-600' : 'text-emerald-600'
                      }`}>
                        {alert.percentChange > 0 ? `+${alert.percentChange}%` : `${alert.percentChange}%`}
                      </span>
                    </td>

                    {/* Diagnosis */}
                    <td className="py-3 px-3.5 max-w-sm text-slate-600 truncate text-[11px]" title={alert.explanation}>
                      {alert.explanation}
                    </td>

                    {/* Status */}
                    <td className="py-3 px-3.5 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        alert.status === 'new'
                          ? 'bg-rose-50 text-rose-700 border border-rose-200'
                          : alert.status === 'acknowledged'
                          ? 'bg-blue-50 text-blue-700 border border-blue-200'
                          : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      }`}>
                        {alert.status.toUpperCase()}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-3.5 text-right whitespace-nowrap">
                      <button
                        onClick={() => setActiveAlertModal(alert)}
                        className="px-2.5 py-1 rounded bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold text-[11px] transition-colors inline-flex items-center space-x-1"
                      >
                        <span>Inspect</span>
                        <ChevronRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-3 border-t border-slate-200/80 flex items-center justify-between text-xs text-slate-500 bg-slate-50/50">
          <div>
            Showing <span className="font-semibold text-slate-900">{paginatedAlerts.length}</span> of <span className="font-semibold text-slate-900">{filteredAlerts.length}</span> alerts
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1 rounded border border-slate-300 bg-white disabled:opacity-40 hover:bg-slate-50 transition-colors"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="font-medium text-slate-700 text-[11px]">Page {currentPage} of {totalPages}</span>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1 rounded border border-slate-300 bg-white disabled:opacity-40 hover:bg-slate-50 transition-colors"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Alert Details Playbook Modal */}
      {activeAlertModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full border border-slate-200 shadow-xl overflow-hidden flex flex-col max-h-[85vh]">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-200 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <div className={`p-2 rounded-lg ${
                  activeAlertModal.severity === 'critical' ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/20 text-amber-400'
                }`}>
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-sm text-white">{activeAlertModal.campaign}</h3>
                  <p className="text-[11px] text-slate-400 font-mono">{activeAlertModal.date} • {activeAlertModal.id}</p>
                </div>
              </div>
              <button
                onClick={() => setActiveAlertModal(null)}
                className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 overflow-y-auto space-y-4 text-xs">
              {/* Quick Metric Stat Chips */}
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Observed vs Expected</span>
                  <p className="font-bold text-slate-900 text-xs mt-0.5">{activeAlertModal.observedValue} vs {activeAlertModal.expectedBaseline}</p>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Deviation</span>
                  <p className={`font-bold text-xs mt-0.5 ${activeAlertModal.percentChange < 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                    {activeAlertModal.percentChange > 0 ? `+${activeAlertModal.percentChange}%` : `${activeAlertModal.percentChange}%`}
                  </p>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Classification</span>
                  <p className="font-bold text-indigo-700 text-xs mt-0.5 uppercase">{activeAlertModal.category.replace('_', ' ')}</p>
                </div>
              </div>

              {/* Plain-English Explanation */}
              <div>
                <h4 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider mb-1.5">Anomaly Diagnosis</h4>
                <div className="p-3 bg-indigo-50/70 border border-indigo-150 rounded-lg text-xs text-indigo-950 leading-relaxed">
                  {activeAlertModal.explanation}
                </div>
              </div>

              {/* Diagnostic Checklist */}
              <div>
                <h4 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider mb-2">Recommended First Steps</h4>
                <div className="space-y-1.5">
                  {activeAlertModal.diagnosticSteps.map((step, idx) => (
                    <div key={idx} className="flex items-start space-x-2 p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-800">
                      <span className="w-4 h-4 rounded-full bg-indigo-600 text-white font-bold text-[9px] flex items-center justify-center flex-shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-3.5 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
              <button
                onClick={() => {
                  setSelectedCampaign(activeAlertModal.campaign);
                  setActiveAlertModal(null);
                  setActiveTab('analysis');
                }}
                className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 font-semibold text-xs rounded-lg transition-colors flex items-center space-x-1"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>View Bands</span>
              </button>

              <div className="flex items-center space-x-2">
                {activeAlertModal.status !== 'acknowledged' && (
                  <button
                    onClick={() => updateAlertStatus(activeAlertModal.id, 'acknowledged')}
                    className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg shadow-xs transition-colors"
                  >
                    Acknowledge
                  </button>
                )}
                {activeAlertModal.status !== 'resolved' && (
                  <button
                    onClick={() => updateAlertStatus(activeAlertModal.id, 'resolved')}
                    className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-lg shadow-xs transition-colors"
                  >
                    Resolve
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
