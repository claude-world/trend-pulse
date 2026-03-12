"""Bluesky trending via public AT Protocol API (free, no auth)."""

from __future__ import annotations

import httpx

from .base import TrendSource, TrendItem


class BlueskySource(TrendSource):
    name = "bluesky"
    description = "Bluesky trending topics via public AT Protocol API"
    requires_auth = False
    rate_limit = "3000 req/5min (public)"

    API = "https://public.api.bsky.app/xrpc"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        items: list[TrendItem] = []
        async with httpx.AsyncClient(timeout=15) as client:
            # Try getTrendingTopics first
            resp = await client.get(f"{self.API}/app.bsky.unspecced.getTrendingTopics")
            if resp.status_code == 200:
                data = resp.json()
                topics = data.get("topics", [])
                for i, topic in enumerate(topics[:count]):
                    items.append(TrendItem(
                        keyword=topic.get("topic", topic.get("displayName", "")),
                        score=max(100 - i * 5, 10),  # Rank-based score
                        source=self.name,
                        url=f"https://bsky.app/search?q={topic.get('topic', '')}",
                        category="social",
                        metadata={"link": topic.get("link", "")},
                    ))

            # Also try getSuggestions for popular feeds
            if len(items) < count:
                resp = await client.get(
                    f"{self.API}/app.bsky.unspecced.getPopularFeedGenerators",
                    params={"limit": min(count - len(items), 25)},
                )
                if resp.status_code == 200:
                    for feed in resp.json().get("feeds", []):
                        items.append(TrendItem(
                            keyword=feed.get("displayName", ""),
                            score=min(feed.get("likeCount", 0) / 100, 100),
                            source=self.name,
                            url=feed.get("uri", ""),
                            traffic=f"{feed.get('likeCount', 0)} likes",
                            category="feed",
                            metadata={
                                "type": "feed",
                                "creator": feed.get("creator", {}).get("handle", ""),
                                "description": feed.get("description", "")[:200],
                            },
                        ))

        return items[:count]

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.API}/app.bsky.feed.searchPosts",
                params={"q": query, "limit": 25, "sort": "top"},
            )
            if resp.status_code != 200:
                return []

            items: list[TrendItem] = []
            for post in resp.json().get("posts", []):
                record = post.get("record", {})
                likes = post.get("likeCount", 0)
                reposts = post.get("repostCount", 0)
                replies = post.get("replyCount", 0)
                engagement = likes + reposts * 3 + replies * 2

                items.append(TrendItem(
                    keyword=record.get("text", "")[:100],
                    score=min(engagement / 10, 100),
                    source=self.name,
                    url=f"https://bsky.app/profile/{post.get('author', {}).get('handle', '')}/post/{post.get('uri', '').split('/')[-1]}",
                    traffic=f"{likes}L {reposts}R {replies}C",
                    category="social",
                    metadata={
                        "author": post.get("author", {}).get("handle", ""),
                        "created_at": record.get("createdAt", ""),
                    },
                ))

        return items
