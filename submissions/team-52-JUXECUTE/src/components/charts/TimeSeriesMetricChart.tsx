import React, { useState } from 'react'
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Dot,
} from 'recharts'
import { MetricDataPoint } from '../../types/campaign'
import { formatCurrency, formatPercent, formatDate, formatNumber } from '../../utils/formatters'
import { AlertCircle } from 'lucide-react'

export type SelectedMetric = 'spend' | 'clicks' | 'conversions' | 'ctr' | 'cpc' | 'cvr'

interface TimeSeriesMetricChartProps {
  data: MetricDataPoint[]
  title?: string
  subtitle?: string
  campaignSelector?: React.ReactNode
  showMetricSelector?: boolean
  defaultMetric?: SelectedMetric
  height?: number
}

export const TimeSeriesMetricChart: React.FC<TimeSeriesMetricChartProps> = ({
  data,
  title = 'Campaign Metric & Adaptive Anomaly Bounds',
  subtitle = 'Daily observed metric vs baseline expectation and adaptive tolerance envelope',
  campaignSelector,
  showMetricSelector = true,
  defaultMetric = 'conversions',
  height = 340,
}) => {
  const [selectedMetric, setSelectedMetric] = useState<SelectedMetric>(defaultMetric)

  // Map metric to actual, baseline, lower, and upper values in data
  const chartData = data.map((d) => {
    let actual = d.spend
    let baseline = d.baselineSpend
    let lower = d.lowerBandSpend
    let upper = d.upperBandSpend

    if (selectedMetric === 'clicks') {
      actual = d.clicks
      baseline = d.baselineClicks
      lower = d.lowerBandClicks
      upper = d.upperBandClicks
    } else if (selectedMetric === 'conversions') {
      actual = d.conversions
      baseline = d.baselineConversions
      lower = d.lowerBandConversions
      upper = d.upperBandConversions
    } else if (selectedMetric === 'ctr') {
      actual = Number((d.ctr * 100).toFixed(2))
      baseline = Number((d.baselineCtr * 100).toFixed(2))
      lower = Number((d.baselineCtr * 0.7 * 100).toFixed(2))
      upper = Number((d.baselineCtr * 1.3 * 100).toFixed(2))
    } else if (selectedMetric === 'cpc') {
      actual = d.cpc
      baseline = d.baselineCpc
      lower = Number((d.baselineCpc * 0.75).toFixed(2))
      upper = Number((d.baselineCpc * 1.25).toFixed(2))
    } else if (selectedMetric === 'cvr') {
      actual = Number((d.cvr * 100).toFixed(2))
      baseline = Number((d.baselineCvr * 100).toFixed(2))
      lower = Number((d.baselineCvr * 0.65 * 100).toFixed(2))
      upper = Number((d.baselineCvr * 1.35 * 100).toFixed(2))
    }

    const bandRange = Math.max(0, upper - lower)

    return {
      date: d.date,
      actual,
      baseline,
      lowerBand: lower,
      upperBand: upper,
      bandBase: lower,
      bandRange,
      isAnomaly: d.isAnomaly,
      anomalySeverity: d.anomalySeverity,
      score: d.anomalyScore,
    }
  })

  // Format Y-axis value
  const formatYAxis = (val: number) => {
    if (selectedMetric === 'spend' || selectedMetric === 'cpc') {
      return formatCurrency(val)
    }
    if (selectedMetric === 'ctr' || selectedMetric === 'cvr') {
      return `${val}%`
    }
    return formatNumber(val)
  }

  // Custom Dot renderer to highlight anomalies
  const renderCustomDot = (props: any) => {
    const { cx, cy, payload } = props
    if (payload.isAnomaly) {
      return (
        <g key={`anomaly-dot-${payload.date}`}>
          <circle cx={cx} cy={cy} r={6} fill="#DC3545" stroke="#FFFFFF" strokeWidth={2} />
          <circle cx={cx} cy={cy} r={10} fill="#DC3545" opacity={0.25} />
        </g>
      )
    }
    return <Dot key={`dot-${payload.date}`} {...props} r={2} fill="#3867F5" />
  }

  // Custom Rich Tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload
      const deviation = p.baseline > 0 ? ((p.actual - p.baseline) / p.baseline) * 100 : 0

      return (
        <div className="bg-white border border-[#E4E9F1] rounded-xl shadow-lg p-3 text-xs w-60 z-50">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100">
            <span className="font-semibold text-slate-800">{formatDate(label)}</span>
            {p.isAnomaly && (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                <AlertCircle className="w-3 h-3" /> Anomaly Detected
              </span>
            )}
          </div>
          <div className="space-y-1.5 text-slate-600">
            <div className="flex justify-between">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#3867F5]" /> Observed {selectedMetric.toUpperCase()}:
              </span>
              <span className="font-bold text-slate-900">{formatYAxis(p.actual)}</span>
            </div>
            <div className="flex justify-between">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-0.5 bg-slate-400" /> Expected Baseline:
              </span>
              <span className="font-medium text-slate-700">{formatYAxis(p.baseline)}</span>
            </div>
            <div className="flex justify-between">
              <span>Adaptive Band:</span>
              <span className="font-mono text-[11px] text-slate-500">
                {formatYAxis(p.lowerBand)} – {formatYAxis(p.upperBand)}
              </span>
            </div>
            <div className="flex justify-between pt-1 border-t border-slate-100">
              <span>Deviation:</span>
              <span
                className={`font-semibold ${
                  deviation < 0 ? 'text-rose-600' : 'text-blue-600'
                }`}
              >
                {deviation > 0 ? '+' : ''}
                {deviation.toFixed(1)}%
              </span>
            </div>
            {p.score && (
              <div className="flex justify-between text-[11px] text-slate-500">
                <span>Anomaly Score:</span>
                <span className="font-semibold text-rose-600">{p.score} MAD</span>
              </div>
            )}
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div className="w-full">
      {/* Chart Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h4 className="text-sm font-semibold text-[#172033]">{title}</h4>
          <p className="text-xs text-[#697586]">{subtitle}</p>
        </div>

        <div className="flex items-center flex-wrap gap-2">
          {campaignSelector}

          {showMetricSelector && (
            <div className="flex items-center bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg p-0.5 text-xs">
              {(['conversions', 'spend', 'clicks', 'ctr', 'cpc'] as SelectedMetric[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setSelectedMetric(m)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                    selectedMetric === m
                      ? 'bg-white text-[#3867F5] shadow-2xs font-semibold'
                      : 'text-[#697586] hover:text-[#172033]'
                  }`}
                >
                  {m.toUpperCase()}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recharts Composed Area + Line Chart */}
      <div style={{ width: '100%', height }} className="overflow-hidden">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E4E9F1" />
            <XAxis
              dataKey="date"
              tickFormatter={(date) => formatDate(date, 'MMM d')}
              tick={{ fontSize: 11, fill: '#697586' }}
              axisLine={{ stroke: '#E4E9F1' }}
              tickLine={false}
              minTickGap={28}
            />
            <YAxis
              tickFormatter={formatYAxis}
              tick={{ fontSize: 11, fill: '#697586' }}
              axisLine={false}
              tickLine={false}
              width={65}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Upper/Lower Band as transparent stack and shaded envelope */}
            <Area
              type="monotone"
              dataKey="bandBase"
              stackId="band"
              stroke="none"
              fill="transparent"
            />
            <Area
              type="monotone"
              dataKey="bandRange"
              stackId="band"
              stroke="none"
              fill="#E0E7FF"
              fillOpacity={0.6}
              name="Adaptive Tolerance Envelope"
            />

            {/* Baseline Expected Line */}
            <Line
              type="monotone"
              dataKey="baseline"
              stroke="#94A3B8"
              strokeDasharray="4 4"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
              name="Historical Baseline"
            />

            {/* Observed Actual Metric Line */}
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#3867F5"
              strokeWidth={2}
              dot={renderCustomDot}
              activeDot={{ r: 6, fill: '#3867F5', stroke: '#FFFFFF', strokeWidth: 2 }}
              name={`Observed ${selectedMetric.toUpperCase()}`}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Chart Legend */}
      <div className="flex items-center justify-center gap-6 mt-3 text-xs text-[#697586] flex-wrap">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-[#3867F5]" />
          <span>Observed Value</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 border-t border-dashed border-[#94A3B8]" />
          <span>Expected Baseline</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-2.5 rounded-xs bg-[#E0E7FF]" />
          <span>Adaptive Tolerance Envelope</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#DC3545]" />
          <span>Flagged Anomaly Observation</span>
        </div>
      </div>
    </div>
  )
}
