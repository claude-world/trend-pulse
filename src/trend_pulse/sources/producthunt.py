"""Product Hunt via the official Atom feed (free, no auth).

The feed lists the latest featured launches. It carries no vote counts,
so scores are rank-based.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET

import httpx

from .base import TrendSource, TrendItem
from .. import __version__

# Atom namespace
_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ProductHuntSource(TrendSource):
    name = "producthunt"
    description = "Product Hunt - top products and launches"
    requires_auth = False
    rate_limit = "reasonable (Atom feed)"

    BASE_URL = "https://www.producthunt.com"
    FEED_URL = "https://www.producthunt.com/feed"
    HEADERS = {
        "User-Agent": f"trend-pulse/{__version__} (github.com/claude-world/trend-pulse)",
        "Accept": "application/atom+xml",
    }

    def _parse_feed(self, xml_text: str) -> list[TrendItem]:
        root = ET.fromstring(xml_text)
        items: list[TrendItem] = []
        for entry in root.findall("atom:entry", _NS):
            name = (entry.findtext("atom:title", "", _NS) or "").strip()
            if not name:
                continue

            url = ""
            for link in entry.findall("atom:link", _NS):
                if link.get("rel", "alternate") == "alternate":
                    url = link.get("href", "")
                    break

            # The tagline is the first <p> of the HTML content
            content = entry.findtext("atom:content", "", _NS) or ""
            tagline_match = re.search(r"<p>\s*(.*?)\s*</p>", content, re.DOTALL)
            tagline = html.unescape(re.sub(r"<[^>]+>", "", tagline_match.group(1))).strip() if tagline_match else ""

            rank = len(items) + 1
            items.append(TrendItem(
                keyword=name,
                score=max(100 - (rank - 1) * 5, 10),  # Rank-based score
                source=self.name,
                url=url,
                traffic=f"rank #{rank}",
                category="product",
                published=entry.findtext("atom:published", "", _NS) or "",
                metadata={
                    "tagline": tagline,
                    "slug": url.rstrip("/").rsplit("/", 1)[-1] if url else "",
                    "author": entry.findtext("atom:author/atom:name", "", _NS) or "",
                },
            ))
        return items

    async def _fetch_feed(self) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(self.FEED_URL, headers=self.HEADERS)
            resp.raise_for_status()
            text = resp.text

        return self._parse_feed(text)

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        return (await self._fetch_feed())[:count]

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        """Search the latest launches in the feed by name or tagline."""
        q = query.lower()
        return [
            it for it in await self._fetch_feed()
            if q in it.keyword.lower() or q in it.metadata.get("tagline", "").lower()
        ]
