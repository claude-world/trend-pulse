"""TikTok trending hashtags via Creative Center (free, no auth).

TikTok's Creative Center has a public trending hashtags page:
https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en

This source scrapes the public page. For more data, install playwright:
pip install 'trend-pulse[browser]' or pip install playwright && playwright install chromium
"""

from __future__ import annotations

import re

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem

try:
    from playwright.async_api import async_playwright  # type: ignore[import]
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


class TikTokTrendingSource(PluginSource):
    name = "tiktok_trending"
    description = "TikTok Trending - trending hashtags from TikTok Creative Center (playwright optional)"
    requires_auth = False
    rate_limit = "moderate"
    category = "social"
    frequency = "realtime"
    difficulty = "medium"

    # Creative Center public API endpoint (no auth required)
    API_URL = "https://ads.tiktok.com/creative_radar_api/v1/popular_trend/hashtag/list"
    CC_URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en",
        "Origin": "https://ads.tiktok.com",
    }

    _GEO_MAP = {
        "TW": "TW", "US": "US", "JP": "JP", "KR": "KR",
        "SG": "SG", "TH": "TH", "ID": "ID",
        "": "US",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        region = self._GEO_MAP.get(geo.upper(), "US")

        # Try JSON API first (fastest)
        try:
            return await self._fetch_api(region, count)
        except Exception:
            pass

        # Try playwright if available (more reliable)
        if _PLAYWRIGHT_AVAILABLE:
            try:
                return await self._fetch_playwright(region, count)
            except Exception:
                pass

        # Last resort: scrape static HTML
        return await self._fetch_html(region, count)

    async def _fetch_api(self, region: str, count: int) -> list[TrendItem]:
        """Try the Creative Center internal API."""
        params = {
            "period": 7,
            "country_code": region,
            "page_size": count,
            "page": 1,
            "sort_by": "popular",
        }

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(self.API_URL, params=params, headers=self.HEADERS)
            resp.raise_for_status()
            data = resp.json()

        return self._parse_api(data, count)

    async def _fetch_playwright(self, region: str, count: int) -> list[TrendItem]:
        """Use playwright for JS-rendered content."""
        url = f"{self.CC_URL}?region={region}"
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30_000)
            content = await page.content()
            await browser.close()

        return self._parse_html(content, count)

    async def _fetch_html(self, region: str, count: int) -> list[TrendItem]:
        """Fallback: static HTTP request (may not work for JS-rendered content)."""
        url = f"{self.CC_URL}?region={region}"
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                **self.HEADERS,
                "Accept": "text/html,application/xhtml+xml",
            })
            resp.raise_for_status()

        return self._parse_html(resp.text, count)

    def _parse_api(self, data: dict, count: int) -> list[TrendItem]:
        items: list[TrendItem] = []
        rank = 1

        hashtags = (
            data.get("data", {}).get("list", [])
            or data.get("list", [])
            or data.get("hashtag_list", [])
        )

        for tag in hashtags[:count]:
            if not isinstance(tag, dict):
                continue

            name = tag.get("hashtag_name", "") or tag.get("name", "")
            post_count = tag.get("post_num", 0) or tag.get("video_count", 0) or 0
            view_count = tag.get("video_views", 0) or tag.get("views", 0) or 0

            if not name:
                continue

            keyword = f"#{name}" if not name.startswith("#") else name
            items.append(TrendItem(
                keyword=keyword,
                score=min(view_count / 10_000_000, 100) if view_count else max(0, 100 - rank),
                source=self.name,
                url=f"https://www.tiktok.com/tag/{name.lstrip('#')}",
                traffic=f"{view_count:,} views" if view_count else f"{post_count:,} posts",
                category="social",
                metadata={
                    "hashtag": name,
                    "post_count": post_count,
                    "view_count": view_count,
                    "rank": rank,
                },
            ))
            rank += 1

        return items

    def _parse_html(self, html: str, count: int) -> list[TrendItem]:
        """Extract hashtag data from HTML/JS bundle."""
        items: list[TrendItem] = []
        rank = 1

        # Try to find JSON data embedded in the page
        patterns = [
            r'"hashtag_name"\s*:\s*"([^"]+)"[^}]*"post_num"\s*:\s*(\d+)',
            r'"name"\s*:\s*"#?([^"]+)"[^}]*"video_count"\s*:\s*(\d+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)
            if matches:
                for name, count_str in matches[:count]:
                    post_count = int(count_str)
                    keyword = f"#{name}" if not name.startswith("#") else name
                    items.append(TrendItem(
                        keyword=keyword,
                        score=min(post_count / 100_000, 100),
                        source=self.name,
                        url=f"https://www.tiktok.com/tag/{name.lstrip('#')}",
                        traffic=f"{post_count:,} posts",
                        category="social",
                        metadata={"hashtag": name, "post_count": post_count, "rank": rank},
                    ))
                    rank += 1
                if items:
                    return items

        return items


def register() -> TikTokTrendingSource:
    return TikTokTrendingSource()
