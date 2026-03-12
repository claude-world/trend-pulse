"""CoinGecko trending cryptocurrencies via public API (free, no auth)."""

from __future__ import annotations

import httpx

from .base import TrendSource, TrendItem


class CoinGeckoSource(TrendSource):
    name = "coingecko"
    description = "CoinGecko - trending cryptocurrencies"
    requires_auth = False
    rate_limit = "10-30 req/min (public)"

    URL = "https://api.coingecko.com/api/v3/search/trending"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.URL)
            resp.raise_for_status()
            data = resp.json()

        items: list[TrendItem] = []

        # Trending coins
        for index, entry in enumerate(data.get("coins", [])):
            coin = entry.get("item", {})
            if not coin:
                continue

            market_cap_rank = coin.get("market_cap_rank")
            if market_cap_rank:
                score = max(100 - market_cap_rank * 2, 10)
                traffic = f"Rank #{market_cap_rank}"
            else:
                score = max(100 - index * 10, 10)
                traffic = ""

            items.append(TrendItem(
                keyword=coin.get("name", ""),
                score=score,
                source=self.name,
                url=f'https://www.coingecko.com/en/coins/{coin.get("id", "")}',
                traffic=traffic,
                category="crypto",
                metadata={
                    "symbol": coin.get("symbol", ""),
                    "market_cap_rank": coin.get("market_cap_rank"),
                    "thumb": coin.get("thumb", ""),
                },
            ))

        # Trending NFTs
        for nft in data.get("nfts", []):
            items.append(TrendItem(
                keyword=nft.get("name", ""),
                score=50,
                source=self.name,
                url=f'https://www.coingecko.com/en/nft/{nft.get("id", "")}',
                category="crypto-nft",
                metadata={
                    "symbol": nft.get("symbol", ""),
                    "thumb": nft.get("thumb", ""),
                },
            ))

        return items[:count]
