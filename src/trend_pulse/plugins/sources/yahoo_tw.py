"""Yahoo 新聞台灣 RSS feed (free, no auth).

Taiwan Yahoo News RSS — hot/trending news articles.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class YahooTWSource(PluginSource):
    name = "yahoo_tw"
    description = "Yahoo 新聞台灣 - Taiwan Yahoo News trending headlines via RSS"
    requires_auth = False
    rate_limit = "unlimited (RSS)"
    category = "tw"
    frequency = "realtime"

    RSS_URLS = [
        "https://tw.news.yahoo.com/rss/",
        "https://tw.news.yahoo.com/rss/politics",
        "https://tw.news.yahoo.com/rss/tech",
    ]
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml,application/xml,text/xml,*/*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "Referer": "https://tw.news.yahoo.com/",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        items: list[TrendItem] = []
        seen: set[str] = set()

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for url in self.RSS_URLS:
                if len(items) >= count:
                    break
                try:
                    resp = await client.get(url, headers=self.HEADERS)
                    resp.raise_for_status()
                    parsed = self._parse_rss(resp.content, count - len(items), seen)
                    items.extend(parsed)
                except Exception:
                    continue

        # Re-score by rank position
        for i, item in enumerate(items):
            item.score = max(0, 100 - i)

        return items[:count]

    def _parse_rss(self, content: bytes, limit: int, seen: set[str]) -> list[TrendItem]:
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return []

        items: list[TrendItem] = []
        rank = len(seen) + 1

        for entry in root.findall(".//item"):
            if len(items) >= limit:
                break

            title = entry.findtext("title", "").strip()
            link = entry.findtext("link", "").strip()
            pub_date = entry.findtext("pubDate", "")
            description = re.sub(r'<[^>]+>', '', entry.findtext("description", ""))[:200]

            if not title or title in seen:
                continue
            seen.add(title)

            items.append(TrendItem(
                keyword=title,
                score=max(0, 100 - rank),
                source=self.name,
                url=link,
                traffic=f"rank #{rank}",
                category="news",
                published=pub_date,
                metadata={"description": description.strip()},
            ))
            rank += 1

        return items


def register() -> YahooTWSource:
    return YahooTWSource()
