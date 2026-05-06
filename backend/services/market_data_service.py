"""
External market data service.
Fetches latest prices and indices. Falls back to cached mock prices.

When MARKET_DATA_API_KEY is set, fetches from Alpha Vantage.
Includes helpers to fetch all ticker prices for a client's holdings and
optionally enrich those holdings with fresh market values.
"""

import config
import httpx
import ssl
import certifi
from typing import Any

try:
    import truststore
except ImportError:
    truststore = None

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

# Some portfolio symbols are internal aliases; map to tradable public tickers.
SYMBOL_OVERRIDES: dict[str, str] = {
    "GOLD": "IAU",
}

MARKET_SUMMARY_SYMBOLS: dict[str, str] = {
    "FTSE 100": "EWU",  # iShares MSCI United Kingdom ETF proxy
    "S&P 500": "SPY",
    "Gold": "IAU",
}


class MarketDataService:
    _BASE = "https://www.alphavantage.co/query"
    _TIMEOUT_SECONDS = 8.0

    def __init__(self):
        self._live = config.market_data_enabled()
        self._quote_cache: dict[str, dict[str, Any]] = {}
        self._ssl_context = self._create_ssl_context()
        if not self._live:
            print("[MarketDataService] Running in mock mode (MARKET_DATA_API_KEY not set)")

    async def get_price(self, symbol: str) -> float | None:
        quote = await self.get_quote(symbol)
        if not quote:
            return None
        return quote.get("price")

    async def get_quote(self, symbol: str) -> dict[str, Any] | None:
        clean_symbol = self._clean_symbol(symbol)
        if not clean_symbol:
            return None

        if clean_symbol in self._quote_cache:
            return self._quote_cache[clean_symbol]

        if not self._live:
            price = MOCK_PRICES.get(clean_symbol)
            if price is None:
                return None
            result = {
                "symbol": clean_symbol,
                "provider_symbol": clean_symbol,
                "price": price,
                "change_pct": 0.0,
                "source": "mock",
            }
            self._quote_cache[clean_symbol] = result
            return result

        provider_symbol = SYMBOL_OVERRIDES.get(clean_symbol, clean_symbol)
        data = await self._request_alpha_vantage(
            {
                "function": "GLOBAL_QUOTE",
                "symbol": provider_symbol,
                "apikey": config.MARKET_DATA_API_KEY,
            }
        )
        quote = (data or {}).get("Global Quote", {})
        price = self._to_float(quote.get("05. price"))

        if price is None:
            fallback = MOCK_PRICES.get(clean_symbol)
            if fallback is None:
                return None
            result = {
                "symbol": clean_symbol,
                "provider_symbol": provider_symbol,
                "price": fallback,
                "change_pct": 0.0,
                "source": "mock-fallback",
            }
            self._quote_cache[clean_symbol] = result
            return result

        result = {
            "symbol": clean_symbol,
            "provider_symbol": provider_symbol,
            "price": price,
            "change_pct": self._to_float(str(quote.get("10. change percent", "0")).rstrip("%")) or 0.0,
            "source": "live",
        }
        self._quote_cache[clean_symbol] = result
        return result

    async def get_prices_for_symbols(self, symbols: list[str]) -> dict[str, float | None]:
        prices: dict[str, float | None] = {}
        for symbol in symbols:
            clean_symbol = self._clean_symbol(symbol)
            if not clean_symbol:
                continue
            prices[clean_symbol] = await self.get_price(clean_symbol)
        return prices

    async def get_portfolio_ticker_data(self, holdings: list[dict]) -> dict[str, dict[str, Any] | None]:
        """
        Fetch quote data for all unique, non-cash ticker symbols in a portfolio.
        Expects each holding to include a `symbol` key.
        """
        symbols = {
            self._clean_symbol(h.get("symbol"))
            for h in holdings
            if self._clean_symbol(h.get("symbol")) not in (None, "", "CASH")
        }

        results: dict[str, dict[str, Any] | None] = {}
        for symbol in sorted(symbols):
            results[symbol] = await self.get_quote(symbol)
        return results

    async def enrich_holdings_with_market_data(self, holdings: list[dict]) -> list[dict]:
        """
        Update holding rows with live current_price / market_value / gain_loss where possible.
        This method only enriches the list passed in and does not perform any DB writes.
        """
        quotes = await self.get_portfolio_ticker_data(holdings)

        for holding in holdings:
            symbol = self._clean_symbol(holding.get("symbol"))
            if not symbol or symbol == "CASH":
                continue

            quote = quotes.get(symbol)
            if not quote:
                continue

            price = self._to_float(quote.get("price"))
            if price is None:
                continue

            quantity = self._to_float(holding.get("quantity")) or 0.0
            previous_market_value = self._to_float(holding.get("market_value")) or 0.0
            cost_basis = self._to_float(holding.get("cost_basis")) or 0.0
            gain_loss_pct = self._to_float(holding.get("gain_loss_pct"))

            if not cost_basis and previous_market_value and gain_loss_pct is not None and gain_loss_pct > -100:
                cost_basis = previous_market_value / (1 + gain_loss_pct / 100)

            market_value = quantity * price if quantity else previous_market_value
            gain_loss = market_value - cost_basis if cost_basis else 0.0

            holding["current_price"] = round(price, 2)
            holding["market_value"] = round(market_value, 2)
            holding["cost_basis"] = round(cost_basis, 2)
            holding["gain_loss"] = round(gain_loss, 2)
            if cost_basis:
                holding["gain_loss_pct"] = round((gain_loss / cost_basis) * 100, 2)

        return holdings

    async def get_market_summary(self) -> dict:
        if not self._live:
            return MOCK_MARKET_SUMMARY

        summary = {k: v.copy() for k, v in MOCK_MARKET_SUMMARY.items()}

        for label, symbol in MARKET_SUMMARY_SYMBOLS.items():
            quote = await self.get_quote(symbol)
            if quote:
                summary[label] = {
                    "value": quote.get("price", summary[label]["value"]),
                    "change_pct": quote.get("change_pct", 0.0),
                }

        gbp_usd = await self._fetch_fx_rate("GBP", "USD")
        if gbp_usd:
            summary["GBP/USD"] = gbp_usd

        return summary

    async def _fetch_fx_rate(self, from_currency: str, to_currency: str) -> dict[str, float] | None:
        data = await self._request_alpha_vantage(
            {
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": from_currency,
                "to_currency": to_currency,
                "apikey": config.MARKET_DATA_API_KEY,
            }
        )
        rate_obj = (data or {}).get("Realtime Currency Exchange Rate", {})
        value = self._to_float(rate_obj.get("5. Exchange Rate"))
        if value is None:
            return None

        # This endpoint does not return a direct daily change %, so keep 0.0.
        return {"value": value, "change_pct": 0.0}

    async def _request_alpha_vantage(self, params: dict[str, str]) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT_SECONDS, verify=self._ssl_context) as client:
                response = await client.get(self._BASE, params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            print(f"[MarketDataService] Alpha Vantage request failed ({exc}); using fallback")
            return None

        if not isinstance(data, dict):
            return None

        if "Note" in data or "Information" in data or "Error Message" in data:
            message = data.get("Note") or data.get("Information") or data.get("Error Message")
            print(f"[MarketDataService] Alpha Vantage response not usable ({message}); using fallback")
            return None

        return data

    def _clean_symbol(self, symbol: Any) -> str | None:
        if symbol is None:
            return None
        clean = str(symbol).strip().upper()
        return clean or None

    def _to_float(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _create_ssl_context(self) -> ssl.SSLContext:
        if truststore is not None:
            return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return ssl.create_default_context(cafile=certifi.where())


market_data_service = MarketDataService()
