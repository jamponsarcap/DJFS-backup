import { useState } from 'react'
import { BrainCircuit, ChevronDown, ChevronUp, AlertTriangle, FileText, Info } from 'lucide-react'
import { fetchAgentPortfolio } from '../api/client'
import type { AgentPortfolioInsights } from '../types'

interface Props { clientId: string }

export default function AgentPortfolioInsights({ clientId }: Props) {
  const [data, setData] = useState<AgentPortfolioInsights | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showRaw, setShowRaw] = useState(false)
  const [elapsed, setElapsed] = useState<number | null>(null)

  const run = async () => {
    setLoading(true)
    setError(null)
    setElapsed(null)
    const start = Date.now()
    try {
      const result = await fetchAgentPortfolio(clientId)
      setData(result)
      setElapsed((Date.now() - start) / 1000)
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? 'Failed to run Portfolio Insights Agent.'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  const fmt = (n: number | null | undefined, decimals = 2) =>
    n == null ? '—' : n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BrainCircuit size={18} className="text-indigo-500" />
          <h3 className="text-sm font-semibold text-gray-700">Portfolio Insights Agent</h3>
          <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">PortfolioInsightsAgent</span>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="flex items-center gap-2 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-60"
          style={{ backgroundColor: loading ? '#3730a3' : '#4338ca' }}
        >
          {loading ? (
            <>
              <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Running…
            </>
          ) : (
            <>
              <BrainCircuit size={13} />
              {data ? 'Re-run Agent' : 'Run Agent'}
            </>
          )}
        </button>
      </div>

      {/* Placeholder */}
      {!data && !loading && !error && (
        <p className="text-sm text-gray-400 italic">
          Click "Run Agent" to have the Portfolio Insights Agent query Fabric SQL and Azure AI Search
          and return a full structured portfolio payload with statement overlays and reconciliation notes.
        </p>
      )}

      {/* Error */}
      {error && (
        <p className="text-sm text-red-500 bg-red-50 border border-red-200 rounded-lg p-3">{error}</p>
      )}

      {/* Parse error from agent */}
      {data?.parse_error && (
        <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-1">
          <p className="font-medium">Agent returned an unexpected format</p>
          <p className="text-xs">{data.parse_error}</p>
          {data.raw_response && (
            <pre className="text-xs mt-2 bg-white border rounded p-2 overflow-auto max-h-48 whitespace-pre-wrap">
              {data.raw_response}
            </pre>
          )}
        </div>
      )}

      {/* Structured output */}
      {data && !data.parse_error && (
        <div className="space-y-5">

          {/* As-of + client confirmation */}
          {(data.as_of || data.client) && (
            <p className="text-xs text-gray-400">
              {data.client?.client_name && <span className="font-medium text-gray-600">{data.client.client_name} · </span>}
              {data.as_of && <span>As of {data.as_of}</span>}
            </p>
          )}

          {/* KPI metrics from agent */}
          {data.ui_metrics && (
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-gray-50 rounded-lg px-3 py-2">
                <p className="text-xs text-gray-500 mb-0.5">Portfolio Value</p>
                <p className="text-sm font-semibold text-gray-800">
                  {data.ui_metrics.total_portfolio_value?.value != null
                    ? `$${fmt(data.ui_metrics.total_portfolio_value.value, 0)}`
                    : '—'}
                </p>
                <p className="text-xs text-gray-400">{data.ui_metrics.total_portfolio_value?.currency ?? ''}</p>
              </div>
              <div className="bg-gray-50 rounded-lg px-3 py-2">
                <p className="text-xs text-gray-500 mb-0.5">Total Return</p>
                <p className={`text-sm font-semibold ${
                  (data.ui_metrics.total_return_pct?.value ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-500'
                }`}>
                  {data.ui_metrics.total_return_pct?.value != null
                    ? `${data.ui_metrics.total_return_pct.value >= 0 ? '+' : ''}${fmt(data.ui_metrics.total_return_pct.value)}%`
                    : '—'}
                </p>
                {data.ui_metrics.total_return_pct?.baseline_period_date && (
                  <p className="text-xs text-gray-400">from {data.ui_metrics.total_return_pct.baseline_period_date}</p>
                )}
              </div>
              <div className="bg-gray-50 rounded-lg px-3 py-2">
                <p className="text-xs text-gray-500 mb-0.5">YTD Return</p>
                <p className={`text-sm font-semibold ${
                  (data.ui_metrics.ytd_return_pct?.value ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-500'
                }`}>
                  {data.ui_metrics.ytd_return_pct?.value != null
                    ? `${data.ui_metrics.ytd_return_pct.value >= 0 ? '+' : ''}${fmt(data.ui_metrics.ytd_return_pct.value)}%`
                    : '—'}
                </p>
                {data.ui_metrics.ytd_return_pct?.note && (
                  <p className="text-xs text-amber-500">{data.ui_metrics.ytd_return_pct.note}</p>
                )}
              </div>
            </div>
          )}

          {/* Statement insights */}
          {(data.statement_insights?.highlights?.length ?? 0) > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <FileText size={13} className="text-indigo-400" />
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Statement Highlights</p>
              </div>
              <ul className="space-y-1">
                {data.statement_insights!.highlights!.map((h, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
                    {h}
                  </li>
                ))}
              </ul>
              {(data.statement_insights?.documents_used?.length ?? 0) > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {data.statement_insights!.documents_used!.map((d, i) => (
                    <span key={i} className="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded">
                      {d.metadata_storage_name || d.statement_date}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Reconciliation notes */}
          {(data.reconciliation_notes?.filter(Boolean).length ?? 0) > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <AlertTriangle size={13} className="text-amber-500" />
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Reconciliation Notes</p>
              </div>
              <ul className="space-y-1">
                {data.reconciliation_notes!.filter(Boolean).map((note, i) => (
                  <li key={i} className="text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded px-3 py-1.5">
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Missing data */}
          {(data.missing_data?.filter(Boolean).length ?? 0) > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Info size={13} className="text-gray-400" />
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Missing / Data Gaps</p>
              </div>
              <ul className="space-y-1">
                {data.missing_data!.filter(Boolean).map((item, i) => (
                  <li key={i} className="text-sm text-gray-500 flex items-start gap-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-gray-300 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Expandable raw payload + elapsed time */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => setShowRaw(s => !s)}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              {showRaw ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {showRaw ? 'Hide' : 'View'} full agent payload
            </button>
            {elapsed != null && (
              <span className="text-xs text-gray-400">
                Generated in {elapsed.toFixed(1)}s
              </span>
            )}
          </div>
          {showRaw && (
            <pre className="text-xs bg-gray-50 border border-gray-200 rounded-lg p-3 overflow-auto max-h-96 whitespace-pre-wrap">
              {JSON.stringify(data, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}