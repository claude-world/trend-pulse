"""ETtoday 新聞雲 RSS feed (free, no auth).

Taiwan news portal with real-time headlines via RSS.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class ETtodaySource(PluginSource):
    name = "ettoday"
    description = "ETtoday 新聞雲 - Taiwan real-time news headlines via RSS"
    requires_auth = False
    rate_limit = "unlimited (RSS)"
    category = "tw"
    frequency = "realtime"

    # ETtoday provides multiple RSS feeds
    RSS_FEEDS = [
        ("realtime", "https://feeds.feedburner.com/ettoday/realtime"),
        ("headline", "https://feeds.feedburner.com/ettoday/headline"),
    ]

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        for feed_name, feed_url in self.RSS_FEEDS:
            try:
                return await self._fetch_rss(feed_url, count)
            except Exception:
                continue
        return []

    async def _fetch_rss(self, url: str, count: int) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"Accept": "application/rss+xml,application/xml,text/xml"},
            )
            resp.raise_for_status()

        root = ET.fromstring(resp.content)
        items: list[TrendItem] = []
        rank = 1

        for item in root.findall(".//item"):
            if rank > count:
                break

            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            pub_date = item.findtext("pubDate", "")
            description = item.findtext("description", "").strip()
            # Remove HTML tags from description
            import re
            description = re.sub(r'<[^>]+>', '', description)[:200]

            if not title:
                continue

            items.append(TrendItem(
                keyword=title,
                score=max(0, 100 - rank),  # Rank-based scoring (1st = 99, last = 0)
                source=self.name,
                url=link,
                traffic=f"rank #{rank}",
                category="news",
                published=pub_date,
                metadata={"description": description, "rank": rank},
            ))
            rank += 1

        return items


def register() -> ETtodaySource:
    return ETtodaySource()
