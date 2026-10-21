"""Line Today 台灣 trending articles (free, no auth).

Uses the public web API behind LINE TODAY's "即時熱門排行榜" (realtime most-viewed,
3-hour window). Falls back to the headline listing embedded in the tab page.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

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

    # Same request the 即時熱門排行榜 module on today.line.me/tw makes
    MOST_VIEW_URL = (
        "https://today.line.me/webapi/trending/category/mostView/listings/"
        "module:6555867c4085edd81c1bf16e"
    )
    PAGE_URL = "https://today.line.me/tw/v3/tab"
    ALL_CATEGORY = "100259"
    MAX_COUNT = 50
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        n = max(1, min(count, self.MAX_COUNT))
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            try:
                resp = await client.get(self.MOST_VIEW_URL, headers=self.HEADERS, params={
                    "country": "tw",
                    "targetContent": "ARTICLE",
                    "categories": f"{self.ALL_CATEGORY}:{n}",
                    "trendingEventPeriod": "THREE_HOUR",
                    "offset": 0,
                    "length": n,
                })
                if resp.status_code == 200:
                    items = self._parse(resp.json().get("items", []), count)
                    if items:
                        return items
            except Exception:
                pass

            # Fallback: headline listing server-rendered into the page's __NEXT_DATA__
            resp = await client.get(self.PAGE_URL, headers={**self.HEADERS, "Accept": "text/html"})
            resp.raise_for_status()
            return self._parse_page(resp.text, count)

    def _parse_page(self, page: str, count: int) -> list[TrendItem]:
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.DOTALL)
        if not m:
            return []
        try:
            fallback = json.loads(m.group(1))["props"]["pageProps"]["fallback"]
        except (ValueError, KeyError, TypeError):
            return []

        # Listing caches are keyed like '<moduleId>_{"offset":0,"length":10}'
        articles: list[dict] = []
        for key, value in fallback.items():
            if '"offset"' in key and isinstance(value, list):
                articles.extend(a for a in value if isinstance(a, dict))
        return self._parse(articles, count)

    def _parse(self, articles: list, count: int) -> list[TrendItem]:
        valid = [a for a in articles if isinstance(a, dict) and (a.get("title") or "").strip()]
        top_views = max((a.get("viewCount") or 0 for a in valid), default=0)

        items: list[TrendItem] = []
        seen: set[str] = set()
        for article in valid:
            title = article["title"].strip()
            if title in seen:
                continue
            seen.add(title)
            rank = len(items) + 1

            url_info = article.get("url") or {}
            url = url_info.get("url", "") if isinstance(url_info, dict) else ""
            if not url and isinstance(url_info, dict) and url_info.get("hash"):
                url = f"https://today.line.me/tw/v3/article/{url_info['hash']}"

            views = article.get("viewCount") or 0
            published = ""
            if article.get("publishTimeUnix"):
                published = datetime.fromtimestamp(
                    article["publishTimeUnix"] / 1000, tz=timezone.utc,
                ).isoformat()

            items.append(TrendItem(
                keyword=title,
                # Views relative to the most-read article; rank-based for listings without views
                score=round(views / top_views * 100, 1) if top_views else max(0, 100 - rank),
                source=self.name,
                url=url,
                traffic=f"{views:,} views" if views else f"rank #{rank}",
                category="news",
                published=published,
                metadata={
                    "publisher": article.get("publisher", ""),
                    "category": article.get("categoryName", ""),
                    "views": views,
                    "rank": rank,
                },
            ))
            if len(items) >= count:
                break
        return items


def register() -> LineTodaySource:
    return LineTodaySource()
