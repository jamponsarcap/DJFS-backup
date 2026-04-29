"""
Indexes Fabric SQL portfolio data into Azure AI Search as searchable text.
Run from the backend/ directory: python -m data.index_lakehouse

Works in both Fabric-live and mock modes — whichever fabric_service resolves to.
Re-run whenever the underlying portfolio data changes.
"""
import asyncio
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv()

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from services.fabric_service import fabric_service


def _safe_id(*parts: str) -> str:
    """Build an Azure AI Search-safe document key (letters, digits, _, -, = only)."""
    raw = "_".join(str(p) for p in parts)
    return re.sub(r"[^A-Za-z0-9_\-=]", "_", raw)


def _build_documents(client_id: str, portfolio: dict) -> list[dict]:
    name = portfolio["client_name"]
    docs = []

    # ── Portfolio summary ──────────────────────────────────────────────────────
    docs.append({
        "id":        _safe_id(client_id, "summary"),
        "client_id": client_id,
        "source":    "fabric_summary",
        "page":      None,
        "content": (
            f"{name}: total portfolio value £{portfolio['total_value']:,.0f}, "
            f"total return £{portfolio['total_return']:,.0f} "
            f"({portfolio['total_return_pct']:.1f}%), "
            f"YTD return {portfolio['ytd_return_pct']:.2f}%."
        ),
    })

    # ── Asset allocation ───────────────────────────────────────────────────────
    alloc = portfolio.get("allocation", {})
    docs.append({
        "id":        _safe_id(client_id, "allocation"),
        "client_id": client_id,
        "source":    "fabric_allocation",
        "page":      None,
        "content": (
            f"{name} asset allocation: "
            f"equity {alloc.get('equity', 0):.1f}%, "
            f"fixed income {alloc.get('fixed_income', 0):.1f}%, "
            f"cash {alloc.get('cash', 0):.1f}%, "
            f"alternatives {alloc.get('alternatives', 0):.1f}%."
        ),
    })

    # ── Accounts ───────────────────────────────────────────────────────────────
    account_lines = "; ".join(
        f"{a['name']} ({a['type']}) £{a['balance']:,.0f} {a['currency']}"
        for a in portfolio.get("accounts", [])
    )
    docs.append({
        "id":        _safe_id(client_id, "accounts"),
        "client_id": client_id,
        "source":    "fabric_accounts",
        "page":      None,
        "content":   f"{name} accounts: {account_lines}.",
    })

    # ── One document per holding ───────────────────────────────────────────────
    for h in portfolio.get("holdings", []):
        gl_sign = "+" if h["gain_loss"] >= 0 else ""
        docs.append({
            "id":        _safe_id(client_id, "holding", h["symbol"]),
            "client_id": client_id,
            "source":    "fabric_holdings",
            "page":      None,
            "content": (
                f"{name} holds {h['symbol']} ({h['name']}), "
                f"asset class {h['asset_class']}, "
                f"quantity {h['quantity']:,}, "
                f"market value £{h['market_value']:,.0f}, "
                f"portfolio weight {h['weight']:.1f}%, "
                f"gain/loss {gl_sign}£{h['gain_loss']:,.0f} ({gl_sign}{h['gain_loss_pct']:.1f}%)."
            ),
        })

    # ── One document per risk alert ────────────────────────────────────────────
    for i, alert in enumerate(portfolio.get("risk_alerts", [])):
        docs.append({
            "id":        _safe_id(client_id, "alert", str(i)),
            "client_id": client_id,
            "source":    "fabric_risk_alerts",
            "page":      None,
            "content": (
                f"{name} risk alert – severity {alert['level']}, "
                f"category {alert['category']}: {alert['message']}"
            ),
        })

    # ── Cash flow summary (annual totals) ──────────────────────────────────────
    cash_flows = portfolio.get("cash_flows", [])
    if cash_flows:
        total_in  = sum(cf["inflow"]  for cf in cash_flows)
        total_out = sum(cf["outflow"] for cf in cash_flows)
        net       = sum(cf["net"]     for cf in cash_flows)
        docs.append({
            "id":        _safe_id(client_id, "cashflows"),
            "client_id": client_id,
            "source":    "fabric_cashflows",
            "page":      None,
            "content": (
                f"{name} annual cash flows: "
                f"total inflows £{total_in:,.0f}, "
                f"total outflows £{total_out:,.0f}, "
                f"net £{net:,.0f}."
            ),
        })

    return docs


async def main():
    endpoint   = os.environ["AZURE_SEARCH_ENDPOINT"]
    key        = os.environ["AZURE_SEARCH_API_KEY"]
    index_name = os.environ.get("AZURE_SEARCH_INDEX", "portfolio-docs")

    search = SearchClient(endpoint, index_name, AzureKeyCredential(key))

    clients = await fabric_service.get_clients()
    all_docs: list[dict] = []

    for client in clients:
        cid       = client["id"]
        portfolio = await fabric_service.get_portfolio_data(cid)
        if not portfolio:
            print(f"  [!] No portfolio data for {cid} – skipping")
            continue

        docs = _build_documents(cid, portfolio)
        all_docs.extend(docs)
        print(f"  {cid} ({portfolio['client_name']}): {len(docs)} documents prepared")

    results   = search.upload_documents(documents=all_docs)
    succeeded = sum(1 for r in results if r.succeeded)
    failed    = len(all_docs) - succeeded

    print(f"\nIndexed {succeeded}/{len(all_docs)} documents successfully.", end="")
    if failed:
        print(f" {failed} failed.")
    else:
        print()


if __name__ == "__main__":
    asyncio.run(main())
