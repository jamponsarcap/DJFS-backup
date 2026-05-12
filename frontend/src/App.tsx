import { useState, useEffect } from 'react'
import { BarChart2, RefreshCw } from 'lucide-react'
import ClientSelector from './components/ClientSelector'
import StatusBar from './components/StatusBar'
import KpiCards from './components/KpiCards'
import AllocationChart from './components/AllocationChart'
import AccountBalances from './components/AccountBalances'
import PerformanceChart from './components/PerformanceChart'
import HoldingsTable from './components/HoldingsTable'
import CashFlowChart from './components/CashFlowChart'
import RiskAlerts from './components/RiskAlerts'
import InsightsSummary from './components/InsightsSummary'
import DocumentUpload from './components/DocumentUpload'
import StatementDiffModal from './components/StatementDiffModal'
import HoldingsTrendChart from './components/HoldingsTrendChart'
import DocumentList from './components/DocumentList'
import { fetchClients, fetchPortfolio, fetchStatus, refreshMarketData, fetchRefreshStatus } from './api/client'
import type { Client, PortfolioData, ServiceStatus, DocumentUploadResponse } from './types'

export default function App() {
  const [clients, setClients] = useState<Client[]>([])
  const [selected, setSelected] = useState<Client | null>(null)
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null)
  const [status, setStatus] = useState<ServiceStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [diffResult, setDiffResult] = useState<DocumentUploadResponse | null>(null)
  const [marketRefreshing, setMarketRefreshing] = useState(false)
  const [lastRefreshed, setLastRefreshed] = useState<string | null>(null)
  const [nextRefreshAt, setNextRefreshAt] = useState<number | null>(null)
  const [cooldownSecs, setCooldownSecs] = useState(0)
  const [docListKey, setDocListKey] = useState(0)
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0)

  useEffect(() => {
    fetchRefreshStatus().then(s => {
      if (s.last_refreshed) setLastRefreshed(s.last_refreshed)
      if (s.next_refresh_allowed) {
        const next = new Date(s.next_refresh_allowed).getTime()
        if (next > Date.now()) setNextRefreshAt(next)
      }
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!nextRefreshAt) return
    const tick = () => {
      const secs = Math.max(0, Math.ceil((nextRefreshAt - Date.now()) / 1000))
      setCooldownSecs(secs)
      if (secs === 0) setNextRefreshAt(null)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [nextRefreshAt])

  const handleMarketRefresh = async () => {
    setMarketRefreshing(true)
    try {
      const result = await refreshMarketData()
      setLastRefreshed(result.refreshed_at)
      setNextRefreshAt(new Date(result.next_refresh_allowed).getTime())
      if (selected) loadPortfolio(selected.id)
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'Market data refresh failed.'
      setError(msg)
    } finally {
      setMarketRefreshing(false)
    }
  }

  useEffect(() => {
    fetchClients()
      .then(data => {
        setClients(data)
        if (data.length === 0) return
        const savedId = localStorage.getItem('rm_selected_client')
        const restored = savedId ? data.find(c => c.id === savedId) : null
        setSelected(restored ?? data[0])
      })
      .catch(() => setError('Cannot reach backend. Start the FastAPI server on port 8000.'))

    fetchStatus()
      .then(setStatus)
      .catch(() => {/* status is optional */})
  }, [])

  const handleSelectClient = (client: Client) => {
    localStorage.setItem('rm_selected_client', client.id)
    setSelected(client)
  }

  const loadPortfolio = (clientId: string) => {
    setLoading(true)
    setError(null)
    fetchPortfolio(clientId)
      .then(setPortfolio)
      .catch(() => setError('Failed to load portfolio data.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (!selected) return
    loadPortfolio(selected.id)
  }, [selected])

  const handleUploadComplete = (result: DocumentUploadResponse) => {
    setDiffResult(result)
    setDocListKey(k => k + 1)
    if (selected) loadPortfolio(selected.id)
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* ── Navbar ─────────────────────────────────────────────────────────── */}
      <header style={{ backgroundColor: '#0A1628' }} className="shadow-xl sticky top-0 z-30">
        {/* Teal accent stripe */}
        <div className="h-0.5 bg-gradient-to-r from-teal-500 via-teal-400 to-teal-600" />

        {/* Main row */}
        <div className="max-w-screen-2xl mx-auto px-6 py-3.5 flex items-center justify-between gap-4">
          {/* Brand */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="bg-gradient-to-br from-teal-400 to-teal-600 p-2 rounded-lg shadow-md">
              <BarChart2 size={18} className="text-white" />
            </div>
            <div className="leading-tight">
              <div className="text-white font-bold text-base tracking-tight">RM Insights</div>
              <div className="text-teal-400 text-xs font-medium">Agentic Portfolio Intelligence</div>
            </div>
          </div>

          {/* Client selector — right-aligned */}
          <ClientSelector clients={clients} selected={selected} onSelect={handleSelectClient} />
        </div>

        {/* Status sub-bar */}
        {status && (
          <div style={{ backgroundColor: '#071020' }} className="border-t border-white/5">
            <div className="max-w-screen-2xl mx-auto px-6 py-1.5">
              <StatusBar status={status} />
            </div>
          </div>
        )}
      </header>

      {/* ── Main ───────────────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-screen-2xl mx-auto w-full px-6 py-6 space-y-6">

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-5 py-4 text-sm">
            {error}
          </div>
        )}

        {loading && !portfolio && (
          <div className="flex items-center justify-center py-24">
            <div className="flex items-center gap-3 text-gray-400">
              <RefreshCw size={20} className="animate-spin" />
              <span>Loading portfolio data…</span>
            </div>
          </div>
        )}

        {portfolio && (
          <>
            {/* Client header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold text-gray-900">{portfolio.client_name}</h1>
                <p className="text-sm text-gray-500 mt-0.5">
                  RM: {selected?.rm_name} &nbsp;·&nbsp;
                  Risk profile: <span className="font-medium text-gray-700">{selected?.risk_profile}</span> &nbsp;·&nbsp;
                  Last review: {selected?.last_review}
                </p>
              </div>
              {loading && (
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <RefreshCw size={16} className="animate-spin" />
                  <span>Refreshing…</span>
                </div>
              )}
            </div>

            {/* AI Briefing */}
            <InsightsSummary clientId={portfolio.client_id} />

            {/* KPI row */}
            <KpiCards data={portfolio} />

            {/* Allocation + Accounts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <AllocationChart allocation={portfolio.allocation} />
              <AccountBalances accounts={portfolio.accounts} />
            </div>

            {/* Performance */}
            <PerformanceChart data={portfolio.performance} />

            {/* Holdings */}
            <HoldingsTable
              holdings={portfolio.holdings}
              currency={portfolio.accounts[0]?.currency ?? 'GBP'}
              onRefresh={handleMarketRefresh}
              refreshing={marketRefreshing}
              cooldownSecs={cooldownSecs}
              lastRefreshed={lastRefreshed}
            />

            {/* Holdings price trend */}
            <HoldingsTrendChart
              clientId={portfolio.client_id}
              refreshTrigger={lastRefreshed}
            />

            {/* Cash flow + Risk alerts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <CashFlowChart data={portfolio.cash_flows} />
              <RiskAlerts alerts={portfolio.risk_alerts} />
            </div>

            {/* Document upload + Lakehouse document list */}
            <div className="w-full grid grid-cols-1 lg:grid-cols-2 gap-6">
              <DocumentUpload
                clientId={portfolio.client_id}
                onUploadComplete={handleUploadComplete}
                historyRefreshKey={historyRefreshKey}
              />
              <DocumentList
                clientId={portfolio.client_id}
                refreshKey={docListKey}
                onDelete={() => setHistoryRefreshKey(k => k + 1)}
              />
            </div>
          </>
        )}
      </main>

      <footer style={{ backgroundColor: '#071020' }} className="border-t border-white/5 mt-4">
        <div className="max-w-screen-2xl mx-auto px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-4">

          {/* Left — brand */}
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-teal-400 to-teal-600 p-1.5 rounded-md">
              <BarChart2 size={13} className="text-white" />
            </div>
            <div>
              <div className="text-white text-sm font-bold leading-tight">RM Insights</div>
              <div className="text-gray-500 text-xs mt-0.5">Agentic Industry Hackathon 2026</div>
            </div>
          </div>

          {/* Centre — team */}
          <div className="text-center">
            <div className="text-gray-400 text-xs font-medium">Team DJ FS</div>
            <div className="text-gray-600 text-xs mt-0.5">Capgemini · Powered by Microsoft Azure</div>
          </div>

          {/* Right — tech stack */}
          <div className="flex items-center gap-2 flex-wrap justify-center sm:justify-end">
            {['Azure AI Foundry', 'Microsoft Fabric', 'Azure OpenAI'].map(tag => (
              <span key={tag} className="text-xs text-gray-500 border border-white/10 rounded px-2 py-0.5">
                {tag}
              </span>
            ))}
          </div>

        </div>
      </footer>

      {/* Diff modal — shown after a successful upload */}
      {diffResult?.diff && (
        <StatementDiffModal
          filename={diffResult.filename}
          diff={diffResult.diff}
          onClose={() => setDiffResult(null)}
        />
      )}
    </div>
  )
}
