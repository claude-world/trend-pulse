"""小紅書 (Xiaohongshu / RED) trending topics (no auth for public endpoints).

Xiaohongshu's explore/trending page uses internal APIs.
This implementation attempts to access public endpoints without auth.
For more reliable access, consider xiaohongshu-cli (pip install xiaohongshu-cli).
"""

from __future__ import annotations

import json
import re

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem

try:
    # Optional: xiaohongshu-cli provides better API access
    import xiaohongshu as _xhs_module  # type: ignore[import]  # noqa: F401
    _XHS_AVAILABLE = True
except ImportError:
    _XHS_AVAILABLE = False


class XiaohongshuSource(PluginSource):
    name = "xiaohongshu"
    description = "小紅書 Xiaohongshu - trending topics and hot content on RED (Chinese lifestyle platform)"
    requires_auth = False
    rate_limit = "moderate"
    category = "social"
    frequency = "realtime"
    difficulty = "medium"

    # XHS public endpoints
    HOT_URL = "https://www.xiaohongshu.com/explore"
    API_URL = "https://edith.xiaohongshu.com/api/sns/web/v1/homefeed"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://www.xiaohongshu.com",
        "Referer": "https://www.xiaohongshu.com/",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        # Note: Xiaohongshu may be geo-blocked outside mainland China.
        # For reliable access, use a proxy or mainland China server.
        try:
            return await self._fetch_homefeed(count)
        except Exception:
            pass
        try:
            return await self._fetch_scrape(count)
        except Exception:
            return []

    async def _fetch_homefeed(self, count: int) -> list[TrendItem]:
        """Try XHS's internal homefeed API."""
        payload = {
            "cursor_score": "",
            "num": count,
            "refresh_type": 1,
            "note_index": 0,
            "unread_begin_note_id": "",
            "unread_end_note_id": "",
            "unread_note_count": 0,
            "category": "homefeed_recommend",
            "search_key": "",
            "need_num": count,
            "image_formats": ["jpg", "webp", "avif"],
        }

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.post(self.API_URL, json=payload, headers=self.HEADERS)
            resp.raise_for_status()
            data = resp.json()

        return self._parse_homefeed(data, count)

    async def _fetch_scrape(self, count: int) -> list[TrendItem]:
        """Fallback: scrape explore page."""
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(self.HOT_URL, headers={
                **self.HEADERS,
                "Accept": "text/html,application/xhtml+xml",
            })
            resp.raise_for_status()

        return self._parse_html(resp.text, count)

    def _parse_homefeed(self, data: dict, count: int) -> list[TrendItem]:
        items: list[TrendItem] = []
        rank = 1

        notes = (
            data.get("data", {}).get("items", [])
            or data.get("items", [])
        )

        for note in notes[:count]:
            if not isinstance(note, dict):
                continue

            note_card = note.get("note_card", note)
            title = (
                note_card.get("title", "")
                or note_card.get("display_title", "")
                or note_card.get("desc", "")
            ).strip()

            if not title:
                continue

            note_id = note.get("id", "") or note_card.get("note_id", "")
            like_count = note_card.get("interact_info", {}).get("liked_count", 0) or 0
            if isinstance(like_count, str):
                like_count = int(re.sub(r"[^0-9]", "", like_count) or 0)

            items.append(TrendItem(
                keyword=title[:100],
                score=min(like_count / 10_000, 100) if like_count else max(0, 100 - rank),
                source=self.name,
                url=f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else "https://www.xiaohongshu.com/explore",
                traffic=f"{like_count:,} likes" if like_count else f"rank #{rank}",
                category="lifestyle",
                metadata={"note_id": note_id, "likes": like_count, "rank": rank},
            ))
            rank += 1

        return items

    def _parse_html(self, html: str, count: int) -> list[TrendItem]:
        """Extract note data from HTML bundle."""
        items: list[TrendItem] = []
        rank = 1

        # Look for initial data in script tags
        json_matches = re.findall(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*(?:;|\n)', html, re.DOTALL)
        for json_str in json_matches[:2]:
            try:
                data = json.loads(json_str)
                parsed = self._parse_homefeed(data, count)
                if parsed:
                    return parsed
            except (json.JSONDecodeError, ValueError):
                continue

        # Fallback: extract titles from meta tags
        titles = re.findall(r'<title[^>]*>([^<]+)</title>', html)
        for title in titles[:count]:
            title = title.strip()
            if title and len(title) > 5 and "小紅書" not in title:
                items.append(TrendItem(
                    keyword=title[:100],
                    score=max(0, 100 - rank),
                    source=self.name,
                    url="https://www.xiaohongshu.com/explore",
                    traffic=f"rank #{rank}",
                    category="lifestyle",
                    metadata={"rank": rank},
                ))
                rank += 1

        return items


def register() -> XiaohongshuSource:
    return XiaohongshuSource()
