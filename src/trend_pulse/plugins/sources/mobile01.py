"""Mobile01 台灣 popular topics (free, no auth).

Mobile01 is Taiwan's largest tech/lifestyle forum.
Uses their public RSS feeds for hot topics.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class Mobile01Source(PluginSource):
    name = "mobile01"
    description = "Mobile01 - Taiwan's largest tech/lifestyle forum popular topics"
    requires_auth = False
    rate_limit = "moderate"
    category = "tw"
    frequency = "daily"

    RSS_URLS = [
        "https://www.mobile01.com/rss/hottopics.xml",
        "https://www.mobile01.com/rss/news.xml",
    ]
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml,application/xml,text/xml,*/*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "Referer": "https://www.mobile01.com/",
        "Origin": "https://www.mobile01.com",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for url in self.RSS_URLS:
                try:
                    resp = await client.get(url, headers=self.HEADERS)
                    if resp.status_code != 200:
                        continue
                    items = self._parse_rss(resp.content, count)
                    if items:
                        return items
                except Exception:
                    continue
        return []

    def _parse_rss(self, content: bytes, count: int) -> list[TrendItem]:
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return []

        items: list[TrendItem] = []
        rank = 1

        for entry in root.findall(".//item"):
            if rank > count:
                break

            title = entry.findtext("title", "").strip()
            link = entry.findtext("link", "").strip()
            pub_date = entry.findtext("pubDate", "")
            description = re.sub(r'<[^>]+>', '', entry.findtext("description", ""))[:200]

            category = "tech"
            if title:
                if "汽車" in title or "摩托" in title:
                    category = "automotive"
                elif "攝影" in title or "相機" in title:
                    category = "photography"

            if not title:
                continue

            items.append(TrendItem(
                keyword=title,
                score=max(0, 100 - rank),
                source=self.name,
                url=link,
                traffic=f"rank #{rank}",
                category=category,
                published=pub_date,
                metadata={"description": description.strip(), "rank": rank},
            ))
            rank += 1

        return items


def register() -> Mobile01Source:
    return Mobile01Source()
