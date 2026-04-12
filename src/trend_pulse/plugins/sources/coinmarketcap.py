"""CoinMarketCap trending cryptocurrencies (free, no auth for public endpoints).

Uses CMC's public search/trending endpoint that requires no API key.
"""

from __future__ import annotations

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class CoinMarketCapSource(PluginSource):
    name = "coinmarketcap"
    description = "CoinMarketCap - trending & top-search cryptocurrencies"
    requires_auth = False
    rate_limit = "moderate"
    category = "crypto"
    frequency = "realtime"

    # Public endpoints (no API key)
    TRENDING_URL = "https://api.coinmarketcap.com/data-api/v3/topsearch/rank"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://coinmarketcap.com/",
        "Origin": "https://coinmarketcap.com",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        params = {
            "limit": min(count, 50),
            "timeframe": "24h",
        }

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(self.TRENDING_URL, params=params, headers=self.HEADERS)
            resp.raise_for_status()
            data = resp.json()

        return self._parse(data, count)

    def _parse(self, data: dict, count: int) -> list[TrendItem]:
        items: list[TrendItem] = []
        rank = 1

        coins = (
            data.get("data", {}).get("cryptoTopSearchRanks", [])
            or data.get("data", [])
            or data.get("cryptoTopSearchRanks", [])
        )

        for coin in coins[:count]:
            if not isinstance(coin, dict):
                continue

            symbol = coin.get("symbol", "")
            name = coin.get("name", "")
            slug = coin.get("slug", symbol.lower())
            price_change = coin.get("priceChange", {})
            change_24h = 0.0
            if isinstance(price_change, dict):
                change_24h = price_change.get("priceChange24h", 0.0) or 0.0

            keyword = f"{name} ({symbol})" if name else symbol
            if not keyword.strip():
                continue

            # Score based on positive momentum + rank
            score = max(0, 100 - rank) + min(max(change_24h, 0), 10)
            score = min(score, 100)

            items.append(TrendItem(
                keyword=keyword,
                score=score,
                source=self.name,
                url=f"https://coinmarketcap.com/currencies/{slug}/",
                traffic=f"rank #{rank}",
                category="crypto",
                metadata={
                    "symbol": symbol,
                    "name": name,
                    "slug": slug,
                    "change_24h": change_24h,
                    "rank": rank,
                },
            ))
            rank += 1

        return items


def register() -> CoinMarketCapSource:
    return CoinMarketCapSource()
