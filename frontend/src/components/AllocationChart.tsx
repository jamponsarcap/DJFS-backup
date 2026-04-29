import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { AllocationBreakdown } from '../types'

const COLORS: Record<string, string> = {
  equity:       '#3B82F6',
  fixed_income: '#10B981',
  cash:         '#F59E0B',
  alternatives: '#8B5CF6',
}

const LABELS: Record<string, string> = {
  equity:       'Equity',
  fixed_income: 'Fixed Income',
  cash:         'Cash',
  alternatives: 'Alternatives',
}

interface Props { allocation: AllocationBreakdown }

export default function AllocationChart({ allocation }: Props) {
  const raw = Object.entries(allocation)
    .map(([key, value]) => ({
      name: LABELS[key] ?? key,
      rawValue: Number(value),
      color: COLORS[key] ?? '#6B7280',
    }))
    .filter(d => d.rawValue > 0)

  const total = raw.reduce((sum, d) => sum + d.rawValue, 0)
  const data = raw.map(d => ({
    ...d,
    value: total > 0 ? Number((d.rawValue / total * 100).toFixed(1)) : 0,
  }))

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 h-full">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Allocation Breakdown</h3>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={65}
            outerRadius={95}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip formatter={(v: number) => `${v}%`} />
          <Legend
            wrapperStyle={{ paddingTop: 16 }}
            formatter={(v, entry: any) => (
              <span className="text-xs text-gray-600">
                {v} <span className="font-medium">{entry.payload.value}%</span>
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
