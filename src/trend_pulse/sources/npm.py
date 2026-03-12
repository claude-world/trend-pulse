"""npm download trends via registry API (free, no auth)."""

from __future__ import annotations

import asyncio

import httpx

from .base import TrendSource, TrendItem


class NpmSource(TrendSource):
    name = "npm"
    description = "npm - JavaScript package download trends"
    requires_auth = False
    rate_limit = "unlimited (public API)"

    API = "https://api.npmjs.org/downloads/point"

    # Curated list of hot JS packages to track
    HOT_PACKAGES = [
        "react", "next", "vue", "svelte", "astro",
        "vite", "esbuild", "bun", "typescript", "zod",
        "trpc", "prisma", "drizzle-orm", "hono", "effect",
        "vitest", "playwright", "ai", "langchain", "ollama",
    ]

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        packages = self.HOT_PACKAGES[:count]

        async with httpx.AsyncClient(timeout=15) as client:
            tasks = [self._fetch_package(client, pkg) for pkg in packages]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        items = [r for r in results if isinstance(r, TrendItem)]
        items.sort(key=lambda x: x.metadata.get("downloads_daily", 0), reverse=True)
        return items

    async def _fetch_package(self, client: httpx.AsyncClient, pkg: str) -> TrendItem:
        """Fetch daily and weekly downloads for a single package."""
        resp_day, resp_week = await asyncio.gather(
            client.get(f"{self.API}/last-day/{pkg}"),
            client.get(f"{self.API}/last-week/{pkg}"),
        )

        resp_day.raise_for_status()
        downloads = resp_day.json().get("downloads", 0)

        weekly = 0
        if resp_week.status_code == 200:
            weekly = resp_week.json().get("downloads", 0)

        weekly_avg = weekly / 7 if weekly else 0
        growth = (downloads / weekly_avg - 1) * 100 if weekly_avg > 0 else 0

        return TrendItem(
            keyword=pkg,
            score=min(downloads / 50000, 100),  # 5M/day = 100
            source=self.name,
            url=f"https://www.npmjs.com/package/{pkg}",
            traffic=f"{downloads:,} downloads/day",
            category="javascript",
            metadata={
                "downloads_daily": downloads,
                "downloads_weekly": weekly,
                "daily_growth": round(growth, 1),
            },
        )
