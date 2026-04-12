"""LinkedIn trending news and topics (public feed, no auth).

Fetches trending professional topics from LinkedIn's public news feed.
"""

from __future__ import annotations

import re

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class LinkedInTrendingSource(PluginSource):
    name = "linkedin_trending"
    description = "LinkedIn - trending professional news and topics"
    requires_auth = False
    rate_limit = "moderate"
    category = "professional"
    frequency = "daily"
    difficulty = "medium"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # LinkedIn public news API (no auth)
    NEWS_URL = "https://www.linkedin.com/news/trending-topics/"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        try:
            return await self._fetch_voyager(count)
        except Exception:
            pass
        try:
            return await self._fetch_news_page(count)
        except Exception:
            return []

    async def _fetch_voyager(self, count: int) -> list[TrendItem]:
        """Try LinkedIn's public voyager endpoint (no auth required for public news)."""
        url = "https://www.linkedin.com/voyager/api/feed/trendingNewsArticles"
        headers = {
            **self.HEADERS,
            "Accept": "application/vnd.linkedin.normalized+json+2.1",
            "x-li-lang": "en_US",
            "x-restli-protocol-version": "2.0.0",
        }
        async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
            resp = await client.get(url, params={"q": "trending", "count": count})
            resp.raise_for_status()
            data = resp.json()

        items: list[TrendItem] = []
        articles = data.get("elements", data.get("data", {}).get("elements", []))
        for i, art in enumerate(articles[:count]):
            if not isinstance(art, dict):
                continue
            title = art.get("title", art.get("headline", {}).get("text", ""))
            url_ = art.get("shareUrl", art.get("url", ""))
            if not title:
                continue
            score = max(10.0, 100.0 - i * 5)
            items.append(TrendItem(
                keyword=title[:100],
                score=score,
                source=self.name,
                url=url_,
                category="professional",
            ))
        return items

    async def _fetch_news_page(self, count: int) -> list[TrendItem]:
        """Scrape LinkedIn news trending page."""
        async with httpx.AsyncClient(timeout=15, headers=self.HEADERS, follow_redirects=True) as client:
            resp = await client.get(self.NEWS_URL)
            resp.raise_for_status()
            text = resp.text

        # Extract article titles
        matches = re.findall(r'<h[23][^>]*>\s*([^<]{10,120})\s*</h[23]>', text)
        seen: set[str] = set()
        items: list[TrendItem] = []
        for i, title in enumerate(matches):
            title = title.strip()
            if title in seen or len(title) < 10:
                continue
            seen.add(title)
            score = max(10.0, 90.0 - i * 4)
            items.append(TrendItem(
                keyword=title[:100],
                score=score,
                source=self.name,
                url=self.NEWS_URL,
                category="professional",
            ))
            if len(items) >= count:
                break
        return items

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        return []


def register() -> LinkedInTrendingSource:
    return LinkedInTrendingSource()
