"""PyPI download trends via pypistats.org API (free, no auth)."""

from __future__ import annotations

import httpx

from .base import TrendSource, TrendItem


class PyPISource(TrendSource):
    name = "pypi"
    description = "PyPI package download stats (daily, free)"
    requires_auth = False
    rate_limit = "once per day per endpoint"

    API = "https://pypistats.org/api"

    # Top Python packages to track (curated list of trending-relevant packages)
    HOT_PACKAGES = [
        "anthropic", "openai", "langchain", "llamaindex", "transformers",
        "fastapi", "pydantic", "httpx", "uvicorn", "polars",
        "ruff", "uv", "mcp", "crewai", "autogen",
        "streamlit", "gradio", "chainlit", "instructor", "outlines",
    ]

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        items: list[TrendItem] = []
        packages = self.HOT_PACKAGES[:count]

        async with httpx.AsyncClient(timeout=15) as client:
            for pkg in packages:
                try:
                    resp = await client.get(
                        f"{self.API}/packages/{pkg}/recent",
                        headers={"Accept": "application/json"},
                    )
                    if resp.status_code != 200:
                        continue
                    data = resp.json().get("data", {})
                    last_day = data.get("last_day", 0)
                    last_week = data.get("last_week", 0)
                    last_month = data.get("last_month", 0)

                    # Growth signal: daily vs weekly average
                    weekly_avg = last_week / 7 if last_week else 0
                    growth = (last_day / weekly_avg - 1) * 100 if weekly_avg > 0 else 0

                    items.append(TrendItem(
                        keyword=pkg,
                        score=min(last_day / 5000, 100),  # 500K/day = 100
                        source=self.name,
                        url=f"https://pypi.org/project/{pkg}/",
                        traffic=f"{last_day:,}/day ({last_week:,}/week)",
                        category="python",
                        metadata={
                            "last_day": last_day,
                            "last_week": last_week,
                            "last_month": last_month,
                            "daily_growth": round(growth, 1),
                        },
                    ))
                except Exception:
                    continue

        # Sort by daily downloads
        items.sort(key=lambda x: x.metadata.get("last_day", 0), reverse=True)
        return items
