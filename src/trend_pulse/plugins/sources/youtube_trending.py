"""YouTube Trending via InnerTube API (free, no auth required).

Uses YouTube's internal API endpoint that the web frontend also uses.
Returns trending videos with view counts and engagement data.
"""

from __future__ import annotations

import json
import os
import re

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class YouTubeTrendingSource(PluginSource):
    name = "youtube_trending"
    description = "YouTube Trending - top trending videos worldwide or by region"
    requires_auth = False
    rate_limit = "reasonable (internal API)"
    category = "global"
    frequency = "daily"

    INNERTUBE_URL = "https://www.youtube.com/youtubei/v1/browse"
    # Read from env var; fallback is YouTube's well-known public web client key
    INNERTUBE_KEY = os.environ.get("YOUTUBE_INNERTUBE_KEY", "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8")
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }

    _GEO_MAP = {
        "TW": "TW", "US": "US", "JP": "JP", "KR": "KR",
        "HK": "HK", "SG": "SG", "": "US",
    }

    PAGE_URL = "https://www.youtube.com/feed/trending"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        region = self._GEO_MAP.get(geo.upper(), geo.upper() or "US")

        # Try HTML page scraping (ytInitialData embedded in page)
        try:
            return await self._fetch_html(region, count)
        except Exception:
            pass

        # Try InnerTube API as fallback
        try:
            return await self._fetch_innertube(region, count)
        except Exception:
            return []

    async def _fetch_html(self, region: str, count: int) -> list[TrendItem]:
        """Scrape YouTube trending page for ytInitialData."""
        params = {}
        if region and region != "US":
            params["gl"] = region

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(self.PAGE_URL, params=params, headers=self.HEADERS)
            resp.raise_for_status()
            html = resp.text

        # Extract ytInitialData JSON using JSONDecoder — avoids catastrophic backtracking
        # that `re.DOTALL` + `.*?` would cause on a 500KB+ HTML page.
        for marker in ("var ytInitialData = ", "ytInitialData = "):
            idx = html.find(marker)
            if idx != -1:
                start = html.find("{", idx)
                if start != -1:
                    try:
                        data, _ = json.JSONDecoder().raw_decode(html, start)
                        return self._parse(data, count)
                    except (ValueError, json.JSONDecodeError):
                        continue
        return []

    async def _fetch_innertube(self, region: str, count: int) -> list[TrendItem]:
        """Try the InnerTube internal API."""
        payload = {
            "browseId": "FEtrending",
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20240101",
                    "hl": "zh-TW" if region in ("TW", "HK") else "en",
                    "gl": region,
                },
            },
        }

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.post(
                self.INNERTUBE_URL,
                params={"key": self.INNERTUBE_KEY},
                json=payload,
                headers=self.HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

        return self._parse(data, count)

    def _parse(self, data: dict, count: int) -> list[TrendItem]:
        items: list[TrendItem] = []

        # Navigate InnerTube response structure
        try:
            tabs = data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]
        except (KeyError, TypeError):
            return items

        for tab in tabs:
            tab_renderer = tab.get("tabRenderer", {})
            if not tab_renderer.get("selected", False):
                # Try first tab if none selected
                if not tabs or tab != tabs[0]:
                    continue

            try:
                sections = (
                    tab_renderer["content"]["sectionListRenderer"]["contents"]
                )
            except (KeyError, TypeError):
                continue

            for section in sections:
                item_section = section.get("itemSectionRenderer", {})
                contents = item_section.get("contents", [])

                for content in contents:
                    shelf = content.get("shelfRenderer", {})
                    shelf_contents = (
                        shelf.get("content", {})
                        .get("expandedShelfContentsRenderer", {})
                        .get("items", [])
                    )

                    for video_item in shelf_contents:
                        vr = video_item.get("videoRenderer", {})
                        if not vr:
                            continue

                        video_id = vr.get("videoId", "")
                        title_runs = vr.get("title", {}).get("runs", [])
                        title = "".join(r.get("text", "") for r in title_runs)
                        if not title:
                            continue

                        view_text = (
                            vr.get("viewCountText", {}).get("simpleText", "")
                            or vr.get("viewCountText", {}).get("runs", [{}])[0].get("text", "")
                        )
                        views = self._parse_views(view_text)

                        channel_runs = vr.get("ownerText", {}).get("runs", [{}])
                        channel = channel_runs[0].get("text", "") if channel_runs else ""

                        items.append(TrendItem(
                            keyword=title,
                            score=min(views / 1_000_000, 100),  # 100M views = 100
                            source=self.name,
                            url=f"https://youtube.com/watch?v={video_id}",
                            traffic=view_text,
                            category="video",
                            metadata={
                                "video_id": video_id,
                                "channel": channel,
                                "views": views,
                            },
                        ))

                        if len(items) >= count:
                            return items

        return items

    @staticmethod
    def _parse_views(text: str) -> float:
        """Parse view count string like '1.2M views', '500K views'."""
        text = text.replace(",", "").replace(" views", "").replace("次觀看", "").strip()
        try:
            if "M" in text or "百萬" in text:
                return float(re.sub(r"[^0-9.]", "", text)) * 1_000_000
            elif "K" in text or "千" in text:
                return float(re.sub(r"[^0-9.]", "", text)) * 1_000
            elif text:
                return float(re.sub(r"[^0-9.]", "", text))
        except ValueError:
            pass
        return 0.0


def register() -> YouTubeTrendingSource:
    return YouTubeTrendingSource()
