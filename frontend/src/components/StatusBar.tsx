import type { ServiceStatus } from '../types'

interface Props { status: ServiceStatus | null }

const services: { key: keyof ServiceStatus; label: string }[] = [
  { key: 'fabric',                       label: 'Fabric SQL' },
  { key: 'openai',                       label: 'Azure OpenAI' },
  { key: 'ai_search',                    label: 'AI Search' },
  { key: 'doc_intelligence',             label: 'Doc Intelligence' },
  { key: 'market_data',                  label: 'Market Data' },
  { key: 'foundry_summarization_agent',  label: 'Summarization Agent' },
  { key: 'foundry_portfolio_agent',      label: 'Portfolio Agent' },
]

export default function StatusBar({ status }: Props) {
  if (!status) return null
  const allLive = services.every(s => status[s.key])
  const liveCnt = services.filter(s => status[s.key]).length

  return (
    <div className="flex items-center gap-4">
      {/* Summary pill */}
      <span className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${
        allLive
          ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
          : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
      }`}>
        <span className={`w-1.5 h-1.5 rounded-full ${allLive ? 'bg-emerald-400' : 'bg-amber-400'}`} />
        {allLive ? 'All services live' : `${liveCnt}/${services.length} live`}
      </span>

      {/* Individual dots */}
      <div className="flex items-center gap-2">
        {services.map(({ key, label }) => (
          <span
            key={key}
            title={`${label}: ${status[key] ? 'Live' : 'Mock'}`}
            className="group relative flex items-center gap-1 text-xs text-gray-500 cursor-default"
          >
            <span className={`w-2 h-2 rounded-full transition-transform group-hover:scale-125 ${
              status[key] ? 'bg-emerald-400' : 'bg-amber-400'
            }`} />
            <span className="hidden sm:inline text-gray-500">{label}</span>
          </span>
        ))}
      </div>
    </div>
  )
}
