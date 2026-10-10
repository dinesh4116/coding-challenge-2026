import React from 'react'
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts'
import { Campaign } from '../../types/campaign'

interface CampaignHealthDonutProps {
  campaigns: Campaign[]
}

export const CampaignHealthDonut: React.FC<CampaignHealthDonutProps> = ({ campaigns }) => {
  const counts = {
    healthy: campaigns.filter((c) => c.status === 'healthy').length,
    warning: campaigns.filter((c) => c.status === 'warning').length,
    critical: campaigns.filter((c) => c.status === 'critical').length,
    investigating: campaigns.filter((c) => c.status === 'investigating').length,
  }

  const data = [
    { name: 'Healthy', value: counts.healthy, color: '#16A36A' },
    { name: 'Warning', value: counts.warning, color: '#F59E0B' },
    { name: 'Critical', value: counts.critical, color: '#DC3545' },
    { name: 'Under Investigation', value: counts.investigating, color: '#3867F5' },
  ].filter((d) => d.value > 0)

  const total = campaigns.length

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0]
      const percent = total > 0 ? ((p.value / total) * 100).toFixed(1) : '0'
      return (
        <div className="bg-white border border-[#E4E9F1] rounded-xl shadow-lg p-2.5 text-xs z-50">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.payload.color }} />
            <span className="font-semibold text-slate-800">{p.name}:</span>
            <span className="font-bold text-slate-900">
              {p.value} ({percent}%)
            </span>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div className="w-full flex flex-col items-center">
      <div style={{ width: '100%', height: 180 }} className="relative flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip content={<CustomTooltip />} />
            <Pie
              data={data}
              innerRadius={54}
              outerRadius={76}
              paddingAngle={3}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-xl font-bold text-[#172033]">{total}</span>
          <span className="text-[10px] text-[#697586] font-medium uppercase tracking-wider">
            Total
          </span>
        </div>
      </div>

      {/* Legend pill list */}
      <div className="grid grid-cols-2 gap-2 w-full mt-2 text-xs">
        {data.map((item) => (
          <div
            key={item.name}
            className="flex items-center justify-between p-2 rounded-lg bg-[#F5F7FB] border border-[#E4E9F1]"
          >
            <div className="flex items-center gap-1.5 truncate">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
              <span className="text-[#697586] truncate text-[11px]">{item.name}</span>
            </div>
            <span className="font-bold text-[#172033] text-xs">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
