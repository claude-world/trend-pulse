"""Dcard trending posts via public API (free, no auth).

Dcard is Taiwan's largest anonymous social platform, popular with
college students and young professionals.
"""

from __future__ import annotations

import httpx

from .base import TrendSource, TrendItem


class DcardSource(TrendSource):
    name = "dcard"
    description = "Dcard - Taiwan's largest social platform trending posts"
    requires_auth = False
    rate_limit = "reasonable (public API)"

    BASE_URL = "https://www.dcard.tw/service/api/v2"

    def _parse_posts(self, posts: list) -> list[TrendItem]:
        items: list[TrendItem] = []
        for post in posts:
            if not post.get("title"):
                continue

            likes = post.get("likeCount", 0)
            comments = post.get("commentCount", 0)

            items.append(TrendItem(
                keyword=post["title"],
                score=min((likes + comments * 2) / 200, 100),
                source=self.name,
                url=f'https://www.dcard.tw/f/{post.get("forumAlias", "")}/p/{post.get("id", "")}',
                traffic=f"{likes} likes",
                category="social",
                published=post.get("createdAt", ""),
                metadata={
                    "id": post.get("id", ""),
                    "forum": post.get("forumAlias", ""),
                    "forum_name": post.get("forumName", ""),
                    "comments": comments,
                    "gender": post.get("gender", ""),
                    "school": post.get("school", ""),
                    "excerpt": post.get("excerpt", "")[:200],
                },
            ))
        return items

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.BASE_URL}/posts",
                params={"popular": "true", "limit": count},
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        return self._parse_posts(data)[:count]
