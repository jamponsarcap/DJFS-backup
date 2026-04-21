import { TrendingUp, TrendingDown, Wallet, BarChart2, Shield } from 'lucide-react'
import type { PortfolioData } from '../types'

const fmt = (n: number) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(n)

const fmtPct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`

interface Props { data: PortfolioData }

export default function KpiCards({ data }: Props) {
  const highAlerts = data.risk_alerts.filter(a => a.level === 'high').length
  const cards = [
    {
      label: 'Total Portfolio Value',
      value: fmt(data.total_value),
      sub: null,
      icon: <Wallet size={20} />,
      color: 'text-teal-500',
      bg: 'bg-teal-50',
    },
    {
      label: 'Total Return',
      value: fmt(data.total_return),
      sub: fmtPct(data.total_return_pct),
      icon: data.total_return >= 0 ? <TrendingUp size={20} /> : <TrendingDown size={20} />,
      color: data.total_return >= 0 ? 'text-emerald-600' : 'text-red-500',
      bg: data.total_return >= 0 ? 'bg-emerald-50' : 'bg-red-50',
    },
    {
      label: 'YTD Return',
      value: fmtPct(data.ytd_return_pct),
      sub: 'year to date',
      icon: <BarChart2 size={20} />,
      color: data.ytd_return_pct >= 0 ? 'text-emerald-600' : 'text-red-500',
      bg: data.ytd_return_pct >= 0 ? 'bg-emerald-50' : 'bg-red-50',
    },
    {
      label: 'Risk Alerts',
      value: data.risk_alerts.length.toString(),
      sub: highAlerts > 0 ? `${highAlerts} high priority` : 'no high priority',
      icon: <Shield size={20} />,
      color: highAlerts > 0 ? 'text-red-500' : 'text-amber-500',
      bg: highAlerts > 0 ? 'bg-red-50' : 'bg-amber-50',
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map(c => (
        <div key={c.label} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{c.label}</span>
            <span className={`${c.bg} ${c.color} p-2 rounded-lg`}>{c.icon}</span>
          </div>
          <div className={`text-2xl font-bold ${c.color}`}>{c.value}</div>
          {c.sub && <div className="text-xs text-gray-400 mt-1">{c.sub}</div>}
        </div>
      ))}
    </div>
  )
}
