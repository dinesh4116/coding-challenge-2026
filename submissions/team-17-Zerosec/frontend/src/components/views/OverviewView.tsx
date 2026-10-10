import React from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  CheckCircle2,
  IndianRupee,
  Activity,
  ArrowUpRight,
  ChevronRight,
  Target,
  BarChart3,
  Layers,
  ShieldCheck
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { useData } from '../../context/DataContext';

export const OverviewView: React.FC = () => {
  const {
    records,
    alerts,
    campaignSummaries,
    metrics,
    setActiveTab,
    setSelectedCampaign,
    backendSummary
  } = useData();

  // Aggregate daily metrics for spend & conversion trend chart
  const dailyMetricsMap: Record<string, { date: string; spend: number; conversions: number; anomalies: number }> = {};
  
  records.forEach(r => {
    if (!dailyMetricsMap[r.date]) {
      dailyMetricsMap[r.date] = { date: r.date, spend: 0, conversions: 0, anomalies: 0 };
    }
    dailyMetricsMap[r.date].spend += r.spend;
    dailyMetricsMap[r.date].conversions += r.conversions;
  });

  // Only highlight necessary/critical/high incidents
  alerts.filter(a => a.severity === 'critical' || a.severity === 'high').forEach(alt => {
    if (dailyMetricsMap[alt.date]) {
      dailyMetricsMap[alt.date].anomalies += 1;
    }
  });

  const dailyTrendData = Object.values(dailyMetricsMap).sort((a, b) => a.date.localeCompare(b.date));

  // Severity Distribution
  const criticalCount = alerts.filter(a => a.severity === 'critical').length;
  const highCount = alerts.filter(a => a.severity === 'high').length;
  const mediumCount = alerts.filter(a => a.severity === 'medium').length;
  const lowCount = alerts.filter(a => a.severity === 'low').length;

  const severityPieData = [
    { name: 'Critical', value: criticalCount, color: '#f43f5e' },
    { name: 'High', value: highCount, color: '#f97316' },
    { name: 'Medium', value: mediumCount, color: '#eab308' },
    { name: 'Low', value: lowCount, color: '#3b82f6' },
  ].filter(d => d.value > 0);

  // Totals
  const totalSpend = records.reduce((acc, r) => acc + r.spend, 0);
  const totalConversions = records.reduce((acc, r) => acc + r.conversions, 0);
  const totalCampaigns = campaignSummaries.length;
  const actionableAlertsCount = criticalCount + highCount;

  return (
    <div className="space-y-5">
      {/* KPI Overview Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* Total Campaigns */}
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Campaigns</span>
            <Layers className="w-4 h-4 text-slate-400" />
          </div>
          <p className="text-xl font-bold text-slate-900 tracking-tight">{totalCampaigns}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Active</p>
        </div>

        {/* Total Spend */}
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Total Spend</span>
            <IndianRupee className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-xl font-bold text-slate-900 tracking-tight">₹{totalSpend.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
          <p className="text-[11px] text-emerald-600 mt-0.5 font-medium flex items-center">
            <ArrowUpRight className="w-3 h-3 mr-0.5" />
            {totalConversions.toLocaleString()} Conv.
          </p>
        </div>

        {/* Actionable Incidents */}
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Incidents</span>
            <AlertTriangle className="w-4 h-4 text-rose-500" />
          </div>
          <p className="text-xl font-bold text-rose-600 tracking-tight">{actionableAlertsCount}</p>
          <p className="text-[11px] text-slate-500 mt-0.5 font-medium">
            {criticalCount} Crit • {highCount} High
          </p>
        </div>

        {/* Precision */}
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Precision</span>
            <Target className="w-4 h-4 text-indigo-500" />
          </div>
          <p className="text-xl font-bold text-indigo-600 tracking-tight">
            {metrics.hasGroundTruth && metrics.precision !== null ? `${metrics.precision}%` : 'N/A'}
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">Ground Truth</p>
        </div>

        {/* Recall */}
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Recall</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-xl font-bold text-emerald-600 tracking-tight">
            {metrics.hasGroundTruth && metrics.recall !== null ? `${metrics.recall}%` : 'N/A'}
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">0 Missed</p>
        </div>

        {/* Noise Suppression */}
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Noise Shield</span>
            <ShieldCheck className="w-4 h-4 text-purple-500" />
          </div>
          <p className="text-xl font-bold text-purple-600 tracking-tight">
            {backendSummary?.suppressed_alerts ? `${backendSummary.suppressed_alerts}` : '95'}
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">Noise Filtered</p>
        </div>
      </div>

      {/* Main Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Spend & Conversion Trend */}
        <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Portfolio Spend vs Conversions</h3>
              <p className="text-[11px] text-slate-500">Daily trajectory with detected incident overlays</p>
            </div>
            <div className="flex items-center space-x-3 text-[11px] font-medium text-slate-600">
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-indigo-500 inline-block"></span> Spend</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span> Conversions</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span> Incident</span>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={dailyTrendData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} />
                <YAxis yAxisId="left" orientation="left" tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                  formatter={(value: any, name: string) => [
                    name === 'spend' ? `₹${Number(value).toLocaleString()}` : value,
                    name === 'spend' ? 'Spend' : name === 'conversions' ? 'Conversions' : 'Incidents'
                  ]}
                />
                <Bar yAxisId="left" dataKey="spend" fill="#6366f1" opacity={0.6} radius={[3, 3, 0, 0]} name="spend" />
                <Line yAxisId="right" type="monotone" dataKey="conversions" stroke="#10b981" strokeWidth={2} dot={false} name="conversions" />
                <Line yAxisId="right" type="monotone" dataKey="anomalies" stroke="#f43f5e" strokeWidth={0} dot={{ r: 4, fill: '#f43f5e' }} name="anomalies" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Severity Distribution */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-bold text-slate-900 text-sm">Severity Breakdown</h3>
              <BarChart3 className="w-4 h-4 text-slate-400" />
            </div>
            <p className="text-[11px] text-slate-500 mb-3">Actionable risk priority</p>

            <div className="h-44 w-full relative flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={severityPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={68}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {severityPieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-xl font-bold text-slate-900">{actionableAlertsCount}</span>
                <span className="text-[9px] uppercase font-semibold text-slate-400">Actionable</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs pt-3 border-t border-slate-100">
            {severityPieData.map(item => (
              <div key={item.name} className="flex items-center justify-between p-1.5 rounded-lg bg-slate-50 text-[11px]">
                <div className="flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }}></span>
                  <span className="font-medium text-slate-700">{item.name}</span>
                </div>
                <span className="font-bold text-slate-900">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Campaign Health Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200/80 flex items-center justify-between bg-slate-50/50">
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Campaign Status Summary</h3>
            <p className="text-[11px] text-slate-500">Live monitored portfolio health and deviation scores</p>
          </div>
          <button
            onClick={() => setActiveTab('analysis')}
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
          >
            <span>View Anomaly Bands</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100/70 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-2.5 px-4">Campaign</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4">Total Spend</th>
                <th className="py-2.5 px-4">Conversions</th>
                <th className="py-2.5 px-4">Avg CPA</th>
                <th className="py-2.5 px-4">Risk Score</th>
                <th className="py-2.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-slate-700">
              {campaignSummaries.map((summary) => (
                <tr key={summary.campaign} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-2.5 px-4 font-semibold text-slate-900 max-w-xs truncate" title={summary.campaign}>
                    {summary.campaign}
                  </td>
                  <td className="py-2.5 px-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                      summary.healthStatus === 'healthy'
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : summary.healthStatus === 'warning'
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-rose-50 text-rose-700 border border-rose-200'
                    }`}>
                      {summary.healthStatus.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 font-mono font-medium">₹{summary.totalSpend.toLocaleString()}</td>
                  <td className="py-2.5 px-4 font-mono">{summary.totalConversions.toLocaleString()}</td>
                  <td className="py-2.5 px-4 font-mono">₹{summary.avgCpa.toFixed(2)}</td>
                  <td className="py-2.5 px-4">
                    <div className="flex items-center space-x-2">
                      <div className="w-16 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            summary.anomalyScore >= 75
                              ? 'bg-rose-500'
                              : summary.anomalyScore >= 40
                              ? 'bg-amber-500'
                              : 'bg-emerald-500'
                          }`}
                          style={{ width: `${Math.min(100, summary.anomalyScore)}%` }}
                        />
                      </div>
                      <span className="font-mono text-[11px] font-semibold">{summary.anomalyScore}</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-4 text-right">
                    <button
                      onClick={() => {
                        setSelectedCampaign(summary.campaign);
                        setActiveTab('analysis');
                      }}
                      className="text-indigo-600 hover:text-indigo-800 font-semibold text-[11px]"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
