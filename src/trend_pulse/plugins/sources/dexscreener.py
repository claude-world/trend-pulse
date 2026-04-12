"""DexScreener trending tokens (free, no auth).

DexScreener provides real-time data on trending DEX tokens/pairs.
Completely public API, no authentication required.
"""

from __future__ import annotations

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class DexScreenerSource(PluginSource):
    name = "dexscreener"
    description = "DexScreener - real-time trending DEX tokens and meme coins"
    requires_auth = False
    rate_limit = "300 req/min"
    category = "crypto"
    frequency = "realtime"

    # Public trending endpoint — no API key needed
    TRENDING_URL = "https://api.dexscreener.com/token-boosts/top/v1"
    LATEST_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
    HEADERS = {
        "User-Agent": "trend-pulse/0.6.0",
        "Accept": "application/json",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.TRENDING_URL, headers=self.HEADERS)

            if resp.status_code != 200:
                # Try latest profiles as fallback
                resp = await client.get(self.LATEST_URL, headers=self.HEADERS)
                resp.raise_for_status()

            data = resp.json()

        return self._parse(data, count)

    def _parse(self, data: dict | list, count: int) -> list[TrendItem]:
        items: list[TrendItem] = []
        rank = 1

        # DexScreener returns a list of token boosts
        tokens = data if isinstance(data, list) else data.get("pairs", data.get("tokens", []))

        for token in tokens[:count]:
            if not isinstance(token, dict):
                continue

            chain_id = token.get("chainId", "")
            token_address = token.get("tokenAddress", "")

            # Nested token info
            token_info = token.get("token", {})
            if isinstance(token_info, dict):
                name = token_info.get("name", "")
                symbol = token_info.get("symbol", "")
            else:
                name = token.get("name", "")
                symbol = token.get("symbol", "")

            amount = token.get("amount", 0) or 0
            total_amount = token.get("totalAmount", 0) or 0

            keyword = f"{name} ({symbol})" if name and symbol else (name or symbol or token_address[:8])
            if not keyword.strip():
                continue

            url = token.get("url", f"https://dexscreener.com/{chain_id}/{token_address}")

            items.append(TrendItem(
                keyword=keyword,
                score=min(total_amount / 1000, 100) if total_amount else max(0, 100 - rank),
                source=self.name,
                url=url,
                traffic=f"boost: {amount}",
                category="crypto",
                metadata={
                    "chain": chain_id,
                    "address": token_address,
                    "symbol": symbol,
                    "amount": amount,
                    "total_amount": total_amount,
                    "rank": rank,
                },
            ))
            rank += 1

        return items


def register() -> DexScreenerSource:
    return DexScreenerSource()
