"""X (Twitter) trending topics — requires optional `twikit` dependency.

Install: pip install 'trend-pulse[social]' or pip install twikit

twikit provides access to X's internal API without an official API key.
https://github.com/d60/twikit
"""

from __future__ import annotations

try:
    from twikit import Client as TwikitClient  # type: ignore[import]
    _TWIKIT_AVAILABLE = True
except ImportError:
    _TWIKIT_AVAILABLE = False

import asyncio
import os

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class XTrendingSource(PluginSource):
    name = "x_trending"
    description = "X (Twitter) Trending - real-time trending topics on X/Twitter (requires twikit)"
    requires_auth = False  # twikit uses guest tokens, no login required for trends
    rate_limit = "moderate"
    category = "social"
    frequency = "realtime"
    difficulty = "medium"

    # WOEID codes for get_trends (Twitter/X location codes)
    _GEO_MAP = {
        "TW": 24865698,  # Taiwan
        "US": 23424977,  # United States
        "JP": 23424856,  # Japan
        "KR": 23424868,  # South Korea
        "HK": 24865698,  # Hong Kong (fallback to Taiwan)
        "": 1,           # Worldwide
    }

    # Public guest token endpoint fallback (no twikit needed)
    _GUEST_TOKEN_URL = "https://api.twitter.com/1.1/guest/activate.json"
    _TRENDS_URL = "https://api.twitter.com/1.1/trends/place.json"
    # Read bearer token from env var; no hardcoded fallback (set X_BEARER_TOKEN to use guest API)
    _BEARER = os.environ.get("X_BEARER_TOKEN", "")

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        if _TWIKIT_AVAILABLE:
            return await self._fetch_twikit(geo, count)
        # twikit not installed: install with pip install 'trend-pulse[social]'
        return []

    async def _fetch_twikit(self, geo: str, count: int) -> list[TrendItem]:
        """Use twikit for trending topics."""
        client = TwikitClient(language="zh-TW" if geo in ("TW", "HK") else "en-US")

        # twikit can fetch trending without login for basic trends
        try:
            trends = await asyncio.to_thread(
                client.get_trends,
                category="trending",
                count=count,
            )
        except Exception:
            # Fallback to guest API if twikit fails
            return await self._fetch_guest_api(geo, count)

        items: list[TrendItem] = []
        for rank, trend in enumerate(trends[:count], 1):
            name = getattr(trend, "name", str(trend))
            tweet_count = getattr(trend, "tweet_count", 0) or 0
            items.append(TrendItem(
                keyword=name,
                score=min(tweet_count / 50_000, 100) if tweet_count else max(0, 100 - rank),
                source=self.name,
                url=f"https://x.com/search?q={name.replace('#', '%23')}&src=trend_click",
                traffic=f"{tweet_count:,} tweets" if tweet_count else f"rank #{rank}",
                category="social",
                metadata={"tweet_count": tweet_count, "rank": rank},
            ))

        return items

    async def _fetch_guest_api(self, geo: str, count: int) -> list[TrendItem]:
        """Use Twitter public guest API for trends (requires X_BEARER_TOKEN env var)."""
        if not self._BEARER:
            return []
        woeid = self._GEO_MAP.get(geo.upper(), 1)

        async with httpx.AsyncClient(timeout=15) as client:
            # Get guest token
            token_resp = await client.post(
                self._GUEST_TOKEN_URL,
                headers={"Authorization": f"Bearer {self._BEARER}"},
            )
            token_resp.raise_for_status()
            guest_token = token_resp.json().get("guest_token", "")

            # Fetch trends
            trends_resp = await client.get(
                self._TRENDS_URL,
                params={"id": woeid},
                headers={
                    "Authorization": f"Bearer {self._BEARER}",
                    "x-guest-token": guest_token,
                },
            )
            trends_resp.raise_for_status()
            data = trends_resp.json()

        items: list[TrendItem] = []
        rank = 1

        if isinstance(data, list) and data:
            trends_list = data[0].get("trends", [])
        else:
            trends_list = []

        for trend in trends_list[:count]:
            name = trend.get("name", "")
            tweet_volume = trend.get("tweet_volume") or 0

            if not name:
                continue

            items.append(TrendItem(
                keyword=name,
                score=min(tweet_volume / 50_000, 100) if tweet_volume else max(0, 100 - rank),
                source=self.name,
                url=trend.get("url", f"https://x.com/search?q={name}"),
                traffic=f"{tweet_volume:,} tweets" if tweet_volume else f"rank #{rank}",
                category="social",
                metadata={"tweet_volume": tweet_volume, "woeid": woeid, "rank": rank},
            ))
            rank += 1

        return items


def register() -> XTrendingSource:
    if not _TWIKIT_AVAILABLE:
        # Still register — will use guest API fallback
        pass
    return XTrendingSource()
