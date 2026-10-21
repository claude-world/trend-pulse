"""DexScreener trending tokens (free, no auth).

DexScreener provides real-time data on trending DEX tokens/pairs.
Completely public API, no authentication required.
"""

from __future__ import annotations

import asyncio

import httpx

from ... import __version__
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
    # Boost lists carry no token names; resolve them via the pairs-by-token endpoint
    TOKENS_URL = "https://api.dexscreener.com/tokens/v1/{chain}/{addresses}"
    TOKENS_BATCH = 30  # max addresses per tokens/v1 request
    HEADERS = {
        "User-Agent": f"trend-pulse/{__version__}",
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
            tokens = data if isinstance(data, list) else data.get("pairs", data.get("tokens", []))
            names = await self._fetch_names(client, [t for t in tokens[:count] if isinstance(t, dict)])

        return self._parse(data, count, names)

    async def _fetch_names(self, client: httpx.AsyncClient, tokens: list[dict]) -> dict[str, tuple[str, str]]:
        """Map lowercase token address -> (name, symbol). Best effort: failures yield {}."""
        by_chain: dict[str, list[str]] = {}
        for token in tokens:
            chain, address = token.get("chainId"), token.get("tokenAddress")
            if chain and address and address not in by_chain.setdefault(chain, []):
                by_chain[chain].append(address)

        async def _one(chain: str, addresses: list[str]) -> dict[str, tuple[str, str]]:
            found: dict[str, tuple[str, str]] = {}
            try:
                resp = await client.get(
                    self.TOKENS_URL.format(chain=chain, addresses=",".join(addresses)),
                    headers=self.HEADERS,
                )
                if resp.status_code != 200:
                    return found
                pairs = resp.json()
            except Exception:
                return found
            for pair in pairs if isinstance(pairs, list) else []:
                for side in ("baseToken", "quoteToken"):
                    info = pair.get(side) or {}
                    addr = (info.get("address") or "").lower()
                    if addr and addr not in found and (info.get("name") or info.get("symbol")):
                        found[addr] = (info.get("name", ""), info.get("symbol", ""))
            return found

        jobs = [
            _one(chain, addresses[i:i + self.TOKENS_BATCH])
            for chain, addresses in by_chain.items()
            for i in range(0, len(addresses), self.TOKENS_BATCH)
        ]
        names: dict[str, tuple[str, str]] = {}
        for result in await asyncio.gather(*jobs):
            names.update(result)
        return names

    def _parse(
        self,
        data: dict | list,
        count: int,
        names: dict[str, tuple[str, str]] | None = None,
    ) -> list[TrendItem]:
        items: list[TrendItem] = []
        rank = 1
        names = names or {}

        # DexScreener returns a list of token boosts
        tokens = data if isinstance(data, list) else data.get("pairs", data.get("tokens", []))
        tokens = [t for t in tokens[:count] if isinstance(t, dict)]
        top_amount = max((t.get("totalAmount", 0) or 0 for t in tokens), default=0)

        for token in tokens:
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
            if not (name or symbol) and token_address:
                name, symbol = names.get(token_address.lower(), ("", ""))

            amount = token.get("amount", 0) or 0
            total_amount = token.get("totalAmount", 0) or 0

            keyword = f"{name} ({symbol})" if name and symbol else (name or symbol or token_address[:8])
            if not keyword.strip():
                continue

            url = token.get("url", f"https://dexscreener.com/{chain_id}/{token_address}")

            items.append(TrendItem(
                keyword=keyword,
                # Boost total relative to the most-boosted token in this batch
                score=round(total_amount / top_amount * 100, 1) if top_amount else max(0, 100 - rank),
                source=self.name,
                url=url,
                traffic=f"boost: {total_amount or amount}",
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
