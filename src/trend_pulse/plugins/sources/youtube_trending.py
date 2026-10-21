"""YouTube most popular videos via the official YouTube Data API v3.

YouTube retired its Trending page in July 2025; the Data API's `mostPopular`
chart (videos.list) is the official replacement and now reflects the Trending
Music, Movies, and Gaming charts. It needs a free API key:

    export YOUTUBE_API_KEY=...   # Google Cloud console -> YouTube Data API v3

Without a key this source returns no items.
"""

from __future__ import annotations

import os

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class YouTubeTrendingSource(PluginSource):
    name = "youtube_trending"
    description = "YouTube Trending - most popular videos by region via the YouTube Data API (set YOUTUBE_API_KEY)"
    requires_auth = True  # free YouTube Data API key; YouTube has no keyless trending feed anymore
    rate_limit = "10,000 quota units/day (1 unit per call)"
    category = "global"
    frequency = "daily"

    API_URL = "https://www.googleapis.com/youtube/v3/videos"

    _GEO_MAP = {
        "TW": "TW", "US": "US", "JP": "JP", "KR": "KR",
        "HK": "HK", "SG": "SG", "": "US",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        api_key = os.environ.get("YOUTUBE_API_KEY", "")
        if not api_key:
            return []
        region = self._GEO_MAP.get(geo.upper(), geo.upper() or "US")

        try:
            return await self._fetch_api(api_key, region, count)
        except Exception:
            return []

    async def _fetch_api(self, api_key: str, region: str, count: int) -> list[TrendItem]:
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": max(1, min(count, 50)),  # API maximum is 50
        }
        # Key goes in a header, not the query string, so it never shows up in request logs
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.API_URL, params=params, headers={"X-Goog-Api-Key": api_key})
            resp.raise_for_status()
            data = resp.json()

        return self._parse(data, region, count)

    def _parse(self, data: dict, region: str, count: int) -> list[TrendItem]:
        items: list[TrendItem] = []

        for rank, video in enumerate(data.get("items", []), 1):
            snippet = video.get("snippet", {})
            stats = video.get("statistics", {})
            video_id = video.get("id", "")
            title = snippet.get("title", "")
            if not video_id or not title:
                continue

            views = int(stats.get("viewCount", 0) or 0)
            items.append(TrendItem(
                keyword=title,
                score=min(views / 1_000_000, 100),  # 100M views = 100
                source=self.name,
                url=f"https://www.youtube.com/watch?v={video_id}",
                traffic=f"{views:,} views",
                category="video",
                published=snippet.get("publishedAt", ""),
                metadata={
                    "video_id": video_id,
                    "channel": snippet.get("channelTitle", ""),
                    "views": views,
                    "likes": int(stats.get("likeCount", 0) or 0),
                    "comments": int(stats.get("commentCount", 0) or 0),
                    "category_id": snippet.get("categoryId", ""),
                    "region": region,
                    "rank": rank,
                },
            ))

            if len(items) >= count:
                break

        return items


def register() -> YouTubeTrendingSource:
    return YouTubeTrendingSource()
