"""巴哈姆特 (Bahamut) trending topics (free, no auth).

Bahamut is Taiwan's largest anime/game/entertainment community.
Uses their public ranking API.
"""

from __future__ import annotations

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class BahamutSource(PluginSource):
    name = "bahamut"
    description = "巴哈姆特 - Taiwan's largest anime/gaming community trending topics"
    requires_auth = False
    rate_limit = "moderate"
    category = "tw"
    frequency = "daily"

    # Bahamut's public hot articles endpoint
    API_URL = "https://api.gamer.com.tw/rank/v1/rank.php"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://home.gamer.com.tw/",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        params = {
            "bsn": "0",    # 0 = all categories
            "type": "all",
            "lang": "tw",
        }

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            try:
                resp = await client.get(self.API_URL, params=params, headers=self.HEADERS)
                if resp.status_code == 200 and resp.content:
                    try:
                        data = resp.json()
                        items = self._parse(data, count)
                        if items:
                            return items
                    except Exception:
                        pass
            except Exception:
                pass

            # Fallback: scrape rank page
            return await self._fallback_scrape(client, count)

    async def _fallback_scrape(self, client: httpx.AsyncClient, count: int) -> list[TrendItem]:
        """Fallback: scrape the public rank page."""
        import re
        resp = await client.get(
            "https://home.gamer.com.tw/rank.php",
            headers=self.HEADERS,
        )
        if resp.status_code != 200:
            return []

        # Extract hot articles from HTML
        items: list[TrendItem] = []
        rank = 1

        # Match article titles and links in rank page
        matches = re.findall(
            r'<a[^>]+href="(https://[^"]+bahamut[^"]*)"[^>]*>([^<]{5,})</a>',
            resp.text,
        )
        for url, title in matches[:count]:
            title = title.strip()
            if not title or len(title) < 3:
                continue
            items.append(TrendItem(
                keyword=title,
                score=max(0, 100 - rank),
                source=self.name,
                url=url,
                traffic=f"rank #{rank}",
                category="entertainment",
                metadata={"rank": rank},
            ))
            rank += 1
            if rank > count:
                break

        return items

    def _parse(self, data: dict, count: int) -> list[TrendItem]:
        items: list[TrendItem] = []
        rank = 1

        articles = (
            data.get("data", [])
            or data.get("rank", [])
            or data.get("items", [])
        )

        for article in articles[:count]:
            if isinstance(article, dict):
                title = (
                    article.get("title", "")
                    or article.get("subject", "")
                    or article.get("name", "")
                ).strip()
                url = article.get("url", "") or article.get("link", "")
                view_count = article.get("view", 0) or article.get("count", 0)
            else:
                continue

            if not title:
                continue

            items.append(TrendItem(
                keyword=title,
                score=min(view_count / 1000, 100) if view_count else max(0, 100 - rank),
                source=self.name,
                url=url,
                traffic=str(view_count) if view_count else f"rank #{rank}",
                category="entertainment",
                metadata={"rank": rank, "views": view_count},
            ))
            rank += 1

        return items


def register() -> BahamutSource:
    return BahamutSource()
