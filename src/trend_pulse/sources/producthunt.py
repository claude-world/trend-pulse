"""Product Hunt via HTML scraping (free, no auth)."""

from __future__ import annotations

import re

import httpx

from .base import TrendSource, TrendItem


class ProductHuntSource(TrendSource):
    name = "producthunt"
    description = "Product Hunt - top products and launches"
    requires_auth = False
    rate_limit = "reasonable (HTML scrape)"

    BASE_URL = "https://www.producthunt.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }

    def _parse_html(self, html_text: str) -> list[TrendItem]:
        items: list[TrendItem] = []
        # Match product cards: data-test="post-name" or similar patterns
        # PH renders structured data in JSON-LD or meta tags
        for match in re.finditer(
            r'"__typename":"Post"[^}]*?"name":"([^"]+)"[^}]*?"tagline":"([^"]+)"[^}]*?"slug":"([^"]+)"[^}]*?"votesCount":(\d+)',
            html_text,
        ):
            name, tagline, slug, votes_str = match.groups()
            votes = int(votes_str)
            items.append(TrendItem(
                keyword=name,
                score=min(votes / 10, 100),
                source=self.name,
                url=f"{self.BASE_URL}/posts/{slug}",
                traffic=f"{votes} votes",
                category="product",
                metadata={"tagline": tagline, "slug": slug},
            ))
        return items

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(self.BASE_URL, headers=self.HEADERS)
            resp.raise_for_status()
            html_text = resp.text

        return self._parse_html(html_text)[:count]

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                f"{self.BASE_URL}/search",
                params={"q": query},
                headers=self.HEADERS,
            )
            resp.raise_for_status()
            html_text = resp.text

        return self._parse_html(html_text)
