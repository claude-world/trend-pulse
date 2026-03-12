"""Reddit popular posts via public JSON API (free, no auth)."""

from __future__ import annotations

from datetime import datetime

import httpx

from .base import TrendSource, TrendItem
from .. import __version__


class RedditSource(TrendSource):
    name = "reddit"
    description = "Reddit - popular posts across all subreddits"
    requires_auth = False
    rate_limit = "60 req/min (with User-Agent)"

    URL = "https://www.reddit.com/r/popular.json"
    USER_AGENT = f"trend-pulse/{__version__} (github.com/claude-world/trend-pulse)"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                self.URL,
                params={"limit": count},
                headers={"User-Agent": self.USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()

        items: list[TrendItem] = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            if not post:
                continue

            upvotes = post.get("score", 0)
            items.append(TrendItem(
                keyword=post.get("title", ""),
                score=min(upvotes / 500, 100),  # 50K upvotes = 100
                source=self.name,
                url=f'https://reddit.com{post.get("permalink", "")}',
                traffic=f"{upvotes} upvotes",
                category="general",
                published=datetime.utcfromtimestamp(post.get("created_utc", 0)).isoformat() + "Z",
                metadata={
                    "subreddit": post.get("subreddit", ""),
                    "author": post.get("author", ""),
                    "comments": post.get("num_comments", 0),
                    "upvote_ratio": post.get("upvote_ratio", 0),
                },
            ))

        return items
