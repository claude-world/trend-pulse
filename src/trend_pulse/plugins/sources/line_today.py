"""Line Today 台灣 trending articles (free, no auth).

Uses Line Today's public content API (same endpoint as their mobile app).
"""

from __future__ import annotations

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class LineTodaySource(PluginSource):
    name = "line_today"
    description = "Line Today 台灣 - trending news articles on Line Today TW"
    requires_auth = False
    rate_limit = "moderate"
    category = "tw"
    frequency = "realtime"

    # Line Today endpoints (try in order)
    API_URLS = [
        "https://today.line.me/tw/v3/tab/curation",
        "https://today.line.me/tw/v3/feed/hot",
        "https://today.line.me/api/v1/articles?country=tw&category=all&order=hot",
    ]
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW",
        "X-Requested-With": "XMLHttpRequest",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for url in self.API_URLS:
                try:
                    resp = await client.get(url, headers=self.HEADERS)
                    if resp.status_code != 200:
                        continue
                    ct = resp.headers.get("content-type", "")
                    if "json" not in ct:
                        continue
                    data = resp.json()
                    items = self._parse(data, count)
                    if items:
                        return items
                except Exception:
                    continue
        return []

    def _parse(self, data: dict, count: int) -> list[TrendItem]:
        items: list[TrendItem] = []
        rank = 1

        sections = data.get("sections", []) or data.get("data", {}).get("sections", [])
        for section in sections:
            articles = section.get("articles", []) or section.get("items", [])
            for article in articles:
                if rank > count:
                    return items

                title = (
                    article.get("title", "")
                    or article.get("headline", "")
                    or article.get("name", "")
                ).strip()

                if not title:
                    continue

                url = article.get("url", "") or article.get("contentUrl", "")
                pub_date = article.get("publishDate", "") or article.get("publishedAt", "")
                source_name = article.get("publisher", {}).get("name", "") if isinstance(article.get("publisher"), dict) else ""

                items.append(TrendItem(
                    keyword=title,
                    score=max(0, 100 - rank),
                    source=self.name,
                    url=url,
                    traffic=f"rank #{rank}",
                    category="news",
                    published=pub_date,
                    metadata={"publisher": source_name, "rank": rank},
                ))
                rank += 1

        return items


def register() -> LineTodaySource:
    return LineTodaySource()
