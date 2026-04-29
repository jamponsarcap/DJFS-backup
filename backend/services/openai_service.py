"""
Azure OpenAI service for narrative generation.
Falls back to pre-canned mock narratives when not configured.
"""

import config
from data.mock_data import MOCK_NARRATIVES


SYSTEM_PROMPT = """You are a senior Relationship Manager assistant at a private bank.
Given structured portfolio data, produce a concise pre-review briefing for the RM.

Rules:
- Write in professional financial English; be factual, not promotional.
- Do NOT give personalised investment advice or predictions.
- Highlight the 3-5 most important points: performance drivers, risk flags, rebalancing needs.
- Keep the narrative under 200 words.
- Return JSON with keys: narrative (string), key_points (list of strings)."""


class OpenAIService:
    def __init__(self):
        self._live = config.openai_enabled()
        if self._live:
            from openai import AzureOpenAI
            self._client = AzureOpenAI(
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                api_key=config.AZURE_OPENAI_API_KEY,
                api_version="2024-05-01-preview",
            )
        else:
            print("[OpenAIService] Running in mock mode (AZURE_OPENAI_ENDPOINT not set)")

    async def generate_portfolio_narrative(self, portfolio_data: dict, doc_context: list[dict] = []) -> dict:
        client_id = portfolio_data.get("client_id", "")

        if not self._live:
            mock = MOCK_NARRATIVES.get(client_id, {})
            return {
                "narrative": mock.get("narrative", "Narrative not available in mock mode."),
                "key_points": mock.get("key_points", []),
                "data_sources": mock.get("data_sources", ["Mock data"]),
            }

        import json
        summary = {
            "client": portfolio_data["client_name"],
            "total_value": portfolio_data["total_value"],
            "total_return_pct": portfolio_data["total_return_pct"],
            "ytd_return_pct": portfolio_data["ytd_return_pct"],
            "allocation": portfolio_data["allocation"],
            "top_holdings": portfolio_data["holdings"][:5],
            "risk_alerts": portfolio_data["risk_alerts"],
        }

        user_content = f"Portfolio data:\n{json.dumps(summary)}"
        if doc_context:
            snippets = "\n".join(f"- [{d['source']}] {d['content']}" for d in doc_context)
            user_content += f"\n\nDocument context from uploaded statements and records:\n{snippets}"

        response = self._client.chat.completions.create(
            model=config.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "narrative": result.get("narrative", ""),
            "key_points": result.get("key_points", []),
            "data_sources": ["Fabric SQL", "Azure OpenAI", "Azure AI Search"],
        }


openai_service = OpenAIService()
