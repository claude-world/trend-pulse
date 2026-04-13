"""Indie Hackers trending posts (free, no auth).

Indie Hackers is a community for bootstrapped founders and indie makers.
Uses their public RSS feed for trending discussions.
"""

from __future__ import annotations

import re

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class IndieHackersSource(PluginSource):
    name = "indie_hackers"
    description = "Indie Hackers - trending posts from the indie maker/founder community"
    requires_auth = False
    rate_limit = "unlimited (RSS)"
    category = "dev"
    frequency = "daily"

    # IH removed public RSS; use their internal API
    API_URL = "https://www.indiehackers.com/api/stories"
    POSTS_URL = "https://www.indiehackers.com/posts"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html, */*",
        "Referer": "https://www.indiehackers.com/",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        # Try JSON API first
        try:
            return await self._fetch_api(count)
        except Exception:
            pass

        # Fallback: scrape posts page
        return await self._fetch_scrape(count)

    async def _fetch_api(self, count: int) -> list[TrendItem]:
        params = {"orderBy": "hot", "limit": count}
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(self.API_URL, params=params, headers=self.HEADERS)
            resp.raise_for_status()
            data = resp.json()

        items: list[TrendItem] = []
        rank = 1

        stories = data if isinstance(data, list) else data.get("stories", data.get("data", []))
        for story in stories[:count]:
            if not isinstance(story, dict):
                continue
            title = story.get("title", "").strip()
            url = story.get("url", "") or f"https://www.indiehackers.com/post/{story.get('id', '')}"
            votes = story.get("votes", 0) or story.get("upvoteCount", 0) or 0

            if not title:
                continue

            items.append(TrendItem(
                keyword=title,
                score=min(votes / 50, 100) if votes else max(0, 100 - rank),
                source=self.name,
                url=url,
                traffic=f"{votes} votes" if votes else f"rank #{rank}",
                category="startup",
                metadata={"votes": votes, "rank": rank},
            ))
            rank += 1

        return items

    async def _fetch_scrape(self, count: int) -> list[TrendItem]:
        """Scrape posts page as fallback."""
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(self.POSTS_URL, headers=self.HEADERS)
            resp.raise_for_status()
            html = resp.text

        items: list[TrendItem] = []
        rank = 1
        seen: set[str] = set()

        # Extract post links from IH
        matches = re.findall(
            r'<a[^>]+href="(/post/[^"]+)"[^>]*>([^<]{10,100})</a>',
            html,
        )
        for path, title in matches[:count]:
            title = title.strip()
            if not title or title in seen:
                continue
            seen.add(title)
            items.append(TrendItem(
                keyword=title,
                score=max(0, 100 - rank),
                source=self.name,
                url=f"https://www.indiehackers.com{path}",
                traffic=f"rank #{rank}",
                category="startup",
                metadata={"rank": rank},
            ))
            rank += 1

        return items


def register() -> IndieHackersSource:
    return IndieHackersSource()
