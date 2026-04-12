"""聯合新聞網 (UDN) trending news scraping (free, no auth).

Taiwan's United Daily News — hot news scraped from their homepage.
"""

from __future__ import annotations

import re

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class UDNSource(PluginSource):
    name = "udn"
    description = "聯合新聞網 UDN - Taiwan United Daily News trending headlines"
    requires_auth = False
    rate_limit = "moderate"
    category = "tw"
    frequency = "daily"

    NEWS_URL = "https://udn.com/news/index/6638"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "Referer": "https://udn.com/",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(self.NEWS_URL, headers=self.HEADERS)
            resp.raise_for_status()

        return self._parse(resp.text, count)

    def _parse(self, html: str, count: int) -> list[TrendItem]:
        items: list[TrendItem] = []
        rank = 1
        seen: set[str] = set()

        # UDN article links: /news/story/{category_id}/{article_id}
        matches = re.findall(
            r'<a[^>]+href="(https://udn\.com/news/story/[^"]+)"[^>]*>([^<]{4,})</a>',
            html,
        )

        for url, title in matches:
            if rank > count:
                break
            title = title.strip()
            if not title or title in seen or len(title) < 5:
                continue
            seen.add(title)

            items.append(TrendItem(
                keyword=title[:100],
                score=max(0, 100 - rank),
                source=self.name,
                url=url,
                traffic=f"rank #{rank}",
                category="news",
                metadata={"rank": rank},
            ))
            rank += 1

        return items


def register() -> UDNSource:
    return UDNSource()
