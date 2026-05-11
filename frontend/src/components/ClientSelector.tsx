import { useState, useRef, useEffect } from 'react'
import { ChevronDown, User, Check } from 'lucide-react'
import type { Client } from '../types'

interface Props {
  clients: Client[]
  selected: Client | null
  onSelect: (c: Client) => void
}

const RISK_STYLES: Record<string, { bg: string; text: string }> = {
  conservative: { bg: 'bg-blue-500/20',   text: 'text-blue-300' },
  balanced:     { bg: 'bg-teal-500/20',   text: 'text-teal-300' },
  growth:       { bg: 'bg-amber-500/20',  text: 'text-amber-300' },
  aggressive:   { bg: 'bg-red-500/20',    text: 'text-red-300' },
}

function riskStyle(profile: string) {
  return RISK_STYLES[profile?.toLowerCase()] ?? { bg: 'bg-gray-500/20', text: 'text-gray-300' }
}

export default function ClientSelector({ clients, selected, onSelect }: Props) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleSelect = (c: Client) => {
    onSelect(c)
    setOpen(false)
  }

  const { bg, text } = selected ? riskStyle(selected.risk_profile) : { bg: '', text: '' }

  return (
    <div ref={ref} className="relative">
      {/* Trigger button */}
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2.5 rounded-xl px-3.5 py-2 transition-all duration-150 border border-white/10 hover:border-white/25 hover:bg-white/5 focus:outline-none"
        style={{ minWidth: 230 }}
      >
        <div className="bg-teal-500/20 p-1.5 rounded-lg">
          <User size={13} className="text-teal-400" />
        </div>

        <div className="flex-1 text-left leading-tight">
          {selected ? (
            <>
              <div className="text-white text-sm font-semibold truncate">{selected.name}</div>
              <div className="text-gray-400 text-xs truncate">{selected.rm_name}</div>
            </>
          ) : (
            <div className="text-gray-400 text-sm">Select client…</div>
          )}
        </div>

        {selected && (
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${bg} ${text}`}>
            {selected.risk_profile}
          </span>
        )}

        <ChevronDown
          size={14}
          className={`text-gray-400 shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-72 rounded-xl border border-white/10 shadow-2xl overflow-hidden z-50"
          style={{ backgroundColor: '#0e1f35' }}
        >
          <div className="px-3 py-2 border-b border-white/5">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Select Client</p>
          </div>

          <ul className="py-1 max-h-72 overflow-y-auto">
            {clients.map(c => {
              const isSelected = c.id === selected?.id
              const { bg: cBg, text: cText } = riskStyle(c.risk_profile)
              return (
                <li key={c.id}>
                  <button
                    onClick={() => handleSelect(c)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors duration-100 ${
                      isSelected ? 'bg-teal-500/10' : 'hover:bg-white/5'
                    }`}
                  >
                    {/* Avatar */}
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
                      isSelected ? 'bg-teal-500/30 text-teal-300' : 'bg-white/10 text-gray-300'
                    }`}>
                      {c.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                    </div>

                    {/* Details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-semibold truncate ${isSelected ? 'text-teal-300' : 'text-white'}`}>
                          {c.name}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 truncate mt-0.5">
                        RM: {c.rm_name} · Last review: {c.last_review}
                      </div>
                    </div>

                    {/* Risk badge */}
                    <div className="flex flex-col items-end gap-1 shrink-0">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cBg} ${cText}`}>
                        {c.risk_profile}
                      </span>
                      {isSelected && <Check size={12} className="text-teal-400" />}
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}