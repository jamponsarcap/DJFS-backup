"""
Mock data that mirrors the schema of what Fabric OneLake / SQL would return.
All figures are illustrative only.
"""

MOCK_CLIENTS = [
    {
        "id": "cli_001",
        "name": "Sarah Chen",
        "rm_name": "James Hargreaves",
        "last_review": "2025-10-14",
        "risk_profile": "Balanced",
    },
    {
        "id": "cli_002",
        "name": "Thompson Family Trust",
        "rm_name": "Priya Mehta",
        "last_review": "2025-11-22",
        "risk_profile": "Growth",
    },
    {
        "id": "cli_003",
        "name": "Alford Capital Ltd",
        "rm_name": "James Hargreaves",
        "last_review": "2025-09-05",
        "risk_profile": "Conservative",
    },
]

# ── Shared helpers ─────────────────────────────────────────────────────────────

def _perf_series(start_val: float, months: int = 13):
    """Generate a simple upward-trending performance series."""
    import random, math
    random.seed(42)
    pts = []
    pval = start_val
    bval = start_val * 0.98
    for i in range(months):
        month = f"2024-{(i % 12) + 1:02d}"
        if i >= 12:
            month = f"2025-{(i - 12) % 12 + 1:02d}"
        pval *= 1 + random.gauss(0.007, 0.02)
        bval *= 1 + random.gauss(0.005, 0.015)
        pts.append({
            "date": month,
            "portfolio_value": round(pval, 2),
            "benchmark_value": round(bval, 2),
        })
    return pts


def _cashflow_series():
    import random
    random.seed(7)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return [
        {
            "month": m,
            "inflow": round(random.uniform(15000, 45000), 2),
            "outflow": round(random.uniform(8000, 25000), 2),
            "net": 0,
        }
        for m in months
    ]


def _add_net(series):
    for pt in series:
        pt["net"] = round(pt["inflow"] - pt["outflow"], 2)
    return series


# ── Client portfolios ──────────────────────────────────────────────────────────

MOCK_PORTFOLIOS = {
    "cli_001": {
        "client_id": "cli_001",
        "client_name": "Sarah Chen",
        "total_value": 1_284_750.00,
        "total_return": 184_750.00,
        "total_return_pct": 16.79,
        "ytd_return_pct": 8.42,
        "accounts": [
            {"id": "acc_001a", "type": "personal", "name": "ISA Portfolio",      "balance": 542_300.00, "currency": "USD"},
            {"id": "acc_001b", "type": "personal", "name": "General Investment",  "balance": 489_150.00, "currency": "USD"},
            {"id": "acc_001c", "type": "joint",    "name": "Joint Savings",       "balance": 253_300.00, "currency": "USD"},
        ],
        "holdings": [
            {"symbol": "AAPL",  "name": "Apple Inc.",            "asset_class": "equity",        "quantity": 480,   "current_price": 189.30, "market_value": 90864.00,  "cost_basis": 72000.00,  "gain_loss": 18864.00,  "gain_loss_pct": 26.2,  "weight": 7.07},
            {"symbol": "MSFT",  "name": "Microsoft Corp.",       "asset_class": "equity",        "quantity": 320,   "current_price": 415.20, "market_value": 132864.00, "cost_basis": 110000.00, "gain_loss": 22864.00,  "gain_loss_pct": 20.8,  "weight": 10.34},
            {"symbol": "VOD",   "name": "Vodafone Group plc",    "asset_class": "equity",        "quantity": 12000, "current_price": 0.74,   "market_value": 8880.00,   "cost_basis": 14400.00,  "gain_loss": -5520.00,  "gain_loss_pct": -38.3, "weight": 0.69},
            {"symbol": "UK10Y", "name": "UK Gilts 10Y",          "asset_class": "fixed_income",  "quantity": 350,   "current_price": 982.50, "market_value": 343875.00, "cost_basis": 350000.00, "gain_loss": -6125.00,  "gain_loss_pct": -1.75, "weight": 26.77},
            {"symbol": "CASH",  "name": "Cash & Equivalents",    "asset_class": "cash",          "quantity": 1,     "current_price": 192300, "market_value": 192300.00, "cost_basis": 192300.00, "gain_loss": 0.00,      "gain_loss_pct": 0.0,   "weight": 14.97},
            {"symbol": "GOLD",  "name": "iShares Gold ETF",      "asset_class": "alternatives",  "quantity": 2800,  "current_price": 162.00, "market_value": 453600.00, "cost_basis": 380000.00, "gain_loss": 73600.00,  "gain_loss_pct": 19.4,  "weight": 35.30},
            {"symbol": "REUK",  "name": "UK REIT Fund",          "asset_class": "alternatives",  "quantity": 820,   "current_price": 76.10,  "market_value": 62402.00,  "cost_basis": 55000.00,  "gain_loss": 7402.00,   "gain_loss_pct": 13.5,  "weight": 4.86},
        ],
        "performance": _perf_series(1_100_000),
        "cash_flows": _add_net(_cashflow_series()),
        "risk_alerts": [
            {"level": "medium", "category": "Concentration",    "message": "Fixed income allocation (26.8%) is below target range of 30–40% for a Balanced profile."},
            {"level": "low",    "category": "Currency",         "message": "3.2% USD exposure without currency hedge in place."},
        ],
        "allocation": {"equity": 18.10, "fixed_income": 26.77, "cash": 14.97, "alternatives": 40.16},
    },

    "cli_002": {
        "client_id": "cli_002",
        "client_name": "Thompson Family Trust",
        "total_value": 3_870_120.00,
        "total_return": 870_120.00,
        "total_return_pct": 29.0,
        "ytd_return_pct": 14.75,
        "accounts": [
            {"id": "acc_002a", "type": "personal",  "name": "Discretionary Portfolio", "balance": 2_110_500.00, "currency": "GBP"},
            {"id": "acc_002b", "type": "joint",     "name": "Family Trust Account",     "balance": 1_200_620.00, "currency": "GBP"},
            {"id": "acc_002c", "type": "corporate", "name": "Thompson Holdings Ltd",    "balance": 559_000.00,   "currency": "GBP"},
        ],
        "holdings": [
            {"symbol": "NVDA",  "name": "NVIDIA Corp.",          "asset_class": "equity",       "quantity": 1200,  "current_price": 875.40,  "market_value": 1050480.00, "cost_basis": 540000.00,  "gain_loss": 510480.00,  "gain_loss_pct": 94.5,  "weight": 27.14},
            {"symbol": "AMZN",  "name": "Amazon.com Inc.",       "asset_class": "equity",       "quantity": 1800,  "current_price": 185.20,  "market_value": 333360.00,  "cost_basis": 270000.00,  "gain_loss": 63360.00,   "gain_loss_pct": 23.5,  "weight": 8.61},
            {"symbol": "GSK",   "name": "GSK plc",               "asset_class": "equity",       "quantity": 15000, "current_price": 16.82,   "market_value": 252300.00,  "cost_basis": 225000.00,  "gain_loss": 27300.00,   "gain_loss_pct": 12.1,  "weight": 6.52},
            {"symbol": "TPVG",  "name": "TriplePoint Ventures",  "asset_class": "alternatives", "quantity": 4200,  "current_price": 98.50,   "market_value": 413700.00,  "cost_basis": 350000.00,  "gain_loss": 63700.00,   "gain_loss_pct": 18.2,  "weight": 10.69},
            {"symbol": "US30Y", "name": "US Treasury 30Y",       "asset_class": "fixed_income", "quantity": 800,   "current_price": 965.10,  "market_value": 772080.00,  "cost_basis": 800000.00,  "gain_loss": -27920.00,  "gain_loss_pct": -3.49, "weight": 19.95},
            {"symbol": "CASH",  "name": "Cash & Equivalents",    "asset_class": "cash",         "quantity": 1,     "current_price": 414200,  "market_value": 414200.00,  "cost_basis": 414200.00,  "gain_loss": 0,           "gain_loss_pct": 0,     "weight": 10.70},
            {"symbol": "INTU",  "name": "Intuit Inc.",           "asset_class": "equity",       "quantity": 780,   "current_price": 634.50,  "market_value": 494910.00,  "cost_basis": 390000.00,  "gain_loss": 104910.00,  "gain_loss_pct": 26.9,  "weight": 12.79},
            {"symbol": "PRIV",  "name": "Blackstone PE Fund",    "asset_class": "alternatives", "quantity": 1,     "current_price": 139090,  "market_value": 139090.00,  "cost_basis": 120000.00,  "gain_loss": 19090.00,   "gain_loss_pct": 15.9,  "weight": 3.60},
        ],
        "performance": _perf_series(3_000_000),
        "cash_flows": _add_net(_cashflow_series()),
        "risk_alerts": [
            {"level": "high",   "category": "Concentration",  "message": "NVIDIA represents 27.1% of total portfolio – exceeds 20% single-stock limit for Growth profile."},
            {"level": "medium", "category": "Liquidity",      "message": "Private equity allocation (14.3%) locks capital until 2027 fund maturity."},
            {"level": "low",    "category": "Interest Rate",  "message": "Long-duration US Treasuries are sensitive to Fed rate decisions (current duration: 24y)."},
        ],
        "allocation": {"equity": 55.06, "fixed_income": 19.95, "cash": 10.70, "alternatives": 14.29},
    },

    "cli_003": {
        "client_id": "cli_003",
        "client_name": "Alford Capital Ltd",
        "total_value": 8_432_000.00,
        "total_return": 432_000.00,
        "total_return_pct": 5.4,
        "ytd_return_pct": 3.20,
        "accounts": [
            {"id": "acc_003a", "type": "corporate", "name": "Operating Account",   "balance": 2_100_000.00, "currency": "GBP"},
            {"id": "acc_003b", "type": "corporate", "name": "Reserve Portfolio",   "balance": 4_980_000.00, "currency": "GBP"},
            {"id": "acc_003c", "type": "corporate", "name": "Capital Reserve",     "balance": 1_352_000.00, "currency": "GBP"},
        ],
        "holdings": [
            {"symbol": "UK5Y",  "name": "UK Gilts 5Y",           "asset_class": "fixed_income",  "quantity": 2500,  "current_price": 978.20,  "market_value": 2445500.00, "cost_basis": 2500000.00, "gain_loss": -54500.00,  "gain_loss_pct": -2.18, "weight": 29.00},
            {"symbol": "EU5Y",  "name": "EUR Corp Bond ETF",     "asset_class": "fixed_income",  "quantity": 1200,  "current_price": 104.50,  "market_value": 1254000.00, "cost_basis": 1200000.00, "gain_loss": 54000.00,   "gain_loss_pct": 4.5,   "weight": 14.87},
            {"symbol": "CASH",  "name": "GBP Cash Deposits",     "asset_class": "cash",          "quantity": 1,     "current_price": 2352000, "market_value": 2352000.00, "cost_basis": 2352000.00, "gain_loss": 0,           "gain_loss_pct": 0,     "weight": 27.90},
            {"symbol": "MMKT",  "name": "Sterling Money Market", "asset_class": "cash",          "quantity": 9500,  "current_price": 105.20,  "market_value": 999400.00,  "cost_basis": 950000.00,  "gain_loss": 49400.00,   "gain_loss_pct": 5.2,   "weight": 11.85},
            {"symbol": "SHRY",  "name": "iShares Short Gilt",    "asset_class": "fixed_income",  "quantity": 5400,  "current_price": 73.40,   "market_value": 396360.00,  "cost_basis": 378000.00,  "gain_loss": 18360.00,   "gain_loss_pct": 4.86,  "weight": 4.70},
            {"symbol": "INFRA", "name": "UK Infrastructure Fund","asset_class": "alternatives",  "quantity": 3800,  "current_price": 254.10,  "market_value": 965580.00,  "cost_basis": 912000.00,  "gain_loss": 53580.00,   "gain_loss_pct": 5.87,  "weight": 11.45},
            {"symbol": "BRKR",  "name": "Barclays Equity",       "asset_class": "equity",        "quantity": 2100,  "current_price": 9.50,    "market_value": 19950.00,   "cost_basis": 18000.00,   "gain_loss": 1950.00,    "gain_loss_pct": 10.8,  "weight": 0.23},
        ],
        "performance": _perf_series(8_000_000),
        "cash_flows": _add_net(_cashflow_series()),
        "risk_alerts": [
            {"level": "low",    "category": "Yield",   "message": "Portfolio yield (3.8%) is below inflation (4.1%); real returns are currently negative."},
            {"level": "low",    "category": "Mandate", "message": "Equity exposure (0.23%) is minimal – confirm this aligns with updated investment mandate."},
        ],
        "allocation": {"equity": 0.23, "fixed_income": 48.57, "cash": 39.75, "alternatives": 11.45},
    },
}

# Pre-canned RM narratives (used when OpenAI is not configured)
MOCK_NARRATIVES = {
    "cli_001": {
        "narrative": (
            "Sarah Chen's portfolio has delivered strong performance over the review period, "
            "generating a total return of 16.8% against a benchmark of 12.1%. The alternatives "
            "allocation – led by the iShares Gold ETF – has been the primary driver of outperformance, "
            "contributing +5.7% in absolute terms. Equities are performing broadly in line with expectations, "
            "with Apple and Microsoft both showing double-digit gains. The main area for review is the "
            "fixed income underweight: at 26.8%, the gilt position sits below the 30–40% target range "
            "for a Balanced mandate, leaving the portfolio marginally more volatile than the policy benchmark. "
            "Cash flow patterns remain healthy, with consistent monthly net inflows averaging £18,200. "
            "No immediate action is required, but we recommend discussing a rebalance into gilts at the upcoming review."
        ),
        "key_points": [
            "Total return of +16.8% vs benchmark +12.1% – outperforming by 4.7%.",
            "Gold ETF is the top contributor at +19.4% YTD.",
            "Fixed income is underweight vs Balanced mandate – rebalance discussion recommended.",
            "Steady net cash inflows averaging £18,200/month.",
            "No high-severity risk flags.",
        ],
        "data_sources": ["Fabric SQL (accounts, holdings)", "Mock market prices", "Pre-canned narrative (Azure OpenAI not configured)"],
    },
    "cli_002": {
        "narrative": (
            "The Thompson Family Trust has delivered exceptional returns of 29.0% since inception, "
            "significantly outpacing its Growth benchmark of 18.3%. NVIDIA has been a standout holding, "
            "nearly doubling in value (+94.5%), but now represents 27.1% of the total portfolio – well above "
            "the 20% single-stock concentration limit. This is flagged as a high-priority item for the review. "
            "Across all three account structures (discretionary, family trust, and corporate), the portfolio "
            "exhibits strong diversification by asset class and geography, though private equity illiquidity "
            "warrants attention ahead of the 2027 fund maturity. YTD performance of 14.75% is ahead of target "
            "and the cash position provides adequate runway for near-term rebalancing without forced selling."
        ),
        "key_points": [
            "Outstanding total return of +29.0% – driven primarily by NVIDIA (+94.5%).",
            "HIGH ALERT: NVIDIA concentration at 27.1% exceeds the 20% single-stock limit.",
            "Private equity (14.3%) locks capital until 2027 – liquidity planning required.",
            "Cash buffer of 10.7% provides flexibility for rebalancing.",
            "Three-account structure (personal + joint + corporate) is well co-ordinated.",
        ],
        "data_sources": ["Fabric SQL (accounts, holdings)", "Mock market prices", "Pre-canned narrative (Azure OpenAI not configured)"],
    },
    "cli_003": {
        "narrative": (
            "Alford Capital Ltd maintains a highly conservative capital preservation mandate, with 88.3% "
            "of assets held in fixed income and cash. The portfolio has returned +5.4% since inception, "
            "broadly in line with short-duration gilt yields. The primary concern flagged is a real return "
            "challenge: with the portfolio yielding 3.8% and CPI running at 4.1%, purchasing power is being "
            "modestly eroded. The infrastructure allocation (11.5%) provides a partial inflation linkage and "
            "continues to perform well (+5.9%). Cash management across the GBP deposit and sterling money "
            "market accounts appears efficient, with strong liquidity coverage for operational requirements. "
            "We recommend reviewing whether any modest increase in index-linked gilts or inflation-linked "
            "alternatives could address the yield gap without breaching the conservative mandate."
        ),
        "key_points": [
            "Conservative mandate maintained: 88.3% in fixed income and cash.",
            "Real returns are marginally negative (yield 3.8% vs CPI 4.1%).",
            "Infrastructure allocation (+5.9%) is the strongest performer.",
            "High liquidity (39.75% cash) meets operational requirements comfortably.",
            "Consider index-linked instruments to close the inflation gap.",
        ],
        "data_sources": ["Fabric SQL (accounts, holdings)", "Mock market prices", "Pre-canned narrative (Azure OpenAI not configured)"],
    },
}
