"""Stack Overflow hot questions via public API (free, no auth)."""

from __future__ import annotations

import html
from datetime import datetime

import httpx

from .base import TrendSource, TrendItem


class StackOverflowSource(TrendSource):
    name = "stackoverflow"
    description = "Stack Overflow - hot questions"
    requires_auth = False
    rate_limit = "300 req/day (without key)"

    URL = "https://api.stackexchange.com/2.3/questions"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                self.URL,
                params={
                    "order": "desc",
                    "sort": "hot",
                    "site": "stackoverflow",
                    "pagesize": count,
                    "filter": "default",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        items: list[TrendItem] = []
        for item in data.get("items", []):
            score_val = item.get("score", 0)
            view_count = item.get("view_count", 0)
            items.append(TrendItem(
                keyword=html.unescape(item.get("title", "")),
                score=min(score_val / 5, 100),  # 500 votes = 100
                source=self.name,
                url=item.get("link", ""),
                traffic=f"{view_count} views",
                category="tech",
                published=datetime.utcfromtimestamp(item.get("creation_date", 0)).isoformat() + "Z",
                metadata={
                    "tags": item.get("tags", []),
                    "answer_count": item.get("answer_count", 0),
                    "is_answered": item.get("is_answered", False),
                    "owner": item.get("owner", {}).get("display_name", ""),
                },
            ))

        return items
