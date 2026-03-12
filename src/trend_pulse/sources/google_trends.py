"""Google Trends via RSS feed (free, no auth)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from .base import TrendSource, TrendItem


class GoogleTrendsSource(TrendSource):
    name = "google_trends"
    description = "Google Trends RSS - real-time trending searches by country"
    requires_auth = False
    rate_limit = "unlimited (RSS)"

    RSS_URL = "https://trends.google.com/trending/rss"
    NS = {"ht": "https://trends.google.com/trending/trendsapi/ht"}

    async def fetch_trending(self, geo: str = "US", count: int = 20) -> list[TrendItem]:
        params = {"geo": geo} if geo else {}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.RSS_URL, params=params)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        items: list[TrendItem] = []

        for i, item in enumerate(root.findall(".//item")):
            if i >= count:
                break

            title = item.findtext("title", "")
            traffic = item.findtext("ht:approx_traffic", "", self.NS)
            pub_date = item.findtext("pubDate", "")

            # Parse news articles
            news = []
            for ns_item in item.findall("ht:news_item", self.NS):
                news.append({
                    "title": ns_item.findtext("ht:news_item_title", "", self.NS),
                    "url": ns_item.findtext("ht:news_item_url", "", self.NS),
                    "source": ns_item.findtext("ht:news_item_source", "", self.NS),
                })

            # Normalize score: parse traffic like "200K+", "50K+", "500+"
            score = self._parse_traffic(traffic)

            items.append(TrendItem(
                keyword=title,
                score=min(score, 100),
                source=self.name,
                url=f"https://trends.google.com/trending?geo={geo}",
                traffic=traffic,
                published=pub_date,
                metadata={"news": news, "geo": geo},
            ))

        return items

    @staticmethod
    def _parse_traffic(traffic: str) -> float:
        """Convert traffic string to a 0-100 score."""
        t = traffic.replace("+", "").replace(",", "").strip().upper()
        if not t:
            return 0
        try:
            if "M" in t:
                return 100.0
            elif "K" in t:
                val = float(t.replace("K", ""))
                return min(val / 5, 100)  # 500K+ = 100
            else:
                val = float(t)
                return min(val / 50, 100)  # 5000 = 100
        except ValueError:
            return 0
