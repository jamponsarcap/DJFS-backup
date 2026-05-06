import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { fetchHoldingsHistory } from '../api/client'
import type { HoldingsHistory } from '../api/client'

const LINE_COLORS = [
  '#3B82F6', '#10B981', '#8B5CF6', '#F59E0B',
  '#EF4444', '#EC4899', '#06B6D4', '#84CC16',
  '#F97316', '#6366F1',
]

const fmtDate = (iso: string) => {
  const d = new Date(iso)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

interface Props {
  clientId: string
  refreshTrigger?: string | null
}

export default function HoldingsTrendChart({ clientId, refreshTrigger }: Props) {
  const [history, setHistory] = useState<HoldingsHistory | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchHoldingsHistory(clientId)
      .then(setHistory)
      .catch(() => setHistory(null))
      .finally(() => setLoading(false))
  }, [clientId, refreshTrigger])

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex items-center justify-center h-[320px]">
        <span className="text-sm text-gray-400">Loading price history…</span>
      </div>
    )
  }

  if (!history || history.series.length === 0) return null

  const chartData = history.dates.map((date, i) => {
    const point: Record<string, any> = { date: fmtDate(date) }
    history.series.forEach(s => { point[s.symbol] = s.values[i] })
    return point
  })

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold text-gray-700">Holdings — Price Trend</h3>
        <span className="text-xs text-gray-400">% change from 26 weeks ago</span>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 8, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10 }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={v => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`}
            tick={{ fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={58}
          />
          <ReferenceLine y={0} stroke="#E5E7EB" strokeWidth={1.5} />
          <Tooltip
            formatter={(v: number, name: string) => {
              const s = history.series.find(x => x.symbol === name)
              return [`${v > 0 ? '+' : ''}${v.toFixed(2)}%`, s?.name ?? name]
            }}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E5E7EB' }}
          />
          <Legend
            formatter={(symbol: string) => {
              const s = history.series.find(x => x.symbol === symbol)
              return <span className="text-xs text-gray-600">{symbol} <span className="text-gray-400">{s?.name}</span></span>
            }}
            wrapperStyle={{ paddingTop: 12 }}
          />
          {history.series.map((s, i) => (
            <Line
              key={s.symbol}
              type="monotone"
              dataKey={s.symbol}
              stroke={LINE_COLORS[i % LINE_COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
