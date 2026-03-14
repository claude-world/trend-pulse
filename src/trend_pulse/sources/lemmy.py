"""Lemmy (lemmy.world) via public API (free, no auth)."""

from __future__ import annotations

import httpx

from .base import TrendSource, TrendItem


class LemmySource(TrendSource):
    name = "lemmy"
    description = "Lemmy - federated link aggregator (lemmy.world)"
    requires_auth = False
    rate_limit = "unlimited (public API)"

    BASE_URL = "https://lemmy.world/api/v3"

    def _parse_posts(self, posts: list) -> list[TrendItem]:
        items: list[TrendItem] = []
        for entry in posts:
            post = entry.get("post", {})
            counts = entry.get("counts", {})
            community = entry.get("community", {})
            creator = entry.get("creator", {})

            if not post.get("name"):
                continue

            upvotes = counts.get("upvotes", 0)
            comments = counts.get("comments", 0)

            items.append(TrendItem(
                keyword=post["name"],
                score=min(upvotes / 50, 100),  # 5000 upvotes = 100
                source=self.name,
                url=post.get("ap_id", f"https://lemmy.world/post/{post.get('id', '')}"),
                traffic=f"{upvotes} upvotes",
                category="community",
                published=post.get("published", ""),
                metadata={
                    "id": post.get("id", ""),
                    "community": community.get("name", ""),
                    "creator": creator.get("name", ""),
                    "comments": comments,
                    "external_url": post.get("url", ""),
                },
            ))
        return items

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.BASE_URL}/post/list",
                params={"sort": "Hot", "limit": count},
            )
            resp.raise_for_status()
            data = resp.json()

        return self._parse_posts(data.get("posts", []))[:count]

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.BASE_URL}/search",
                params={
                    "q": query,
                    "type_": "Posts",
                    "sort": "TopAll",
                    "limit": 20,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return self._parse_posts(data.get("posts", []))
