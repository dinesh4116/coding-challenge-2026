import React, { useState, useMemo } from 'react';
import {
  LineChart as LineChartIcon,
  TrendingUp,
  AlertTriangle,
  Info,
  ShieldCheck,
  CheckCircle2,
  Sliders,
  DollarSign,
  Activity
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceDot
} from 'recharts';
import { useData } from '../../context/DataContext';

export const AnomalyAnalysisView: React.FC = () => {
  const {
    records,
    alerts,
    campaignSummaries,
    selectedCampaign,
    setSelectedCampaign,
    config
  } = useData();

  const [metricChoice, setMetricChoice] = useState<'conversions' | 'spend' | 'cpa'>('conversions');

  // Active Campaign Data
  const activeCampaignName = selectedCampaign !== 'all' && selectedCampaign ? selectedCampaign : (campaignSummaries[0]?.campaign || '');

  // Filter records for the active campaign
  const campaignRecords = useMemo(() => {
    return records
      .filter(r => r.campaign === activeCampaignName)
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [records, activeCampaignName]);

  // Compute rolling baseline (14-day) and upper/lower variation bands for the chart
  const timeSeriesData = useMemo(() => {
    if (!campaignRecords.length) return [];
    const windowSize = config.baselineWindow;
    const result: any[] = [];

    for (let i = 0; i < campaignRecords.length; i++) {
      const current = campaignRecords[i];
      let val = current.conversions;
      if (metricChoice === 'spend') val = current.spend;
      if (metricChoice === 'cpa') val = current.cpa;

      // Calculate baseline mean & stdDev over rolling window
      const startIdx = Math.max(0, i - windowSize);
      const windowSlice = campaignRecords.slice(startIdx, i + 1);
      
      const values = windowSlice.map(r => {
        if (metricChoice === 'spend') return r.spend;
        if (metricChoice === 'cpa') return r.cpa;
        return r.conversions;
      });

      const mean = values.reduce((a, b) => a + b, 0) / values.length;
      const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / Math.max(1, values.length - 1);
      const stdDev = Math.sqrt(variance);

      // Upper and lower bands (mu +- 2 * sigma)
      const upperBand = Number((mean + 2 * stdDev).toFixed(2));
      const lowerBand = Math.max(0, Number((mean - 2 * stdDev).toFixed(2)));

      // Check if alert exists on this date
      const matchingAlert = alerts.find(a => a.campaign === activeCampaignName && a.date === current.date);

      result.push({
        date: current.date,
        observed: val,
        baseline: Number(mean.toFixed(2)),
        upperBand,
        lowerBand,
        // For Recharts Area shaded band: [lowerBand, upperBand]
        bandRange: [lowerBand, upperBand],
        isAnomaly: !!matchingAlert,
        alert: matchingAlert
      });
    }

    return result;
  }, [campaignRecords, metricChoice, alerts, activeCampaignName, config]);

  // Active campaign summary
  const campaignSummary = campaignSummaries.find(s => s.campaign === activeCampaignName);
  const campaignAlerts = alerts.filter(a => a.campaign === activeCampaignName);

  return (
    <div className="space-y-6">
      {/* Top Campaign Selector Header */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-card flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 tracking-tight">Anomaly Bands</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Historical metric trends compared against rolling median baselines and variation bands
          </p>
        </div>

        {/* Campaign Picker Dropdown */}
        <div className="flex items-center space-x-3">
          <label className="text-xs font-semibold text-slate-600">Select Campaign:</label>
          <select
            value={activeCampaignName}
            onChange={e => setSelectedCampaign(e.target.value)}
            className="px-3.5 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs font-bold text-slate-900 focus:bg-white focus:ring-2 focus:ring-indigo-500 max-w-xs truncate"
          >
            {campaignSummaries.map(s => (
              <option key={s.campaign} value={s.campaign}>
                {s.campaign} ({s.totalAlerts} alerts)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Metric Visualizer Card */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-card space-y-4">
        {/* Metric Selector Tabs */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setMetricChoice('conversions')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                metricChoice === 'conversions' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Conversions Trend
            </button>
            <button
              onClick={() => setMetricChoice('spend')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                metricChoice === 'spend' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Spend (₹) Trend
            </button>
            <button
              onClick={() => setMetricChoice('cpa')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                metricChoice === 'cpa' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              CPA (₹) Trend
            </button>
          </div>

          <div className="flex items-center space-x-4 text-xs">
            <span className="flex items-center gap-1.5 text-slate-600"><span className="w-3 h-0.5 bg-indigo-600 inline-block"></span> Observed Value</span>
            <span className="flex items-center gap-1.5 text-slate-600"><span className="w-3 h-0.5 bg-slate-400 stroke-dasharray inline-block"></span> 14d Rolling Baseline ($\mu$)</span>
            <span className="flex items-center gap-1.5 text-slate-600"><span className="w-3 h-3 bg-indigo-100 border border-indigo-300 rounded inline-block"></span> Acceptable Band ($\pm 2\sigma$)</span>
          </div>
        </div>

        {/* Multi-Metric Chart with Shaded Band & Anomaly Overlay */}
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={timeSeriesData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                formatter={(value: any, name: string) => [
                  Array.isArray(value) ? `${value[0]} - ${value[1]}` : value,
                  name === 'observed' ? 'Observed' : name === 'baseline' ? '14d Baseline' : 'Variation Band'
                ]}
              />

              {/* Shaded Confidence Band Area */}
              <Area
                type="monotone"
                dataKey="bandRange"
                stroke="none"
                fill="#e0e7ff"
                fillOpacity={0.6}
                name="Acceptable Band"
              />

              {/* Baseline Curve */}
              <Line
                type="monotone"
                dataKey="baseline"
                stroke="#64748b"
                strokeDasharray="4 4"
                strokeWidth={2}
                dot={false}
                name="baseline"
              />

              {/* Observed Metric Curve */}
              <Line
                type="monotone"
                dataKey="observed"
                stroke="#4f46e5"
                strokeWidth={2.5}
                dot={(props: any) => {
                  const { cx, cy, payload } = props;
                  if (payload.isAnomaly) {
                    return (
                      <circle
                        key={payload.date}
                        cx={cx}
                        cy={cy}
                        r={5}
                        fill="#f43f5e"
                        stroke="#fff"
                        strokeWidth={2}
                      />
                    );
                  }
                  return <circle key={payload.date} cx={cx} cy={cy} r={2} fill="#4f46e5" />;
                }}
                name="observed"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Campaign Incident Breakdown & Evidence Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card 1: Campaign Health Summary */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-card space-y-4">
          <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wider">Campaign Profile</h3>
          
          <div className="space-y-3 text-xs">
            <div className="flex justify-between pb-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">Campaign Name:</span>
              <span className="font-bold text-slate-900 truncate max-w-[180px]">{activeCampaignName}</span>
            </div>
            <div className="flex justify-between pb-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">Total Spend:</span>
              <span className="font-mono font-bold text-slate-900">₹{campaignSummary?.totalSpend.toLocaleString()}</span>
            </div>
            <div className="flex justify-between pb-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">Total Conversions:</span>
              <span className="font-mono font-bold text-slate-900">{campaignSummary?.totalConversions.toLocaleString()}</span>
            </div>
            <div className="flex justify-between pb-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">Anomaly Score:</span>
              <span className="font-mono font-bold text-rose-600">{campaignSummary?.anomalyScore} / 100</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 font-medium">Total Detected Incidents:</span>
              <span className="font-bold text-slate-900">{campaignAlerts.length}</span>
            </div>
          </div>
        </div>

        {/* Card 2: Incident Classification & Evidence */}
        <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-slate-200 shadow-card space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wider">Incident Classification & Signal Evidence</h3>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
              Multi-Metric Signal Classifier
            </span>
          </div>

          {campaignAlerts.length === 0 ? (
            <div className="p-8 text-center bg-slate-50 rounded-xl border border-slate-200 text-slate-500 text-xs">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p className="font-bold text-slate-800">No active anomalies detected for this campaign</p>
              <p className="mt-1">Performance metrics remain within expected historical confidence bounds.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {campaignAlerts.map(alt => (
                <div key={alt.id} className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        alt.severity === 'critical' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {alt.severity.toUpperCase()}
                      </span>
                      <span className="font-bold text-slate-900">{alt.category.replace('_', ' ').toUpperCase()}</span>
                    </div>
                    <span className="font-mono text-slate-500">{alt.date}</span>
                  </div>

                  <p className="text-slate-700 leading-relaxed">{alt.explanation}</p>

                  <div className="p-2.5 bg-amber-50/70 border border-amber-200/60 rounded-lg text-[11px] text-amber-900 flex items-start space-x-2">
                    <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <span>
                      <strong>Signal Evidence Disclaimer:</strong> Statistical anomaly detected based on historical baseline deviation. Requires verification against conversion tag logs and web analytics before confirmation.
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
