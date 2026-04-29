import { X, TrendingUp, TrendingDown, ArrowRight, DollarSign, BarChart2 } from 'lucide-react'
import type { StatementDiff } from '../types'

interface Props {
  filename: string
  diff: StatementDiff
  onClose: () => void
}

function fmt(n: number, showSign = false) {
  const sign = showSign && n > 0 ? '+' : ''
  return sign + new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(n)
}

function DeltaBadge({ value }: { value: number }) {
  const positive = value >= 0
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full
      ${positive ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-600'}`}>
      {positive ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
      {fmt(value, true)}
    </span>
  )
}

export default function StatementDiffModal({ filename, diff, onClose }: Props) {
  const portfolioDeltaPositive = diff.total_value_delta >= 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">

        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-gray-100">
          <div>
            <h2 className="text-base font-bold text-gray-900">Statement Processed</h2>
            <p className="text-xs text-gray-500 mt-0.5">{filename} · {diff.transactions_count} transactions extracted</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors ml-4 mt-0.5">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-5">

          {/* Portfolio value */}
          <div className={`rounded-xl p-4 border ${portfolioDeltaPositive ? 'bg-emerald-50 border-emerald-100' : 'bg-red-50 border-red-100'}`}>
            <div className="flex items-center gap-2 mb-3">
              <DollarSign size={15} className={portfolioDeltaPositive ? 'text-emerald-600' : 'text-red-500'} />
              <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Portfolio Value</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">{fmt(diff.total_value_before)}</span>
              <ArrowRight size={14} className="text-gray-400 flex-shrink-0" />
              <span className="text-sm font-semibold text-gray-900">{fmt(diff.total_value_after)}</span>
              <DeltaBadge value={diff.total_value_delta} />
            </div>
          </div>

          {/* Account changes */}
          {Object.keys(diff.account_changes).length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Account Changes</h3>
              <div className="space-y-2">
                {Object.entries(diff.account_changes).map(([id, ac]) => (
                  <div key={id} className="bg-gray-50 rounded-lg p-3 flex items-center justify-between gap-3">
                    <span className="text-sm text-gray-700 font-medium truncate">{ac.account_name}</span>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-xs text-gray-400">{fmt(ac.before)}</span>
                      <ArrowRight size={12} className="text-gray-300" />
                      <span className="text-xs font-semibold text-gray-800">{fmt(ac.after)}</span>
                      <DeltaBadge value={ac.delta} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cash flow changes */}
          {Object.keys(diff.cash_flow_changes).length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                <span className="flex items-center gap-1.5"><BarChart2 size={12} /> Cash Flow Updates</span>
              </h3>
              <div className="rounded-lg border border-gray-100 overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left px-3 py-2 text-gray-500 font-medium">Month</th>
                      <th className="text-right px-3 py-2 text-gray-500 font-medium">Money In</th>
                      <th className="text-right px-3 py-2 text-gray-500 font-medium">Money Out</th>
                      <th className="text-right px-3 py-2 text-gray-500 font-medium">Net</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {Object.entries(diff.cash_flow_changes).map(([month, cf]) => (
                      <tr key={month} className="bg-white">
                        <td className="px-3 py-2 font-medium text-gray-700">{month}</td>
                        <td className="px-3 py-2 text-right text-emerald-600">{fmt(cf.inflow_delta)}</td>
                        <td className="px-3 py-2 text-right text-red-500">{fmt(cf.outflow_delta)}</td>
                        <td className="px-3 py-2 text-right">
                          <DeltaBadge value={cf.net_delta} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 pb-5">
          <button
            onClick={onClose}
            className="w-full bg-gray-900 hover:bg-gray-700 text-white text-sm font-medium rounded-lg py-2.5 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
