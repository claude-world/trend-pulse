"""Google News via RSS feed (free, no auth)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from .base import TrendSource, TrendItem


class GoogleNewsSource(TrendSource):
    name = "google_news"
    description = "Google News RSS - top stories by country"
    requires_auth = False
    rate_limit = "unlimited (RSS)"

    GEO_LANG = {
        "TW": "zh-TW",
        "JP": "ja",
        "US": "en",
    }

    async def fetch_trending(self, geo: str = "US", count: int = 20) -> list[TrendItem]:
        lang = self.GEO_LANG.get(geo.upper(), "en") if geo else "en"
        gl = geo.upper() if geo else "US"
        url = f"https://news.google.com/rss?hl={lang}&gl={gl}&ceid={gl}:{lang}"

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        items: list[TrendItem] = []

        for i, item in enumerate(root.findall(".//item")):
            if i >= count:
                break

            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")

            # Rank-based score: first item=100, decrease by 3 per rank, min 10
            score = max(100 - i * 3, 10)

            items.append(TrendItem(
                keyword=title,
                score=score,
                source=self.name,
                url=link,
                category="news",
                published=pub_date,
                metadata={"geo": gl, "lang": lang},
            ))

        return items
