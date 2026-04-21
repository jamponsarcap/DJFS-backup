"""
Microsoft Fabric / OneLake SQL service.

When FABRIC_SERVER + FABRIC_DATABASE are set, this connects via Entra ID
(DefaultAzureCredential) using the Microsoft ODBC Driver for SQL Server.
Otherwise it returns mock data so the app runs locally without Azure.

Install notes (when activating live mode):
  pip install pyodbc
  Install ODBC Driver 18 for SQL Server from Microsoft.
"""

import config
from data.mock_data import MOCK_CLIENTS, MOCK_PORTFOLIOS


class FabricService:
    def __init__(self):
        self._live = config.fabric_enabled()
        if self._live:
            self._init_live()
        else:
            print("[FabricService] Running in mock mode (FABRIC_SERVER not set)")

    def _init_live(self):
        # PLACEHOLDER ─ uncomment once ODBC driver is installed
        # from azure.identity import DefaultAzureCredential
        # import struct, pyodbc
        # credential = DefaultAzureCredential()
        # token = credential.get_token("https://database.windows.net/.default")
        # token_bytes = token.token.encode("utf-16-le")
        # token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
        # SQL_COPT_SS_ACCESS_TOKEN = 1256
        # conn_str = (
        #     f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        #     f"SERVER={config.FABRIC_SERVER};"
        #     f"DATABASE={config.FABRIC_DATABASE};"
        #     "Encrypt=yes;TrustServerCertificate=no"
        # )
        # self._conn = pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
        raise NotImplementedError("Fabric live mode: install pyodbc + ODBC Driver 18 and uncomment above")

    async def get_clients(self) -> list:
        if not self._live:
            return MOCK_CLIENTS
        # PLACEHOLDER ─ replace with real SQL query
        # cursor = self._conn.cursor()
        # cursor.execute("SELECT id, name, rm_name, last_review, risk_profile FROM dbo.clients")
        # return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        raise NotImplementedError

    async def get_portfolio_data(self, client_id: str) -> dict | None:
        if not self._live:
            return MOCK_PORTFOLIOS.get(client_id)
        # PLACEHOLDER ─ join accounts + holdings + performance + cashflows tables
        # cursor = self._conn.cursor()
        # cursor.execute("EXEC dbo.sp_get_client_portfolio @client_id=?", client_id)
        # ...
        raise NotImplementedError


fabric_service = FabricService()
