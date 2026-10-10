import React from 'react'
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
import { EvaluationRun } from '../../types/evaluation'
import { formatPercent } from '../../utils/formatters'

interface PrecisionRecallChartProps {
  runs: EvaluationRun[]
}

export const PrecisionRecallChart: React.FC<PrecisionRecallChartProps> = ({ runs }) => {
  const chartData = runs.map((r) => ({
    name: r.shortName,
    precision: Number((r.precision * 100).toFixed(1)),
    recall: Number((r.recall * 100).toFixed(1)),
    f1Score: Number((r.f1Score * 100).toFixed(1)),
    totalAlerts: r.totalAlertsGenerated,
  }))

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const dataObj = chartData.find((d) => d.name === label)
      return (
        <div className="bg-white border border-[#E4E9F1] rounded-xl shadow-lg p-3 text-xs w-56 z-50">
          <p className="font-semibold text-slate-800 pb-1 mb-1 border-b border-slate-100">
            {label}
          </p>
          <div className="space-y-1">
            {payload.map((item: any) => (
              <div key={item.name} className="flex justify-between">
                <span className="flex items-center gap-1.5 text-slate-600">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                  {item.name}:
                </span>
                <span className="font-bold text-slate-900">{item.value}%</span>
              </div>
            ))}
            {dataObj && (
              <div className="flex justify-between pt-1 border-t border-slate-100 text-slate-500">
                <span>Total Alerts Fired:</span>
                <span className="font-semibold text-slate-900">{dataObj.totalAlerts}</span>
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
      <div className="flex items-center justify-between mb-3">
        <div>
          <h4 className="text-sm font-semibold text-[#172033]">
            Detection Method Performance Benchmark
          </h4>
          <p className="text-xs text-[#697586]">
            Precision (Noise reduction) vs Recall (Incident capture) vs F1 Score
          </p>
        </div>
      </div>

      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E4E9F1" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: '#697586' }}
              axisLine={{ stroke: '#E4E9F1' }}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(val) => `${val}%`}
              tick={{ fontSize: 11, fill: '#697586' }}
              axisLine={false}
              tickLine={false}
              domain={[0, 100]}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
              iconType="circle"
              iconSize={8}
            />
            <Bar dataKey="precision" name="Precision (Alert Quality)" fill="#16A36A" radius={[4, 4, 0, 0]} />
            <Bar dataKey="recall" name="Recall (Safety Net)" fill="#3867F5" radius={[4, 4, 0, 0]} />
            <Bar dataKey="f1Score" name="F1 Score" fill="#F59E0B" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
