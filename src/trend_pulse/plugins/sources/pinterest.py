"""Pinterest trending topics (public search API, no auth).

Scrapes Pinterest's trending search terms from their open search API.
"""

from __future__ import annotations

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class PinterestSource(PluginSource):
    name = "pinterest"
    description = "Pinterest - trending search keywords and visual topics"
    requires_auth = False
    rate_limit = "moderate"
    category = "social"
    frequency = "daily"
    difficulty = "low"

    TRENDING_URL = "https://www.pinterest.com/resource/TrendingSearchesResource/get/"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://www.pinterest.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        try:
            return await self._fetch_trending_api(count)
        except Exception:
            pass
        try:
            return await self._fetch_explore(count)
        except Exception:
            return []

    async def _fetch_trending_api(self, count: int) -> list[TrendItem]:
        params = {
            "source_url": "/",
            "data": '{"options":{"country":"US"},"context":{}}',
        }
        async with httpx.AsyncClient(timeout=15, headers=self.HEADERS, follow_redirects=True) as client:
            resp = await client.get(self.TRENDING_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        items: list[TrendItem] = []
        trends = (
            data.get("resource_response", {}).get("data", {}).get("trending_searches", [])
            or data.get("resource_response", {}).get("data", [])
        )
        for i, entry in enumerate(trends[:count]):
            if isinstance(entry, dict):
                kw = entry.get("display_term", entry.get("term", ""))
            elif isinstance(entry, str):
                kw = entry
            else:
                continue
            if not kw:
                continue
            score = max(10.0, 100.0 - i * 4)
            items.append(TrendItem(
                keyword=kw,
                score=score,
                source=self.name,
                url=f"https://www.pinterest.com/search/pins/?q={kw.replace(' ', '+')}",
                category="visual",
            ))
        return items

    async def _fetch_explore(self, count: int) -> list[TrendItem]:
        """Fallback: scrape explore page for trending keywords."""
        import re
        async with httpx.AsyncClient(timeout=15, headers=self.HEADERS, follow_redirects=True) as client:
            resp = await client.get("https://www.pinterest.com/ideas/")
            resp.raise_for_status()
            text = resp.text

        # Extract topic headings from the page
        matches = re.findall(r'"displayName"\s*:\s*"([^"]{3,50})"', text)
        seen: set[str] = set()
        items: list[TrendItem] = []
        for i, kw in enumerate(matches):
            if kw in seen or len(kw) < 3:
                continue
            seen.add(kw)
            score = max(10.0, 90.0 - i * 3)
            items.append(TrendItem(
                keyword=kw,
                score=score,
                source=self.name,
                url=f"https://www.pinterest.com/search/pins/?q={kw.replace(' ', '+')}",
                category="visual",
            ))
            if len(items) >= count:
                break
        return items

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        return []


def register() -> PinterestSource:
    return PinterestSource()
