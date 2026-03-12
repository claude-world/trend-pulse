"""Hacker News via official Firebase API + Algolia (free, no auth)."""

from __future__ import annotations

import httpx

from .base import TrendSource, TrendItem


class HackerNewsSource(TrendSource):
    name = "hackernews"
    description = "Hacker News top/best stories via Firebase API + Algolia search"
    requires_auth = False
    rate_limit = "unlimited"

    HN_API = "https://hacker-news.firebaseio.com/v0"
    ALGOLIA_API = "https://hn.algolia.com/api/v1"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            # Get top story IDs
            resp = await client.get(f"{self.HN_API}/topstories.json")
            resp.raise_for_status()
            story_ids = resp.json()[:count]

            # Fetch story details in parallel
            items: list[TrendItem] = []
            for sid in story_ids:
                r = await client.get(f"{self.HN_API}/item/{sid}.json")
                if r.status_code != 200:
                    continue
                story = r.json()
                if not story or story.get("type") != "story":
                    continue

                score_val = story.get("score", 0)
                items.append(TrendItem(
                    keyword=story.get("title", ""),
                    score=min(score_val / 5, 100),  # 500 points = 100
                    source=self.name,
                    url=story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                    traffic=f"{score_val} points",
                    category="tech",
                    metadata={
                        "id": sid,
                        "by": story.get("by", ""),
                        "comments": story.get("descendants", 0),
                        "hn_url": f"https://news.ycombinator.com/item?id={sid}",
                    },
                ))

        return items

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.ALGOLIA_API}/search",
                params={"query": query, "tags": "story", "hitsPerPage": 20},
            )
            resp.raise_for_status()
            data = resp.json()

        items: list[TrendItem] = []
        for hit in data.get("hits", []):
            score_val = hit.get("points", 0) or 0
            items.append(TrendItem(
                keyword=hit.get("title", ""),
                score=min(score_val / 5, 100),
                source=self.name,
                url=hit.get("url", ""),
                traffic=f"{score_val} points",
                category="tech",
                published=hit.get("created_at", ""),
                metadata={
                    "id": hit.get("objectID", ""),
                    "by": hit.get("author", ""),
                    "comments": hit.get("num_comments", 0),
                },
            ))

        return items
