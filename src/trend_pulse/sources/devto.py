"""dev.to via public API (free, no auth)."""

from __future__ import annotations

import httpx

from .base import TrendSource, TrendItem


class DevToSource(TrendSource):
    name = "devto"
    description = "dev.to - developer community articles"
    requires_auth = False
    rate_limit = "unlimited (public API)"

    API_URL = "https://dev.to/api/articles"

    def _parse_articles(self, articles: list) -> list[TrendItem]:
        items: list[TrendItem] = []
        for article in articles:
            reactions = article.get("public_reactions_count", 0)
            items.append(TrendItem(
                keyword=article.get("title", ""),
                score=min(reactions / 5, 100),  # 500 reactions = 100
                source=self.name,
                url=article.get("url", ""),
                traffic=f"{reactions} reactions",
                category="tech",
                published=article.get("published_at", ""),
                metadata={
                    "id": article.get("id", ""),
                    "comments": article.get("comments_count", 0),
                    "author": article.get("user", {}).get("username", ""),
                    "tags": article.get("tag_list", []),
                },
            ))
        return items

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                self.API_URL,
                params={"top": 1, "per_page": count},
            )
            resp.raise_for_status()
            articles = resp.json()

        return self._parse_articles(articles)

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                self.API_URL,
                params={"per_page": 20, "tag": query},
            )
            resp.raise_for_status()
            articles = resp.json()

        return self._parse_articles(articles)
