import { useState, useEffect, useRef } from 'react'
import { Sparkles, Database } from 'lucide-react'
import { fetchInsights } from '../api/client'
import type { InsightsResponse } from '../types'

interface Props { clientId: string }

// Split prose into individual sentences for display.
// Splits on '. ' followed by a capital letter to avoid breaking decimals / abbreviations.
function splitSentences(text: string): string[] {
  return text
    .split(/(?<=\.)\s+(?=[A-Z])/)
    .map(s => s.trim())
    .filter(Boolean)
}

// ── Live elapsed timer ────────────────────────────────────────────────────────

function useLiveTimer(running: boolean) {
  const [secs, setSecs] = useState(0)
  const ref = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (running) {
      setSecs(0)
      ref.current = setInterval(() => setSecs(s => s + 1), 1000)
    } else {
      if (ref.current) clearInterval(ref.current)
    }
    return () => { if (ref.current) clearInterval(ref.current) }
  }, [running])

  return secs
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function InsightsSummary({ clientId }: Props) {
  const [insights, setInsights] = useState<InsightsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState<number | null>(null)
  const liveSecs = useLiveTimer(loading)

  const generate = async () => {
    setLoading(true)
    setError(null)
    setElapsed(null)
    const start = Date.now()
    try {
      const data = await fetchInsights(clientId)
      setInsights(data)
      setElapsed((Date.now() - start) / 1000)
    } catch {
      setError('Failed to generate insights. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const sentences = insights ? splitSentences(insights.narrative) : []

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col">

      {/* ── Header ── */}
      <div className="flex items-start justify-between px-5 pt-5 pb-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 bg-gradient-to-br from-teal-400 to-teal-600 p-2 rounded-lg shadow-sm">
            <Sparkles size={14} className="text-white" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-gray-900 leading-tight">AI-Generated RM Briefing</h3>
            <div className="mt-0.5">
              {elapsed != null && !loading ? (
                <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
                  Ready · {elapsed.toFixed(1)}s
                </span>
              ) : loading ? (
                <span className="flex items-center gap-1 text-xs text-teal-600 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse inline-block" />
                  Running · {liveSecs}s
                </span>
              ) : (
                <span className="text-xs text-gray-400">Pre-review summary · SummarizationAgent</span>
              )}
            </div>
          </div>
        </div>

        <button
          onClick={generate}
          disabled={loading}
          className="flex items-center gap-2 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-all disabled:opacity-60 shadow-sm hover:shadow-md active:scale-95"
          style={{ backgroundColor: loading ? '#0f7766' : '#0d9488' }}
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

      {/* ── Body ── */}
      <div className="flex-1 px-5 pb-5">

        {error && (
          <p className="text-sm text-red-500 bg-red-50 border border-red-200 rounded-lg p-3">{error}</p>
        )}

        {!insights && !loading && !error && (
          <div className="flex flex-col items-center justify-center py-10 gap-3">
            <div className="bg-gray-50 rounded-full p-4">
              <Sparkles size={22} className="text-gray-300" />
            </div>
            <p className="text-sm text-gray-400 text-center max-w-xs">
              Click <span className="font-medium text-gray-500">"Generate Briefing"</span> to produce
              a concise pre-meeting advisor briefing for this client.
            </p>
          </div>
        )}

        {loading && (
          <div className="flex flex-col items-center justify-center py-10 gap-4">
            <div className="relative">
              <div className="w-10 h-10 rounded-full border-2 border-teal-100 border-t-teal-500 animate-spin" />
              <Sparkles size={14} className="text-teal-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600 font-medium">Generating briefing…</p>
              <p className="text-xs text-gray-400 mt-0.5">Analysing portfolio data and documents</p>
            </div>
          </div>
        )}

        {insights && (
          <div className="border-l-2 border-teal-400 pl-4 space-y-2.5">
            {sentences.map((sentence, i) => (
              <p key={i} className="text-sm text-gray-700 leading-relaxed">
                {sentence}
              </p>
            ))}
          </div>
        )}

      </div>

      {/* ── Footer ── */}
      {insights && (
        <div className="flex items-center gap-2 px-5 py-3 border-t border-gray-100 bg-gray-50/50 rounded-b-xl">
          <Database size={11} className="text-gray-300 shrink-0" />
          <div className="flex items-center flex-wrap">
            {insights.data_sources.map((s, i) => (
              <span key={i} className="text-xs text-gray-400">
                {i > 0 && <span className="mx-1.5 text-gray-200">·</span>}
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}
