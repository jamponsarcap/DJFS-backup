import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import type { CashFlowPoint } from '../types'

const fmtK = (n: number) =>
  new Intl.NumberFormat('en-GB', { notation: 'compact', maximumFractionDigits: 0 }).format(n)

interface Props { data: CashFlowPoint[] }

export default function CashFlowChart({ data }: Props) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Monthly Cash Flow</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
          <XAxis dataKey="month" tick={{ fontSize: 11 }} tickLine={false} />
          <YAxis tickFormatter={fmtK} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip
            formatter={(v: number) => fmtK(v)}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E5E7EB' }}
          />
          <Legend formatter={v => <span className="text-xs text-gray-600">{v}</span>} />
          <ReferenceLine y={0} stroke="#E5E7EB" />
          <Bar dataKey="inflow"  name="Inflow"  fill="#10B981" radius={[3,3,0,0]} />
          <Bar dataKey="outflow" name="Outflow" fill="#F87171" radius={[3,3,0,0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
