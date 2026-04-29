"""
Microsoft Fabric / OneLake SQL service.

Uses pytds / python-tds (pure Python, no ODBC driver required) with an
Entra ID access token obtained via InteractiveBrowserCredential.

Falls back to mock data when FABRIC_SERVER / FABRIC_DATABASE are not set.
"""

import config
from data.mock_data import MOCK_CLIENTS, MOCK_PORTFOLIOS


def _f(val) -> float:
    """Safe float conversion for Decimal / numeric DB values."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


class FabricService:
    def __init__(self):
        self._live = config.fabric_enabled()
        self._conn = None
        if self._live:
            try:
                self._connect()
            except Exception as e:
                print(f"[FabricService] Could not connect to Fabric ({e}) – falling back to mock data")
                self._live = False
        else:
            print("[FabricService] Running in mock mode (FABRIC_SERVER not set)")

    def _connect(self):
        from azure.identity import InteractiveBrowserCredential
        import pytds
        import certifi

        credential = InteractiveBrowserCredential()
        token = credential.get_token("https://database.windows.net/.default")

        self._conn = pytds.connect(
            server=config.FABRIC_SERVER,
            database=config.FABRIC_DATABASE,
            access_token_callable=lambda: token.token,
            autocommit=True,
            cafile=certifi.where(),
            as_dict=True,
        )
        print("[FabricService] Connected to Fabric SQL via Entra ID token")

    def _cursor(self):
        try:
            c = self._conn.cursor()
            c.execute("SELECT 1")
            return self._conn.cursor()
        except Exception:
            self._connect()
            return self._conn.cursor()

    async def get_clients(self) -> list:
        if not self._live:
            return MOCK_CLIENTS

        cur = self._cursor()
        cur.execute("""
            SELECT client_id AS id,
                   client_name AS name,
                   'N/A' AS rm_name,
                   '2025-01-01' AS last_review,
                   risk_tolerance AS risk_profile
            FROM dbo.clients
            ORDER BY client_name
        """)
        return list(cur.fetchall())

    async def get_portfolio_data(self, client_id: str) -> dict | None:
        if not self._live:
            return MOCK_PORTFOLIOS.get(client_id)

        cur = self._cursor()

        # Client
        cur.execute("""
            SELECT client_id, client_name
            FROM dbo.clients WHERE client_id = %s
        """, (client_id,))
        row = cur.fetchone()
        if not row:
            return None
        portfolio = {"client_id": row["client_id"], "client_name": row["client_name"]}

        # Accounts
        cur.execute("""
            SELECT account_id AS id, account_type AS type,
                   account_name AS name, balance, currency
            FROM dbo.accounts WHERE client_id = %s ORDER BY account_type
        """, (client_id,))
        portfolio["accounts"] = [
            {**r, "balance": _f(r["balance"])} for r in cur.fetchall()
        ]

        # Holdings
        cur.execute("""
            SELECT symbol, name, asset_class, quantity,
                   0.0 AS current_price,
                   market_value,
                   0.0 AS cost_basis,
                   0.0 AS gain_loss,
                   gain_loss_pct, weight
            FROM dbo.holdings WHERE client_id = %s ORDER BY weight DESC
        """, (client_id,))
        holdings = [
            {k: _f(v) if k not in ("symbol", "name", "asset_class") else v
             for k, v in r.items()}
            for r in cur.fetchall()
        ]
        portfolio["holdings"] = holdings

        # Total value = sum of all account balances (source of truth)
        total_value = sum(a["balance"] for a in portfolio["accounts"])
        portfolio["total_value"]      = round(total_value, 2)
        portfolio["total_return"]     = 0.0
        portfolio["total_return_pct"] = 0.0

        # YTD
        cur.execute("""
            SELECT TOP 1 portfolio_value FROM dbo.performance
            WHERE client_id = %s AND MONTH(period_date) = 1
            ORDER BY period_date DESC
        """, (client_id,))
        jan_row = cur.fetchone()
        cur.execute("""
            SELECT TOP 1 portfolio_value FROM dbo.performance
            WHERE client_id = %s ORDER BY period_date DESC
        """, (client_id,))
        latest_row = cur.fetchone()
        if jan_row and latest_row:
            jan_val    = _f(jan_row["portfolio_value"])
            latest_val = _f(latest_row["portfolio_value"])
            portfolio["ytd_return_pct"] = round((latest_val - jan_val) / jan_val * 100, 2) if jan_val else 0.0
        else:
            portfolio["ytd_return_pct"] = 0.0

        # Performance series
        cur.execute("""
            SELECT CONVERT(VARCHAR(7), period_date, 120) AS date,
                   portfolio_value, benchmark_value
            FROM dbo.performance WHERE client_id = %s ORDER BY period_date
        """, (client_id,))
        portfolio["performance"] = [
            {"date": r["date"],
             "portfolio_value": _f(r["portfolio_value"]),
             "benchmark_value": _f(r["benchmark_value"])}
            for r in cur.fetchall()
        ]

        # Cash flows
        cur.execute("""
            SELECT month_label AS month, inflow, outflow, net
            FROM dbo.cash_flows WHERE client_id = %s AND year = 2024 ORDER BY month_num
        """, (client_id,))
        portfolio["cash_flows"] = [
            {"month": r["month"], "inflow": _f(r["inflow"]),
             "outflow": _f(r["outflow"]), "net": _f(r["net"])}
            for r in cur.fetchall()
        ]

        # Risk alerts
        cur.execute("""
            SELECT level, category, message FROM dbo.risk_alerts
            WHERE client_id = %s
            ORDER BY CASE level WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END
        """, (client_id,))
        portfolio["risk_alerts"] = list(cur.fetchall())

        # Allocation
        alloc: dict[str, float] = {"equity": 0.0, "fixed_income": 0.0, "cash": 0.0, "alternatives": 0.0}
        for h in holdings:
            cls = h["asset_class"]
            if cls in alloc:
                alloc[cls] = round(alloc[cls] + h["weight"], 2)
        portfolio["allocation"] = alloc

        return portfolio


fabric_service = FabricService()
