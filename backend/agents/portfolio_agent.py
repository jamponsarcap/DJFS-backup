"""
Portfolio Intelligence Agent.

Two execution paths depending on configuration:

  Foundry path  (when AZURE_AI_AGENT_ID is set)
    → Delegates entirely to SummarizationAgent.
    → The agent queries Fabric SQL and Azure AI Search itself via its connected tools.
    → Steps 1-3 are skipped to avoid redundant data fetching.

  OpenAI path  (fallback when Foundry is not configured)
    → Classic pipeline: Fabric → RAG → market data → Azure OpenAI narrative.
"""

from datetime import datetime, timezone

import config
from services.fabric_service import fabric_service
from services.openai_service import openai_service
from services.foundry_agent_service import foundry_agent_service
from services.search_service import search_service
from services.market_data_service import market_data_service


class PortfolioAgent:
    async def run(self, client_id: str) -> dict:
        if config.foundry_agent_enabled():
            return await self._run_with_foundry(client_id)
        return await self._run_with_openai(client_id)

    # ── Foundry path ──────────────────────────────────────────────────────────

    async def _run_with_foundry(self, client_id: str) -> dict:
        """
        Delegate entirely to SummarizationAgent.
        We do a single lightweight Fabric call only to validate the client exists
        and obtain the display name to pass to the agent.
        """
        print(f"\n[Agent] Starting portfolio review for client: {client_id} (SummarizationAgent)")

        print("[Agent] Step 1 – Validating client via Fabric …")
        portfolio = await fabric_service.get_portfolio_data(client_id)
        if not portfolio:
            raise ValueError(f"No portfolio data found for client {client_id}")
        client_name = portfolio.get("client_name", client_id)
        print(f"[Agent]   → Client confirmed: {client_name}")

        print("[Agent] Step 2 – Dispatching to SummarizationAgent …")
        insights = await foundry_agent_service.run_summarization(client_id, client_name)
        print(f"[Agent]   → Summary received ({len(insights['narrative'])} chars)")

        print("[Agent] Done.\n")
        return {
            **insights,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── OpenAI fallback path ──────────────────────────────────────────────────

    async def _run_with_openai(self, client_id: str) -> dict:
        """
        Classic pipeline: Fabric SQL → Azure AI Search (RAG) → market data → Azure OpenAI.
        Used when Foundry agents are not configured.
        """
        print(f"\n[Agent] Starting portfolio review for client: {client_id} (Azure OpenAI)")

        print("[Agent] Step 1 – Querying Fabric SQL for portfolio data …")
        portfolio = await fabric_service.get_portfolio_data(client_id)
        if not portfolio:
            raise ValueError(f"No portfolio data found for client {client_id}")
        print(f"[Agent]   → {len(portfolio['holdings'])} holdings, "
              f"{len(portfolio['accounts'])} accounts loaded")

        print("[Agent] Step 2 – Searching Azure AI Search for relevant documents …")
        doc_context = await search_service.search_documents(
            query=f"portfolio performance risk cashflow {portfolio['client_name']}",
            client_id=client_id,
        )
        print(f"[Agent]   → {len(doc_context)} document chunks retrieved")

        print("[Agent] Step 3 – Fetching latest market prices …")
        market_summary = await market_data_service.get_market_summary()
        print(f"[Agent]   → Market summary: {list(market_summary.keys())}")

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