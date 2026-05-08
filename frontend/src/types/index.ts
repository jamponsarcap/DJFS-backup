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
