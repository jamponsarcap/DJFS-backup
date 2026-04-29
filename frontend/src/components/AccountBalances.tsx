import type { Account } from '../types'

const fmt = (n: number, currency: string) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n)

const typeColors: Record<string, string> = {
  personal:  'bg-blue-100 text-blue-700',
  joint:     'bg-purple-100 text-purple-700',
  corporate: 'bg-amber-100 text-amber-700',
}

interface Props { accounts: Account[] }

export default function AccountBalances({ accounts }: Props) {
  const currency = accounts[0]?.currency ?? 'GBP'
  const total = accounts.reduce((s, a) => s + a.balance, 0)
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 h-full">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Account Balances</h3>
      <div className="space-y-3">
        {accounts.map(a => (
          <div key={a.id} className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <span className={`text-xs font-medium px-2 py-0.5 rounded capitalize ${typeColors[a.type] ?? 'bg-gray-100 text-gray-600'}`}>
                {a.type}
              </span>
              <span className="text-sm text-gray-700 truncate">{a.name}</span>
            </div>
            <span className="text-sm font-semibold text-gray-900 ml-2 shrink-0">{fmt(a.balance, currency)}</span>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-3 border-t border-gray-100 flex justify-between">
        <span className="text-xs text-gray-500 font-medium">Total across accounts</span>
        <span className="text-sm font-bold text-gray-900">{fmt(total, currency)}</span>
      </div>
    </div>
  )
}
