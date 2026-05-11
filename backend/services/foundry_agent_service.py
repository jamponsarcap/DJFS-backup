"""
Azure AI Foundry Agent service.

Correct API surface for account-based Foundry projects (2025-05-15-preview):
  Base:  {project_endpoint}/threads   (NOT /openai/v1/threads)
  Scope: https://ai.azure.com/.default
  SSL:   verify=False  (corporate proxy on Capgemini network)

Authentication: InteractiveBrowserCredential for the sandbox tenant.
On first call a browser popup appears (same as Lakehouse uploads).
Subsequent calls are silent — the token is cached by MSAL.

Two agents:
  SummarizationAgent     (AZURE_AI_AGENT_ID)           -> advisor-facing text
  PortfolioInsightsAgent (AZURE_AI_PORTFOLIO_AGENT_ID) -> structured JSON payload
"""

import asyncio
import json
import time

import httpx

import config

_API_VERSION = "2025-05-15-preview"
_SCOPE = "https://ai.azure.com/.default"
_SANDBOX_TENANT = "baf5b083-4c53-493a-8af7-a6ae9812014c"


class FoundryAgentService:
    def __init__(self):
        any_live = config.foundry_agent_enabled() or config.foundry_portfolio_agent_enabled()
        if any_live:
            from azure.identity import InteractiveBrowserCredential
            self._cred = InteractiveBrowserCredential(tenant_id=_SANDBOX_TENANT)
            self._base = config.AZURE_AI_PROJECT_ENDPOINT.rstrip("/")
            print(f"[FoundryAgent] Connected — {self._base}")
        else:
            self._cred = None
            self._base = None
            print("[FoundryAgent] Mock mode (AZURE_AI_PROJECT_ENDPOINT not set)")

    # ── Public API ────────────────────────────────────────────────────────────

    async def run_summarization(
        self,
        client_id: str,
        client_name: str = "",
        portfolio: dict | None = None,
        doc_context: list[dict] | None = None,
    ) -> dict:
        """
        Call SummarizationAgent.

        When portfolio data is provided the agent receives it directly in the message,
        bypassing its Fabric tool calls (~5 min) and dropping response time to ~10s.
        When no data is provided the agent fetches it itself (slow path).
        """
        if not config.foundry_agent_enabled():
            return {
                "narrative": "SummarizationAgent not configured — set AZURE_AI_AGENT_ID.",
                "key_points": [],
                "data_sources": ["Mock"],
            }

        label = client_name or client_id
        if portfolio:
            message = self._build_summary_message(label, client_id, portfolio, doc_context or [])
        else:
            message = (
                f"Please produce a portfolio summary for client: {label} (client_id: {client_id}).\n"
                "Retrieve all data from Fabric SQL and Azure AI Search using your connected tools."
            )

        raw = await asyncio.get_event_loop().run_in_executor(
            None, self._run_sync, message, config.AZURE_AI_AGENT_ID, 180.0
        )
        return self._parse_summary(raw)

    async def run_portfolio_insights(
        self,
        client_id: str,
        client_name: str = "",
        portfolio: dict | None = None,
        doc_context: list[dict] | None = None,
    ) -> dict:
        """
        Call PortfolioInsightsAgent. Returns the full structured JSON payload.

        When portfolio data is provided the agent skips its Fabric tool calls.
        """
        if not config.foundry_portfolio_agent_enabled():
            return {"error": "PortfolioInsightsAgent not configured — set AZURE_AI_PORTFOLIO_AGENT_ID."}

        label = client_name or client_id
        if portfolio:
            message = self._build_insights_message(label, client_id, portfolio, doc_context or [])
        else:
            message = (
                f"Generate the full portfolio insights payload for client: {label} (client_id: {client_id}).\n"
                "Retrieve all data from Fabric SQL and Azure AI Search using your connected tools.\n"
                "Return JSON ONLY — no markdown, no explanation."
            )

        raw = await asyncio.get_event_loop().run_in_executor(
            None, self._run_sync, message, config.AZURE_AI_PORTFOLIO_AGENT_ID, 120.0
        )
        return self._parse_insights(raw)

    # ── Core runner ───────────────────────────────────────────────────────────

    def _run_sync(self, user_message: str, agent_id: str, timeout: float = 90.0) -> str:
        """
        Direct REST calls to the Foundry Agents API.
        Path: {project_endpoint}/{resource}?api-version=2025-05-15-preview
        Token scope: https://ai.azure.com/.default
        """
        token = self._cred.get_token(_SCOPE).token
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        params = {"api-version": _API_VERSION}

        with httpx.Client(verify=False, timeout=30.0) as client:
            # 1. Create thread
            r = client.post(f"{self._base}/threads", headers=headers, params=params, json={})
            r.raise_for_status()
            thread_id = r.json()["id"]

            # 2. Add user message
            r = client.post(
                f"{self._base}/threads/{thread_id}/messages",
                headers=headers, params=params,
                json={"role": "user", "content": user_message},
            )
            r.raise_for_status()

            # 3. Start run
            r = client.post(
                f"{self._base}/threads/{thread_id}/runs",
                headers=headers, params=params,
                json={"assistant_id": agent_id},
            )
            r.raise_for_status()
            run_id = r.json()["id"]
            status = r.json()["status"]

            # 4. Poll until done
            deadline = time.time() + timeout
            while status in ("queued", "in_progress", "requires_action"):
                if time.time() > deadline:
                    client.post(
                        f"{self._base}/threads/{thread_id}/runs/{run_id}/cancel",
                        headers=headers, params=params, json={},
                    )
                    raise TimeoutError(f"Foundry Agent run timed out after {timeout}s")
                time.sleep(2.0)
                r = client.get(
                    f"{self._base}/threads/{thread_id}/runs/{run_id}",
                    headers=headers, params=params,
                )
                r.raise_for_status()
                status = r.json()["status"]

            if status != "completed":
                raise RuntimeError(f"Foundry Agent run ended with status '{status}'")

            # 5. Read the assistant's reply
            r = client.get(
                f"{self._base}/threads/{thread_id}/messages",
                headers=headers, params=params,
            )
            r.raise_for_status()
            for msg in r.json().get("data", []):
                if msg.get("role") == "assistant":
                    for block in msg.get("content", []):
                        if block.get("type") == "text":
                            return block["text"]["value"]

        return ""

    # ── Message builders ──────────────────────────────────────────────────────

    def _build_summary_message(
        self, label: str, client_id: str, portfolio: dict, doc_context: list[dict]
    ) -> str:
        data = {
            "client_name": portfolio.get("client_name"),
            "client_id": client_id,
            "total_value": portfolio.get("total_value"),
            "total_return_pct": portfolio.get("total_return_pct"),
            "ytd_return_pct": portfolio.get("ytd_return_pct"),
            "allocation": portfolio.get("allocation"),
            "top_holdings": portfolio.get("holdings", [])[:5],
            "cash_flows": portfolio.get("cash_flows", [])[-3:],
            "risk_alerts": portfolio.get("risk_alerts", []),
            "accounts": portfolio.get("accounts", []),
        }
        msg = (
            f"The following portfolio data has already been retrieved from Fabric SQL for "
            f"client: {label} (client_id: {client_id}). "
            "Use this data directly — do NOT call the Fabric tool again.\n\n"
            f"PORTFOLIO DATA:\n{json.dumps(data, default=str)}"
        )
        if doc_context:
            snippets = "\n".join(f"- [{d['source']}] {d['content']}" for d in doc_context)
            msg += f"\n\nDOCUMENT CONTEXT (from Azure AI Search):\n{snippets}"
        msg += "\n\nPlease produce the portfolio summary now."
        return msg

    def _build_insights_message(
        self, label: str, client_id: str, portfolio: dict, doc_context: list[dict]
    ) -> str:
        msg = (
            f"The following portfolio data has already been retrieved from Fabric SQL for "
            f"client: {label} (client_id: {client_id}). "
            "Use this data directly — do NOT call the Fabric tool again.\n\n"
            f"PORTFOLIO DATA:\n{json.dumps(portfolio, default=str)}"
        )
        if doc_context:
            snippets = "\n".join(f"- [{d['source']}] {d['content']}" for d in doc_context)
            msg += f"\n\nDOCUMENT CONTEXT (from Azure AI Search):\n{snippets}"
        msg += "\n\nGenerate the full portfolio insights JSON payload now. Return JSON ONLY."
        return msg

    # ── Reply parsers ─────────────────────────────────────────────────────────

    def _parse_summary(self, raw: str) -> dict:
        key_points = [
            line.lstrip("-*. ").strip()
            for line in raw.splitlines()
            if line.strip().startswith(("-", "*", "•")) and len(line.strip()) > 3
        ]
        return {
            "narrative": raw,
            "key_points": key_points[:8],
            "data_sources": ["Azure AI Foundry — SummarizationAgent", "Fabric SQL", "Azure AI Search"],
        }

    def _parse_insights(self, raw: str) -> dict:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"raw_response": raw, "parse_error": "Agent did not return valid JSON"}


foundry_agent_service = FoundryAgentService()