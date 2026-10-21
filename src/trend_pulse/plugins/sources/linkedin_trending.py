"""LinkedIn trending news and topics (public feed, no auth).

Fetches trending professional topics from LinkedIn's news page when it is
served publicly. LinkedIn News currently sends anonymous visitors to a
marketing page (and its APIs need OAuth), so this source returns no items
until that changes.
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

    # LinkedIn public news page (no auth)
    NEWS_URL = "https://www.linkedin.com/news/trending-topics/"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        # The voyager API (feed/trendingNewsArticles) needs a logged-in session, so only
        # the public news page is tried
        try:
            return await self._fetch_news_page(count)
        except Exception:
            return []

    async def _fetch_news_page(self, count: int) -> list[TrendItem]:
        """Scrape LinkedIn news trending page."""
        async with httpx.AsyncClient(timeout=15, headers=self.HEADERS, follow_redirects=True) as client:
            resp = await client.get(self.NEWS_URL)
            resp.raise_for_status()
            text = resp.text

        # Anonymous visitors get redirected (via /today) to a business.linkedin.com
        # marketing page whose headings are nav labels, not news
        if resp.url.host != "www.linkedin.com" or not resp.url.path.startswith("/news/"):
            return []

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
