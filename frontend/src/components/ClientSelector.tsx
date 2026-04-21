import { ChevronDown, User } from 'lucide-react'
import type { Client } from '../types'

interface Props {
  clients: Client[]
  selected: Client | null
  onSelect: (c: Client) => void
}

export default function ClientSelector({ clients, selected, onSelect }: Props) {
  return (
    <div className="relative">
      <div className="flex items-center gap-2 bg-navy-700 border border-navy-600 rounded-lg px-3 py-2 cursor-pointer min-w-[220px]">
        <User size={16} className="text-teal-400 shrink-0" />
        <select
          className="bg-transparent text-white text-sm font-medium w-full appearance-none outline-none cursor-pointer"
          value={selected?.id ?? ''}
          onChange={e => {
            const c = clients.find(cl => cl.id === e.target.value)
            if (c) onSelect(c)
          }}
        >
          <option value="" disabled>Select client…</option>
          {clients.map(c => (
            <option key={c.id} value={c.id} className="bg-navy-800 text-white">
              {c.name}
            </option>
          ))}
        </select>
        <ChevronDown size={14} className="text-gray-400 shrink-0" />
      </div>
    </div>
  )
}
