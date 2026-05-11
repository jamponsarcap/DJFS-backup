export interface Client {
  id: string
  name: string
  rm_name: string
  last_review: string
  risk_profile: string
}

export interface Account {
  id: string
  type: 'personal' | 'joint' | 'corporate'
  name: string
  balance: number
  currency: string
}

export interface Holding {
  symbol: string
  name: string
  asset_class: 'equity' | 'fixed_income' | 'cash' | 'alternatives'
  quantity: number
  current_price: number
  market_value: number
  cost_basis: number
  gain_loss: number
  gain_loss_pct: number
  weight: number
}

export interface PerformancePoint {
  date: string
  portfolio_value: number
  benchmark_value: number
}

export interface CashFlowPoint {
  month: string
  inflow: number
  outflow: number
  net: number
}

export interface RiskAlert {
  level: 'high' | 'medium' | 'low'
  category: string
  message: string
}

export interface AllocationBreakdown {
  equity: number
  fixed_income: number
  cash: number
  alternatives: number
}

export interface PortfolioData {
  client_id: string
  client_name: string
  total_value: number
  total_return: number
  total_return_pct: number
  ytd_return_pct: number
  accounts: Account[]
  holdings: Holding[]
  performance: PerformancePoint[]
  cash_flows: CashFlowPoint[]
  risk_alerts: RiskAlert[]
  allocation: AllocationBreakdown
}

export interface InsightsResponse {
  narrative: string
  key_points: string[]
  data_sources: string[]
  generated_at: string
}

export interface ServiceStatus {
  fabric: boolean
  openai: boolean
  ai_search: boolean
  doc_intelligence: boolean
  market_data: boolean
  foundry_summarization_agent: boolean
  foundry_portfolio_agent: boolean
}

// PortfolioInsightsAgent response shape (top-level fields we display)
export interface AgentPortfolioInsights {
  client?: {
    client_id: string
    client_name: string
    risk_tolerance: string
    rm_name: string
    last_review: string
  }
  as_of?: string
  ui_metrics?: {
    total_portfolio_value?: { value: number | null; currency: string }
    total_return_pct?: { value: number | null; baseline_period_date: string | null }
    ytd_return_pct?: { value: number | null; baseline_period_date: string | null; note?: string }
  }
  statement_insights?: {
    documents_used?: { metadata_storage_name: string; metadata_storage_path: string; statement_date: string; statement_period: string }[]
    highlights?: string[]
  }
  reconciliation_notes?: string[]
  missing_data?: string[]
  // full payload fields kept as unknown for expandable raw view
  charts?: unknown
  tables?: unknown
  // error fallback from parse failure
  error?: string
  raw_response?: string
  parse_error?: string
}

export interface AccountChange {
  account_name: string
  before: number
  after: number
  delta: number
}

export interface CashFlowChange {
  inflow_delta: number
  outflow_delta: number
  net_delta: number
}

export interface StatementDiff {
  total_value_before: number
  total_value_after: number
  total_value_delta: number
  account_changes: Record<string, AccountChange>
  cash_flow_changes: Record<string, CashFlowChange>
  transactions_count: number
}

export interface DocumentUploadResponse {
  filename: string
  status: string
  extracted_transactions: number
  summary: string
  diff?: StatementDiff
  lakehouse_path?: string
  indexer_triggered?: boolean
}
