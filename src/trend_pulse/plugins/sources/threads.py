"""Threads popular hashtags and content (free, limited without login).

Threads (by Meta) uses GraphQL internally. This implementation reads the
explore page when it is served publicly. Anonymous visitors are currently
redirected to the login page (and the official Threads API needs an OAuth
token), so this source returns no items until that changes.
"""

from __future__ import annotations

import json
import re

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class ThreadsSource(PluginSource):
    name = "threads"
    description = "Threads (Meta) - trending topics and popular posts on Threads"
    requires_auth = False
    rate_limit = "moderate (scraping)"
    category = "social"
    frequency = "realtime"

    EXPLORE_URL = "https://www.threads.com/explore"  # threads.net redirects here
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Fetch-Mode": "navigate",
    }

    # Fallback: Threads trending hashtags via their search suggestions
    SEARCH_URL = "https://www.threads.net/api/graphql"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        try:
            return await self._fetch_explore(count)
        except Exception:
            return await self._fetch_popular_hashtags(count)

    async def _fetch_explore(self, count: int) -> list[TrendItem]:
        """Scrape explore page for trending content."""
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(self.EXPLORE_URL, headers=self.HEADERS)
            resp.raise_for_status()

        # Explore is login-walled for anonymous visitors: nothing public to read
        if resp.url.path.startswith("/login"):
            return []

        html = resp.text

        # Try to extract __SSR_DATA__ or JSON embedded in script tags. A regex over
        # raw HTML would pick up page chrome and HTML entities (e.g. "&#x2022;"), not trends.
        json_matches = re.findall(r'__SSR_DATA__\s*=\s*(\{.*?\});', html, re.DOTALL)
        for json_str in json_matches[:3]:
            try:
                data = json.loads(json_str)
                extracted = self._extract_from_ssr(data, count)
                if extracted:
                    return extracted
            except (json.JSONDecodeError, ValueError):
                continue

        raise ValueError("Could not extract content from Threads explore page")

    async def _fetch_popular_hashtags(self, count: int) -> list[TrendItem]:
        """Alternative: use known popular Threads topics as fallback."""
        # Return empty rather than fake data
        return []

    def _extract_from_ssr(self, data: dict, count: int) -> list[TrendItem]:
        """Extract trending items from server-side rendered JSON data."""
        items: list[TrendItem] = []
        rank = 1

        def _walk(obj: object, depth: int = 0) -> None:
            nonlocal rank
            if rank > count or depth > 25:
                return
            if isinstance(obj, dict):
                # Look for post-like structures
                if obj.get("caption") or obj.get("text"):
                    text = (obj.get("caption") or obj.get("text") or "")
                    if isinstance(text, dict):
                        text = text.get("text", "")
                    if text and len(text) > 10:
                        items.append(TrendItem(
                            keyword=str(text)[:100],
                            score=max(0, 100 - rank),
                            source=self.name,
                            url=self.EXPLORE_URL,
                            traffic=f"rank #{rank}",
                            category="social",
                            metadata={"rank": rank},
                        ))
                        rank += 1
                for v in obj.values():
                    _walk(v, depth + 1)
            elif isinstance(obj, list):
                for v in obj:
                    _walk(v, depth + 1)

        _walk(data)
        return items


def register() -> ThreadsSource:
    return ThreadsSource()
