import type { Holding } from '../types'

const fmt = (n: number) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(n)

const classColors: Record<string, string> = {
  equity:       'bg-blue-100 text-blue-700',
  fixed_income: 'bg-emerald-100 text-emerald-700',
  cash:         'bg-amber-100 text-amber-700',
  alternatives: 'bg-purple-100 text-purple-700',
}

const classLabels: Record<string, string> = {
  equity:       'Equity',
  fixed_income: 'Fixed Inc.',
  cash:         'Cash',
  alternatives: 'Alts',
}

interface Props { holdings: Holding[] }

export default function HoldingsTable({ holdings }: Props) {
  const sorted = [...holdings].sort((a, b) => b.market_value - a.market_value)
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Holdings</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
              <th className="pb-2 font-medium">Symbol</th>
              <th className="pb-2 font-medium">Class</th>
              <th className="pb-2 font-medium text-right">Market Value</th>
              <th className="pb-2 font-medium text-right">Weight</th>
              <th className="pb-2 font-medium text-right">Gain / Loss</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {sorted.map(h => (
              <tr key={h.symbol} className="hover:bg-gray-50 transition-colors">
                <td className="py-2.5 pr-3">
                  <div className="font-medium text-gray-900">{h.symbol}</div>
                  <div className="text-xs text-gray-400 truncate max-w-[140px]">{h.name}</div>
                </td>
                <td className="py-2.5 pr-3">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${classColors[h.asset_class] ?? 'bg-gray-100 text-gray-600'}`}>
                    {classLabels[h.asset_class] ?? h.asset_class}
                  </span>
                </td>
                <td className="py-2.5 text-right font-medium text-gray-900">{fmt(h.market_value)}</td>
                <td className="py-2.5 text-right text-gray-500">{h.weight.toFixed(1)}%</td>
                <td className={`py-2.5 text-right font-medium ${h.gain_loss >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {h.gain_loss >= 0 ? '+' : ''}{h.gain_loss_pct.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
