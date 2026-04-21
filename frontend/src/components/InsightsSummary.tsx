import { useState } from 'react'
import { Sparkles, ChevronDown, ChevronUp, Database } from 'lucide-react'
import { fetchInsights } from '../api/client'
import type { InsightsResponse } from '../types'

interface Props { clientId: string }

export default function InsightsSummary({ clientId }: Props) {
  const [insights, setInsights] = useState<InsightsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSources, setShowSources] = useState(false)

  const generate = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchInsights(clientId)
      setInsights(data)
    } catch {
      setError('Failed to generate insights. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sparkles size={18} className="text-teal-500" />
          <h3 className="text-sm font-semibold text-gray-700">AI-Generated RM Briefing</h3>
        </div>
        <button
          onClick={generate}
          disabled={loading}
          className="flex items-center gap-2 bg-navy-800 hover:bg-navy-700 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-60"
          style={{ backgroundColor: loading ? '#163055' : '#0A1628' }}
        >
          {loading ? (
            <>
              <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Generating…
            </>
          ) : (
            <>
              <Sparkles size={13} />
              {insights ? 'Regenerate' : 'Generate Briefing'}
            </>
          )}
        </button>
      </div>

      {error && (
        <p className="text-sm text-red-500 bg-red-50 border border-red-200 rounded-lg p-3">{error}</p>
      )}

      {!insights && !loading && !error && (
        <p className="text-sm text-gray-400 italic">
          Click "Generate Briefing" to run the Portfolio Intelligence Agent and produce an RM pre-review summary.
        </p>
      )}

      {insights && (
        <div className="space-y-4">
          <p className="text-sm text-gray-700 leading-relaxed">{insights.narrative}</p>

          {insights.key_points.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Key Points</p>
              <ul className="space-y-1">
                {insights.key_points.map((pt, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="mt-1 w-1.5 h-1.5 rounded-full bg-teal-500 shrink-0" />
                    {pt}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <button
            onClick={() => setShowSources(s => !s)}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            <Database size={12} />
            Data sources
            {showSources ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>

          {showSources && (
            <div className="flex flex-wrap gap-2">
              {insights.data_sources.map((s, i) => (
                <span key={i} className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded">{s}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
