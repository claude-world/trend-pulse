"""Pinterest trending search keywords (Pinterest Trends, no auth).

Uses the JSON endpoint behind the public "Search trends" table on
https://trends.pinterest.com, which serves anonymous visitors.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ... import __version__
from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class PinterestSource(PluginSource):
    name = "pinterest"
    description = "Pinterest - trending search keywords from Pinterest Trends"
    requires_auth = False
    rate_limit = "moderate"
    category = "social"
    frequency = "daily"
    difficulty = "low"

    TRENDS_URL = "https://trends.pinterest.com/top_trends_filtered/"
    HEADERS = {
        "User-Agent": f"trend-pulse/{__version__} (github.com/claude-world/trend-pulse)",
        "Accept": "application/json",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        country = geo.upper() or "US"
        try:
            return await self._fetch_top_trends(country, count)
        except httpx.HTTPStatusError as exc:
            # Pinterest Trends covers a subset of countries (no JP/TW/AU); 400 = unsupported
            if exc.response.status_code == 400 and country != "US":
                try:
                    return await self._fetch_top_trends("US", count)
                except Exception:
                    return []
            return []
        except Exception:
            return []

    async def _fetch_top_trends(self, country: str, count: int) -> list[TrendItem]:
        # Same defaults as the trends.pinterest.com "Search trends" table; endDate is
        # clamped server-side to the latest week with data
        params = {
            "lookbackWindow": 2,
            "endDate": datetime.now(timezone.utc).date().isoformat(),
            "rankingMethod": 3,
            "country": country,
            "trendsPreset": 3,
            "numTermsToReturn": max(1, min(count, 50)),
        }
        async with httpx.AsyncClient(timeout=15, headers=self.HEADERS, follow_redirects=True) as client:
            resp = await client.get(self.TRENDS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        values = [v for v in data.get("values", []) if isinstance(v, dict) and v.get("term")]
        # reverseRank: higher = better rank
        values.sort(key=lambda v: v.get("reverseRank", 0), reverse=True)

        items: list[TrendItem] = []
        for i, entry in enumerate(values[:count]):
            kw = entry["term"]
            mom = (entry.get("mom_change") or {}).get("value")
            items.append(TrendItem(
                keyword=kw,
                score=max(10.0, 100.0 - i * 4),
                source=self.name,
                url=f"https://www.pinterest.com/search/pins/?q={kw.replace(' ', '+')}",
                traffic=self._format_change(mom, "MoM"),
                category="visual",
                metadata={
                    "country": country,
                    "rank": i + 1,
                    "search_count": entry.get("searchCount"),
                    "wow_change": (entry.get("wow_change") or {}).get("value"),
                    "mom_change": mom,
                    "yoy_change": (entry.get("yoy_change") or {}).get("value"),
                },
            ))
        return items

    @staticmethod
    def _format_change(value: float | None, period: str) -> str:
        """Format a growth ratio the way Pinterest Trends shows it (1.5 -> '+150% MoM')."""
        if value is None:
            return ""
        if value >= 100:  # Pinterest caps the ratio at 100.01, shown as "10,000%+"
            return f"10,000%+ {period}"
        return f"{value * 100:+,.0f}% {period}"

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        return []


def register() -> PinterestSource:
    return PinterestSource()
