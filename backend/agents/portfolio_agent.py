"""
Portfolio Intelligence Agent.

Orchestrates all data sources and produces the full pre-review package:
  1. Pull structured data from Fabric (accounts, holdings, performance, cashflows)
  2. Pull relevant document context from Azure AI Search (RAG)
  3. Pull live market prices (or cached)
  4. Generate RM narrative via Azure OpenAI
  5. Return the combined PortfolioInsights package

Each step is logged so the agent's reasoning is visible in the server console.
"""

from datetime import datetime, timezone

from services.fabric_service import fabric_service
from services.openai_service import openai_service
from services.search_service import search_service
from services.market_data_service import market_data_service


class PortfolioAgent:
    async def run(self, client_id: str) -> dict:
        print(f"\n[Agent] Starting portfolio review for client: {client_id}")

        # Step 1: Structured data from Fabric
        print("[Agent] Step 1 – Querying Fabric SQL for portfolio data …")
        portfolio = await fabric_service.get_portfolio_data(client_id)
        if not portfolio:
            raise ValueError(f"No portfolio data found for client {client_id}")
        print(f"[Agent]   → {len(portfolio['holdings'])} holdings, "
              f"{len(portfolio['accounts'])} accounts loaded")

        # Step 2: Document context via RAG
        print("[Agent] Step 2 – Searching Azure AI Search for relevant documents …")
        doc_context = await search_service.search_documents(
            query=f"portfolio performance risk cashflow {portfolio['client_name']}",
            client_id=client_id,
        )
        print(f"[Agent]   → {len(doc_context)} document chunks retrieved")

        # Step 3: Market data enrichment
        print("[Agent] Step 3 – Fetching latest market prices …")
        market_summary = await market_data_service.get_market_summary()
        print(f"[Agent]   → Market summary: {list(market_summary.keys())}")

        # Step 4: Generate narrative via OpenAI
        print("[Agent] Step 4 – Generating RM narrative via Azure OpenAI …")
        insights = await openai_service.generate_portfolio_narrative(portfolio, doc_context)
        print(f"[Agent]   → Narrative generated ({len(insights['narrative'])} chars)")

        print("[Agent] Done.\n")
        return {
            **insights,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "market_context": market_summary,
            "document_hits": len(doc_context),
        }


portfolio_agent = PortfolioAgent()
