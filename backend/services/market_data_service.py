"""
External market data service.
Fetches latest prices and indices. Falls back to cached mock prices.

When MARKET_DATA_API_KEY is set, fetches from Alpha Vantage.
Replace the implementation with your preferred provider if needed.
"""

import config
import httpx

# Cached mock prices used when the live API is not configured
MOCK_PRICES: dict[str, float] = {
    "AAPL":  189.30,
    "MSFT":  415.20,
    "NVDA":  875.40,
    "AMZN":  185.20,
    "GSK":    16.82,
    "INTU":  634.50,
    "VOD":     0.74,
    "GOLD":  162.00,
    "UK10Y": 982.50,
    "US30Y": 965.10,
    "UK5Y":  978.20,
}

MOCK_MARKET_SUMMARY = {
    "FTSE 100": {"value": 8142.15, "change_pct": 0.32},
    "S&P 500":  {"value": 5241.53, "change_pct": -0.18},
    "Gold":     {"value": 2348.60, "change_pct": 0.55},
    "GBP/USD":  {"value": 1.2715,  "change_pct": -0.08},
}


class MarketDataService:
    _BASE = "https://www.alphavantage.co/query"

    def __init__(self):
        self._live = config.market_data_enabled()
        if not self._live:
            print("[MarketDataService] Running in mock mode (MARKET_DATA_API_KEY not set)")

    async def get_price(self, symbol: str) -> float | None:
        if not self._live:
            return MOCK_PRICES.get(symbol)

        # PLACEHOLDER ─ Alpha Vantage global quote
        # async with httpx.AsyncClient() as client:
        #     resp = await client.get(self._BASE, params={
        #         "function": "GLOBAL_QUOTE",
        #         "symbol": symbol,
        #         "apikey": config.MARKET_DATA_API_KEY,
        #     })
        #     data = resp.json()
        #     return float(data["Global Quote"]["05. price"])
        raise NotImplementedError

    async def get_market_summary(self) -> dict:
        if not self._live:
            return MOCK_MARKET_SUMMARY

        # PLACEHOLDER ─ fetch FTSE, S&P, Gold, FX
        raise NotImplementedError


market_data_service = MarketDataService()
