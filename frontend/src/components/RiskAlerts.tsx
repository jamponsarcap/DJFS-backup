import { AlertTriangle, AlertCircle, Info } from 'lucide-react'
import type { RiskAlert } from '../types'

const config: Record<string, { icon: React.ReactNode; bg: string; border: string; text: string; badge: string }> = {
  high: {
    icon: <AlertTriangle size={16} />,
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-700',
    badge: 'bg-red-100 text-red-700',
  },
  medium: {
    icon: <AlertCircle size={16} />,
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-700',
    badge: 'bg-amber-100 text-amber-700',
  },
  low: {
    icon: <Info size={16} />,
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-700',
    badge: 'bg-blue-100 text-blue-700',
  },
}

interface Props { alerts: RiskAlert[] }

export default function RiskAlerts({ alerts }: Props) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">
        Risk Alerts
        {alerts.length > 0 && (
          <span className="ml-2 bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full">
            {alerts.length}
          </span>
        )}
      </h3>
      {alerts.length === 0 ? (
        <p className="text-sm text-gray-400">No risk alerts for this portfolio.</p>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert, i) => {
            const c = config[alert.level] ?? config.low
            return (
              <div key={i} className={`rounded-lg border p-3 ${c.bg} ${c.border}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={c.text}>{c.icon}</span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded ${c.badge} uppercase tracking-wide`}>
                    {alert.level}
                  </span>
                  <span className={`text-xs font-medium ${c.text}`}>{alert.category}</span>
                </div>
                <p className={`text-xs leading-relaxed ${c.text}`}>{alert.message}</p>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
