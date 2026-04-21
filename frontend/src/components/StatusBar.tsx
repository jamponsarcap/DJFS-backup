import type { ServiceStatus } from '../types'

interface Props { status: ServiceStatus | null }

const services: { key: keyof ServiceStatus; label: string }[] = [
  { key: 'fabric',           label: 'Fabric SQL' },
  { key: 'openai',          label: 'Azure OpenAI' },
  { key: 'ai_search',       label: 'AI Search' },
  { key: 'doc_intelligence', label: 'Doc Intelligence' },
  { key: 'market_data',     label: 'Market Data' },
]

export default function StatusBar({ status }: Props) {
  if (!status) return null
  return (
    <div className="flex items-center gap-3 flex-wrap">
      {services.map(({ key, label }) => (
        <span key={key} className="flex items-center gap-1 text-xs">
          <span className={`inline-block w-2 h-2 rounded-full ${status[key] ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          <span className="text-gray-300">{label}</span>
          <span className={`font-medium ${status[key] ? 'text-emerald-400' : 'text-amber-400'}`}>
            {status[key] ? 'Live' : 'Mock'}
          </span>
        </span>
      ))}
    </div>
  )
}
