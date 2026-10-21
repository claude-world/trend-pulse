"""Reddit popular posts via official RSS/Atom feeds (free, no auth).

Reddit's JSON endpoints (/r/popular.json, /search.json) return 403 to
unauthenticated clients, so this source reads the public Atom feeds instead.
The feeds carry no vote counts, so scores are rank-based.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from .base import TrendSource, TrendItem
from .. import __version__

# Atom namespace
_NS = {"atom": "http://www.w3.org/2005/Atom"}


class RedditSource(TrendSource):
    name = "reddit"
    description = "Reddit - popular posts across all subreddits"
    requires_auth = False
    rate_limit = "strict (anonymous RSS, about 1 req/min)"

    URL = "https://www.reddit.com/r/popular/.rss"
    SEARCH_URL = "https://www.reddit.com/search.rss"
    USER_AGENT = f"trend-pulse/{__version__} (github.com/claude-world/trend-pulse)"

    def _parse_feed(self, xml_text: str) -> list[TrendItem]:
        root = ET.fromstring(xml_text)
        items: list[TrendItem] = []
        for entry in root.findall("atom:entry", _NS):
            title = (entry.findtext("atom:title", "", _NS) or "").strip()
            if not title:
                continue

            link_el = entry.find("atom:link", _NS)
            url = link_el.get("href", "") if link_el is not None else ""
            category_el = entry.find("atom:category", _NS)
            subreddit = category_el.get("term", "") if category_el is not None else ""
            author = entry.findtext("atom:author/atom:name", "", _NS) or ""

            rank = len(items) + 1
            items.append(TrendItem(
                keyword=title,
                score=max(100 - (rank - 1) * 5, 10),  # Rank-based score
                source=self.name,
                url=url,
                traffic=f"rank #{rank}",
                category="general",
                published=entry.findtext("atom:published", "", _NS) or "",
                metadata={
                    "subreddit": subreddit,
                    "author": author.removeprefix("/u/"),
                    "rank": rank,
                },
            ))
        return items

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                self.URL,
                params={"limit": min(count, 100)},
                headers={"User-Agent": self.USER_AGENT},
            )
            resp.raise_for_status()
            text = resp.text

        return self._parse_feed(text)[:count]

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                self.SEARCH_URL,
                params={"q": query, "sort": "relevance", "limit": 20},
                headers={"User-Agent": self.USER_AGENT},
            )
            resp.raise_for_status()
            text = resp.text

        return self._parse_feed(text)
