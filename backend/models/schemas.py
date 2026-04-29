from pydantic import BaseModel
from typing import Optional, List, Dict


class Client(BaseModel):
    id: str
    name: str
    rm_name: str
    last_review: str
    risk_profile: str


class Account(BaseModel):
    id: str
    type: str  # personal | joint | corporate
    name: str
    balance: float
    currency: str = "GBP"


class Holding(BaseModel):
    symbol: str
    name: str
    asset_class: str  # equity | fixed_income | cash | alternatives
    quantity: float
    current_price: float
    market_value: float
    cost_basis: float
    gain_loss: float
    gain_loss_pct: float
    weight: float


class PerformancePoint(BaseModel):
    date: str
    portfolio_value: float
    benchmark_value: float


class CashFlowPoint(BaseModel):
    month: str
    inflow: float
    outflow: float
    net: float


class RiskAlert(BaseModel):
    level: str  # high | medium | low
    category: str
    message: str


class AllocationBreakdown(BaseModel):
    equity: float
    fixed_income: float
    cash: float
    alternatives: float


class PortfolioData(BaseModel):
    client_id: str
    client_name: str
    total_value: float
    total_return: float
    total_return_pct: float
    ytd_return_pct: float
    accounts: List[Account]
    holdings: List[Holding]
    performance: List[PerformancePoint]
    cash_flows: List[CashFlowPoint]
    risk_alerts: List[RiskAlert]
    allocation: AllocationBreakdown


class InsightsResponse(BaseModel):
    narrative: str
    key_points: List[str]
    data_sources: List[str]
    generated_at: str


class AccountChange(BaseModel):
    account_name: str
    before: float
    after: float
    delta: float


class CashFlowChange(BaseModel):
    inflow_delta: float
    outflow_delta: float
    net_delta: float


class StatementDiff(BaseModel):
    total_value_before: float
    total_value_after: float
    total_value_delta: float
    account_changes: Dict[str, AccountChange]
    cash_flow_changes: Dict[str, CashFlowChange]
    transactions_count: int


class DocumentUploadResponse(BaseModel):
    filename: str
    status: str
    extracted_transactions: int
    summary: str
    diff: Optional[StatementDiff] = None


class ServiceStatus(BaseModel):
    fabric: bool
    openai: bool
    ai_search: bool
    doc_intelligence: bool
    market_data: bool
