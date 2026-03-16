"""Wikipedia most viewed pages via Pageviews API (free, no auth)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from .base import TrendSource, TrendItem


class WikipediaSource(TrendSource):
    name = "wikipedia"
    description = "Wikipedia most viewed pages by country (daily, free)"
    requires_auth = False
    rate_limit = "100 req/s"

    API = "https://wikimedia.org/api/rest_v1"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        # Use yesterday's data (today might not be ready yet)
        date = datetime.now(timezone.utc) - timedelta(days=1)
        year, month, day = date.strftime("%Y"), date.strftime("%m"), date.strftime("%d")

        # Map geo to Wikipedia project
        project = self._geo_to_project(geo)

        url = f"{self.API}/metrics/pageviews/top/{project}/all-access/{year}/{month}/{day}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers={"User-Agent": "trend-mcp/0.1"})
            resp.raise_for_status()

        data = resp.json()
        articles = []
        for item in data.get("items", [{}])[0].get("articles", []):
            title = item.get("article", "")
            # Skip special pages
            if title.startswith(("Special:", "Main_Page", "Wikipedia:", "-")):
                continue
            views = item.get("views", 0)
            articles.append(TrendItem(
                keyword=title.replace("_", " "),
                score=min(views / 100000, 100),  # 10M views = 100
                source=self.name,
                url=f"https://{project.split('.')[0]}.wikipedia.org/wiki/{title}",
                traffic=f"{views:,} views",
                category="knowledge",
                published=f"{year}-{month}-{day}",
                metadata={"project": project, "rank": item.get("rank", 0)},
            ))
            if len(articles) >= count:
                break

        return articles

    @staticmethod
    def _geo_to_project(geo: str) -> str:
        """Map geo code to Wikipedia project."""
        mapping = {
            "TW": "zh.wikipedia", "CN": "zh.wikipedia",
            "JP": "ja.wikipedia", "KR": "ko.wikipedia",
            "DE": "de.wikipedia", "FR": "fr.wikipedia",
            "ES": "es.wikipedia", "PT": "pt.wikipedia",
            "IT": "it.wikipedia", "RU": "ru.wikipedia",
        }
        return mapping.get(geo.upper(), "en.wikipedia") if geo else "en.wikipedia"
