import { useState, useEffect, useRef } from 'react'
import {
  Sparkles, Database, User, DollarSign, TrendingUp,
  BarChart2, ArrowUpDown, AlertTriangle, FileText,
} from 'lucide-react'
import { fetchInsights } from '../api/client'
import type { InsightsResponse } from '../types'

interface Props { clientId: string }

// ── Markdown helpers ──────────────────────────────────────────────────────────

function renderInline(text: string) {
  // Convert **bold** to <strong> spans
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  return parts.map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={i} className="font-semibold text-gray-800">{part.slice(2, -2)}</strong>
      : <span key={i}>{part}</span>
  )
}

interface Section { heading: string; items: string[] }

function parseNarrative(text: string): Section[] {
  const sections: Section[] = []
  let current: Section | null = null

  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) continue

    if (/^#{1,3} /.test(line)) {
      if (current) sections.push(current)
      current = { heading: line.replace(/^#{1,3} /, '').replace(/:$/, ''), items: [] }
    } else if (/^[-*•] /.test(line)) {
      if (!current) current = { heading: '', items: [] }
      current.items.push(line.replace(/^[-*•] /, ''))
    } else {
      // Non-bullet paragraph line — treat as a plain item
      if (!current) current = { heading: '', items: [] }
      current.items.push(line)
    }
  }
  if (current) sections.push(current)
  return sections.filter(s => s.heading || s.items.length > 0)
}

const SECTION_ICONS: { match: RegExp; icon: React.ReactNode; color: string }[] = [
  { match: /client|snapshot/i,    icon: <User size={13} />,          color: 'text-blue-500' },
  { match: /value|portfolio/i,    icon: <DollarSign size={13} />,    color: 'text-emerald-500' },
  { match: /performance|return/i, icon: <TrendingUp size={13} />,    color: 'text-teal-500' },
  { match: /holding|allocation/i, icon: <BarChart2 size={13} />,     color: 'text-indigo-500' },
  { match: /cash.?flow/i,         icon: <ArrowUpDown size={13} />,   color: 'text-purple-500' },
  { match: /risk|alert/i,         icon: <AlertTriangle size={13} />, color: 'text-amber-500' },
  { match: /statement|document/i, icon: <FileText size={13} />,      color: 'text-gray-500' },
]

function sectionIcon(heading: string) {
  const match = SECTION_ICONS.find(s => s.match.test(heading))
  return match ?? { icon: <Sparkles size={13} />, color: 'text-teal-400' }
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

  const sections = insights ? parseNarrative(insights.narrative) : []

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
            <div className="flex items-center gap-2 mt-0.5">
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
      <div className="flex-1 px-5 py-4">

        {error && (
          <p className="text-sm text-red-500 bg-red-50 border border-red-200 rounded-lg p-3">{error}</p>
        )}

        {!insights && !loading && !error && (
          <div className="flex flex-col items-center justify-center py-10 gap-3">
            <div className="bg-gray-50 rounded-full p-4">
              <Sparkles size={22} className="text-gray-300" />
            </div>
            <p className="text-sm text-gray-400 text-center max-w-xs">
              Click <span className="font-medium text-gray-500">"Generate Briefing"</span> to run the
              Summarization Agent and produce a pre-review summary for this client.
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
              <p className="text-sm text-gray-600 font-medium">Agent is running…</p>
              <p className="text-xs text-gray-400 mt-0.5">Querying Fabric SQL and Azure AI Search</p>
            </div>
          </div>
        )}

        {insights && sections.length > 0 && (
          <div className="space-y-3">
            {sections.map((section, si) => {
              const { icon, color } = sectionIcon(section.heading)
              return (
                <div key={si} className="rounded-lg border border-gray-100 bg-gray-50/60 overflow-hidden">
                  {section.heading && (
                    <div className="flex items-center gap-2 px-3 py-2 bg-white border-b border-gray-100">
                      <span className={color}>{icon}</span>
                      <span className="text-xs font-semibold text-gray-700">{section.heading}</span>
                    </div>
                  )}
                  <ul className="px-3 py-2 space-y-1">
                    {section.items.map((item, ii) => (
                      <li key={ii} className="flex items-start gap-2 text-sm text-gray-600">
                        <span className="mt-1.5 w-1 h-1 rounded-full bg-gray-300 shrink-0" />
                        <span className="leading-relaxed">{renderInline(item)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}
          </div>
        )}

        {/* Fallback: if the narrative doesn't parse into sections, render it plainly */}
        {insights && sections.length === 0 && (
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{insights.narrative}</p>
        )}
      </div>

      {/* ── Footer ── */}
      {insights && (
        <div className="flex items-center gap-2 px-5 py-3 border-t border-gray-100 bg-gray-50/50 rounded-b-xl">
          <Database size={11} className="text-gray-300 shrink-0" />
          <div className="flex items-center gap-1.5 flex-wrap">
            {insights.data_sources.map((s, i) => (
              <span key={i} className="text-xs text-gray-400">{i > 0 && <span className="mr-1.5 text-gray-200">·</span>}{s}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}