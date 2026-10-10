import React, { useState } from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts'
import { formatDate } from '../../utils/formatters'

import { ALERTS } from '../../data/challengeDataset'

export const AlertTrendChart: React.FC = () => {
  const [aggregation, setAggregation] = useState<'daily' | 'weekly'>('weekly')

  // Calculate 180-day weekly distribution from ALERTS
  // 180 days / 7 = ~26 weeks starting from 2026-03-01
  const weeklyData = React.useMemo(() => {
    const startDate = new Date('2026-03-01T00:00:00Z').getTime()
    const weeks: { date: string; critical: number; high: number; medium: number; low: number }[] = []
    for (let w = 0; w < 26; w++) {
      const wStart = new Date(startDate + w * 7 * 86400000)
      const label = `W${w + 1} (${wStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })})`
      weeks.push({ date: label, critical: 0, high: 0, medium: 0, low: 0 })
    }

    ALERTS.forEach((a) => {
      const aDate = new Date(a.date || a.firstDetected).getTime()
      const diffDays = Math.floor((aDate - startDate) / 86400000)
      const weekIdx = Math.min(25, Math.max(0, Math.floor(diffDays / 7)))
      const sev = a.severity as 'critical' | 'high' | 'medium' | 'low'
      if (weeks[weekIdx] && weeks[weekIdx][sev] !== undefined) {
        weeks[weekIdx][sev] += 1
      }
    })
    return weeks
  }, [])

  // Aggregate days with alerts for daily view
  const dailyData = React.useMemo(() => {
    const dayMap: Record<string, { critical: number; high: number; medium: number; low: number }> = {}
    ALERTS.forEach((a) => {
      const d = (a.date || a.firstDetected).split('T')[0]
      if (!dayMap[d]) {
        dayMap[d] = { critical: 0, high: 0, medium: 0, low: 0 }
      }
      const sev = a.severity as 'critical' | 'high' | 'medium' | 'low'
      if (dayMap[d][sev] !== undefined) {
        dayMap[d][sev] += 1
      }
    })
    return Object.entries(dayMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, counts]) => ({
        date,
        ...counts,
      }))
  }, [])

  const activeData = aggregation === 'daily' ? dailyData : weeklyData

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const total = payload.reduce((acc: number, item: any) => acc + (item.value || 0), 0)
      return (
        <div className="bg-white border border-[#E4E9F1] rounded-xl shadow-lg p-3 text-xs w-48 z-50">
          <p className="font-semibold text-slate-800 pb-1 mb-1 border-b border-slate-100">
            {aggregation === 'daily' ? formatDate(label, 'MMM d, yyyy') : label}
          </p>
          <div className="space-y-1">
            {payload.map((item: any) => (
              <div key={item.name} className="flex justify-between">
                <span className="flex items-center gap-1.5 capitalize text-slate-600">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                  {item.name}:
                </span>
                <span className="font-semibold text-slate-900">{item.value}</span>
              </div>
            ))}
            <div className="flex justify-between pt-1 border-t border-slate-100 font-bold text-slate-900">
              <span>Total Volume:</span>
              <span>{total} alerts</span>
            </div>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-sm font-semibold text-[#172033]">Alert Volume by Severity</h4>
          <p className="text-xs text-[#697586]">Distribution over time across severity tiers</p>
        </div>

        <div className="flex bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg p-0.5 text-xs">
          <button
            onClick={() => setAggregation('daily')}
            className={`px-2.5 py-1 rounded-md text-xs font-medium cursor-pointer transition-colors ${
              aggregation === 'daily'
                ? 'bg-white text-[#3867F5] shadow-2xs font-semibold'
                : 'text-[#697586] hover:text-[#172033]'
            }`}
          >
            Daily
          </button>
          <button
            onClick={() => setAggregation('weekly')}
            className={`px-2.5 py-1 rounded-md text-xs font-medium cursor-pointer transition-colors ${
              aggregation === 'weekly'
                ? 'bg-white text-[#3867F5] shadow-2xs font-semibold'
                : 'text-[#697586] hover:text-[#172033]'
            }`}
          >
            Weekly
          </button>
        </div>
      </div>

      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={activeData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E4E9F1" />
            <XAxis
              dataKey="date"
              tickFormatter={(d) => (aggregation === 'daily' ? formatDate(d, 'MMM d') : d)}
              tick={{ fontSize: 11, fill: '#697586' }}
              axisLine={{ stroke: '#E4E9F1' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#697586' }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 11, paddingTop: 10 }}
              iconType="circle"
              iconSize={8}
            />
            <Bar dataKey="critical" name="Critical" stackId="a" fill="#DC3545" radius={[0, 0, 0, 0]} />
            <Bar dataKey="high" name="High" stackId="a" fill="#F59E0B" radius={[0, 0, 0, 0]} />
            <Bar dataKey="medium" name="Medium" stackId="a" fill="#3867F5" radius={[0, 0, 0, 0]} />
            <Bar dataKey="low" name="Low" stackId="a" fill="#94A3B8" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
