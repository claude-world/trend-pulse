"""Mastodon trending via public API (free, no auth)."""

from __future__ import annotations

import httpx

from .base import TrendSource, TrendItem


class MastodonSource(TrendSource):
    name = "mastodon"
    description = "Mastodon trending tags, statuses, and links (public API)"
    requires_auth = False
    rate_limit = "300 req/5min per instance"

    DEFAULT_INSTANCE = "https://mastodon.social"

    def __init__(self, instance: str = DEFAULT_INSTANCE):
        self.instance = instance.rstrip("/")

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        items: list[TrendItem] = []
        async with httpx.AsyncClient(timeout=15) as client:
            # Trending tags
            resp = await client.get(
                f"{self.instance}/api/v1/trends/tags",
                params={"limit": min(count, 40)},
            )
            if resp.status_code == 200:
                for tag in resp.json():
                    history = tag.get("history", [{}])
                    uses_today = int(history[0].get("uses", 0)) if history else 0
                    accounts = int(history[0].get("accounts", 0)) if history else 0
                    items.append(TrendItem(
                        keyword=f"#{tag['name']}",
                        score=min(uses_today / 10, 100),
                        source=self.name,
                        url=f"{self.instance}/tags/{tag['name']}",
                        traffic=f"{uses_today} uses, {accounts} accounts",
                        category="social",
                        metadata={"type": "tag", "instance": self.instance},
                    ))

            # Trending links
            resp = await client.get(
                f"{self.instance}/api/v1/trends/links",
                params={"limit": min(count, 40)},
            )
            if resp.status_code == 200:
                for link in resp.json():
                    history = link.get("history", [{}])
                    uses = int(history[0].get("uses", 0)) if history else 0
                    items.append(TrendItem(
                        keyword=link.get("title", link.get("url", "")),
                        score=min(uses / 5, 100),
                        source=self.name,
                        url=link.get("url", ""),
                        traffic=f"{uses} shares",
                        category="news",
                        metadata={
                            "type": "link",
                            "provider": link.get("provider_name", ""),
                            "description": link.get("description", ""),
                            "instance": self.instance,
                        },
                    ))

        return items[:count]
