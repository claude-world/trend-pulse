"""Lobste.rs via JSON API (free, no auth)."""

from __future__ import annotations

import httpx

from .base import TrendSource, TrendItem


class LobstersSource(TrendSource):
    name = "lobsters"
    description = "Lobste.rs - community-driven tech news"
    requires_auth = False
    rate_limit = "unlimited (JSON API)"

    API_URL = "https://lobste.rs/hottest.json"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.API_URL)
            resp.raise_for_status()

        stories = resp.json()[:count]
        items: list[TrendItem] = []

        for story in stories:
            score_val = story.get("score", 0)
            items.append(TrendItem(
                keyword=story.get("title", ""),
                score=min(score_val / 3, 100),  # 300 points = 100
                source=self.name,
                url=story.get("url") or story.get("comments_url", ""),
                traffic=f'{score_val} points',
                category="tech",
                published=story.get("created_at", ""),
                metadata={
                    "id": story.get("short_id", ""),
                    "comments": story.get("comment_count", 0),
                    "submitter": story.get("submitter_user", ""),
                    "tags": story.get("tags", []),
                },
            ))

        return items
