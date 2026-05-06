"""
Microsoft Fabric / OneLake SQL service.

Uses pytds / python-tds (pure Python, no ODBC driver required) with an
Entra ID access token obtained via InteractiveBrowserCredential.

Falls back to mock data when FABRIC_SERVER / FABRIC_DATABASE are not set.
"""

import datetime
from collections import defaultdict

import config
from data.mock_data import MOCK_CLIENTS, MOCK_PORTFOLIOS

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]


def _f(val) -> float:
    """Safe float conversion for Decimal / numeric DB values."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _row_to_dict(row, columns: list[str]) -> dict:
    return {column: row[index] for index, column in enumerate(columns)}


def _mock_statement_diff(transactions: list[dict]) -> dict:
    """Compute a realistic diff dict from transactions without touching the DB."""
    monthly: dict[str, dict] = defaultdict(lambda: {"inflow": 0.0, "outflow": 0.0})
    for tx in transactions:
        ym = tx["date"][:7]
        if tx["amount"] < 0:
            monthly[ym]["inflow"] += abs(tx["amount"])
        else:
            monthly[ym]["outflow"] += tx["amount"]

    total_net = sum(v["inflow"] - v["outflow"] for v in monthly.values())
    mock_before = 1_284_750.00
    mock_after  = round(mock_before + total_net, 2)

    cf_changes = {}
    for ym, cf in monthly.items():
        year, month_num = int(ym[:4]), int(ym[5:])
        label = f"{MONTH_NAMES[month_num - 1]} {year}"
        cf_changes[label] = {
            "inflow_delta":  round(cf["inflow"], 2),
            "outflow_delta": round(cf["outflow"], 2),
            "net_delta":     round(cf["inflow"] - cf["outflow"], 2),
        }

    return {
        "total_value_before": mock_before,
        "total_value_after":  mock_after,
        "total_value_delta":  round(total_net, 2),
        "account_changes": {
            "acc_001a": {
                "account_name": "ISA Portfolio",
                "before": 542_300.00,
                "after":  round(542_300.00 + total_net, 2),
                "delta":  round(total_net, 2),
            }
        },
        "cash_flow_changes": cf_changes,
        "transactions_count": len(transactions),
        # Empty snapshot — mock mode has no real DB rows to restore
        "_snapshot": {"accounts": [], "cash_flows": {}},
    }


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
            print("[FabricService] Running in mock mode (Fabric connection settings not set)")

    def _connect(self):
        from mssql_python import connect as sql_connect

        try:
            self._conn = sql_connect(self._build_connection_string(), autocommit=True)
            print("[FabricService] Connected to Fabric SQL via Microsoft driver")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Fabric SQL: {e}") from e

    def _build_connection_string(self) -> str:
        if config.FABRIC_CONNECTION_STRING:
            return config.FABRIC_CONNECTION_STRING

        server = config.FABRIC_SERVER.strip()
        user_id = config.CLOUDLABS_ID.strip()
        if not server.lower().startswith("tcp:"):
            server = f"tcp:{server}"
        if "," not in server:
            server = f"{server},1433"

        connection_string = (
            f"Server={server};"
            f"Database={config.FABRIC_DATABASE};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            f"Authentication={config.FABRIC_AUTHENTICATION};"
        )

        if user_id:
            connection_string += f"UID={user_id};"

        return connection_string

    def _fetchone_dict(self, cur):
        row = cur.fetchone()
        if row is None:
            return None
        columns = [col[0] for col in (cur.description or [])]
        return _row_to_dict(row, columns)

    def _fetchall_dicts(self, cur) -> list[dict]:
        columns = [col[0] for col in (cur.description or [])]
        return [_row_to_dict(row, columns) for row in cur.fetchall()]

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
        return self._fetchall_dicts(cur)

    async def get_portfolio_data(self, client_id: str) -> dict | None:
        if not self._live:
            return MOCK_PORTFOLIOS.get(client_id)

        cur = self._cursor()

        # Client
        cur.execute("""
            SELECT client_id, client_name
            FROM dbo.clients WHERE client_id = ?
        """, (client_id,))
        row = self._fetchone_dict(cur)
        if not row:
            return None
        portfolio = {"client_id": row["client_id"], "client_name": row["client_name"]}

        # Accounts
        cur.execute("""
            SELECT account_id AS id, account_type AS type,
                   account_name AS name, balance, currency
            FROM dbo.accounts WHERE client_id = ? ORDER BY account_type
        """, (client_id,))
        portfolio["accounts"] = [
            {**r, "balance": _f(r["balance"])} for r in self._fetchall_dicts(cur)
        ]

        # Holdings
        cur.execute("""
            SELECT symbol, name, asset_class, quantity,
                   current_price,
                   market_value,
                   cost_basis,
                   gain_loss,
                   gain_loss_pct, weight
            FROM dbo.holdings WHERE client_id = ? ORDER BY weight DESC
        """, (client_id,))
        holdings = [
            {k: _f(v) if k not in ("symbol", "name", "asset_class") else v
             for k, v in r.items()}
            for r in self._fetchall_dicts(cur)
        ]
        portfolio["holdings"] = holdings

        # Total value = sum of all account balances (source of truth)
        total_value = sum(a["balance"] for a in portfolio["accounts"])
        portfolio["total_value"] = round(total_value, 2)

        # Performance series (fetched early — used for return calculations below)
        cur.execute("""
            SELECT CONVERT(VARCHAR(7), period_date, 120) AS date,
                   portfolio_value, benchmark_value
            FROM dbo.performance WHERE client_id = ? ORDER BY period_date
        """, (client_id,))
        perf_rows = self._fetchall_dicts(cur)
        portfolio["performance"] = [
            {"date": r["date"],
             "portfolio_value": _f(r["portfolio_value"]),
             "benchmark_value": _f(r["benchmark_value"])}
            for r in perf_rows
        ]

        # Total return: current value vs earliest recorded portfolio value
        if perf_rows:
            initial_val = _f(perf_rows[0]["portfolio_value"])
            if initial_val:
                portfolio["total_return"]     = round(total_value - initial_val, 2)
                portfolio["total_return_pct"] = round((total_value - initial_val) / initial_val * 100, 2)
            else:
                portfolio["total_return"]     = 0.0
                portfolio["total_return_pct"] = 0.0
        else:
            portfolio["total_return"]     = 0.0
            portfolio["total_return_pct"] = 0.0

        # YTD: current value vs this year's January value
        current_year = str(datetime.date.today().year)
        jan_rows = [r for r in perf_rows if r["date"].startswith(f"{current_year}-01")]
        if jan_rows:
            jan_val = _f(jan_rows[0]["portfolio_value"])
            portfolio["ytd_return_pct"] = round((total_value - jan_val) / jan_val * 100, 2) if jan_val else 0.0
        else:
            portfolio["ytd_return_pct"] = 0.0

        # Cash flows — all months across all years, in chronological order
        cur.execute("""
            SELECT CONCAT(month_label, ' ', year) AS month, inflow, outflow, net
            FROM dbo.cash_flows
            WHERE client_id = ?
            ORDER BY year, month_num
        """, (client_id,))
        portfolio["cash_flows"] = [
            {"month": r["month"], "inflow": _f(r["inflow"]),
             "outflow": _f(r["outflow"]), "net": _f(r["net"])}
            for r in self._fetchall_dicts(cur)
        ]

        # Risk alerts
        cur.execute("""
            SELECT level, category, message FROM dbo.risk_alerts
            WHERE client_id = ?
            ORDER BY CASE level WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END
        """, (client_id,))
        portfolio["risk_alerts"] = self._fetchall_dicts(cur)

        # Allocation
        alloc: dict[str, float] = {"equity": 0.0, "fixed_income": 0.0, "cash": 0.0, "alternatives": 0.0}
        for h in holdings:
            cls = h["asset_class"]
            if cls in alloc:
                alloc[cls] = round(alloc[cls] + h["weight"], 2)
        portfolio["allocation"] = alloc

        return portfolio

    async def apply_statement(self, client_id: str, extraction: dict) -> dict:
        """
        Write extracted statement transactions to the DB.
        Returns a diff showing what changed.
        Positive amounts = debits (outflows), negative amounts = credits (inflows).
        """
        transactions = extraction.get("transactions", [])

        if not self._live:
            return _mock_statement_diff(transactions)

        cur = self._cursor()

        # Snapshot accounts before
        cur.execute("""
            SELECT account_id, account_name, balance
            FROM dbo.accounts WHERE client_id = ?
        """, (client_id,))
        accounts_before = {
            r["account_id"]: {"name": r["account_name"], "balance": _f(r["balance"])}
            for r in self._fetchall_dicts(cur)
        }
        total_before = sum(v["balance"] for v in accounts_before.values())

        # Group transactions by year-month
        monthly: dict[str, dict] = defaultdict(lambda: {"inflow": 0.0, "outflow": 0.0})
        for tx in transactions:
            ym = tx["date"][:7]
            if tx["amount"] < 0:
                monthly[ym]["inflow"] += abs(tx["amount"])
            else:
                monthly[ym]["outflow"] += tx["amount"]

        # Upsert cash_flows rows, capturing the before-state for each month
        cf_changes: dict[str, dict] = {}
        cf_snapshot: dict[str, dict] = {}  # keyed by "year-month_num"
        for ym, cf in monthly.items():
            year_val    = int(ym[:4])
            month_num   = int(ym[5:])
            month_label = MONTH_NAMES[month_num - 1]
            net = cf["inflow"] - cf["outflow"]
            snap_key = f"{year_val}-{month_num}"

            cur.execute("""
                SELECT inflow, outflow FROM dbo.cash_flows
                WHERE client_id = ? AND year = ? AND month_num = ?
            """, (client_id, year_val, month_num))
            existing = self._fetchone_dict(cur)

            if existing:
                cf_snapshot[snap_key] = {
                    "existed": True,
                    "year": year_val, "month_num": month_num,
                    "inflow":  _f(existing["inflow"]),
                    "outflow": _f(existing["outflow"]),
                    "net":     _f(existing["inflow"]) - _f(existing["outflow"]),
                }
                new_inflow  = _f(existing["inflow"])  + cf["inflow"]
                new_outflow = _f(existing["outflow"]) + cf["outflow"]
                cur.execute("""
                    UPDATE dbo.cash_flows
                    SET inflow = ?, outflow = ?, net = ?
                    WHERE client_id = ? AND year = ? AND month_num = ?
                """, (new_inflow, new_outflow, new_inflow - new_outflow,
                      client_id, year_val, month_num))
            else:
                cf_snapshot[snap_key] = {
                    "existed": False,
                    "year": year_val, "month_num": month_num,
                }
                cur.execute("""
                    INSERT INTO dbo.cash_flows
                        (client_id, year, month_num, month_label, inflow, outflow, net)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (client_id, year_val, month_num, month_label,
                      cf["inflow"], cf["outflow"], net))

            cf_changes[f"{month_label} {year_val}"] = {
                "inflow_delta":  round(cf["inflow"], 2),
                "outflow_delta": round(cf["outflow"], 2),
                "net_delta":     round(net, 2),
            }

        # Apply net cash change to the first account
        total_net = sum(cf["inflow"] - cf["outflow"] for cf in monthly.values())
        account_changes: dict[str, dict] = {}
        acc_snapshot: list[dict] = []

        if accounts_before:
            first_id = next(iter(accounts_before))
            acc = accounts_before[first_id]
            acc_snapshot.append({"id": first_id, "balance_before": acc["balance"]})
            new_balance = acc["balance"] + total_net
            cur.execute("""
                UPDATE dbo.accounts SET balance = ? WHERE account_id = ?
            """, (new_balance, first_id))
            account_changes[first_id] = {
                "account_name": acc["name"],
                "before": round(acc["balance"], 2),
                "after":  round(new_balance, 2),
                "delta":  round(total_net, 2),
            }

        total_after = round(total_before + total_net, 2)

        return {
            "total_value_before": round(total_before, 2),
            "total_value_after":  total_after,
            "total_value_delta":  round(total_net, 2),
            "account_changes":    account_changes,
            "cash_flow_changes":  cf_changes,
            "transactions_count": len(transactions),
            # Stored by main.py for undo — not exposed in the API response
            "_snapshot": {"accounts": acc_snapshot, "cash_flows": cf_snapshot},
        }

    async def update_holdings_market_data(self, client_id: str, holdings: list[dict]) -> int:
        """Write fresh market prices back to dbo.holdings. Returns number of rows updated."""
        if not self._live:
            return 0

        total_market_value = sum(_f(h.get("market_value", 0)) for h in holdings)

        cur = self._cursor()
        updated = 0
        for h in holdings:
            symbol = h.get("symbol")
            if not symbol or h.get("asset_class") == "cash":
                continue
            price = _f(h.get("current_price", 0))
            if price <= 0:
                continue
            new_weight = round(_f(h["market_value"]) / total_market_value * 100, 2) if total_market_value else _f(h.get("weight", 0))
            cur.execute("""
                UPDATE dbo.holdings
                SET current_price = ?, market_value = ?, gain_loss = ?, gain_loss_pct = ?, weight = ?
                WHERE client_id = ? AND symbol = ?
            """, (price, _f(h.get("market_value", 0)), _f(h.get("gain_loss", 0)),
                  _f(h.get("gain_loss_pct", 0)), new_weight, client_id, symbol))
            updated += 1
        return updated

    async def undo_statement(self, client_id: str, snapshot: dict) -> None:
        """Restore account balances and cash flow rows to their pre-upload state."""
        if not self._live:
            return  # Mock mode: nothing to restore in DB

        cur = self._cursor()

        for acc in snapshot.get("accounts", []):
            cur.execute(
                "UPDATE dbo.accounts SET balance = ? WHERE account_id = ?",
                (acc["balance_before"], acc["id"]),
            )

        for cf in snapshot.get("cash_flows", {}).values():
            year_val, month_num = cf["year"], cf["month_num"]
            if not cf["existed"]:
                cur.execute("""
                    DELETE FROM dbo.cash_flows
                    WHERE client_id = ? AND year = ? AND month_num = ?
                """, (client_id, year_val, month_num))
            else:
                cur.execute("""
                    UPDATE dbo.cash_flows
                    SET inflow = ?, outflow = ?, net = ?
                    WHERE client_id = ? AND year = ? AND month_num = ?
                """, (cf["inflow"], cf["outflow"], cf["net"],
                      client_id, year_val, month_num))


fabric_service = FabricService()
