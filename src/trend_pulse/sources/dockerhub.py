"""Docker Hub popular container images via public API (free, no auth)."""

from __future__ import annotations

import httpx

from .base import TrendSource, TrendItem


def _format_pulls(value: int) -> str:
    """Format pull count into human-readable string."""
    if value >= 1_000_000_000:
        return f"{value / 1e9:.1f}B pulls"
    elif value >= 1_000_000:
        return f"{value / 1e6:.0f}M pulls"
    elif value >= 1_000:
        return f"{value / 1e3:.0f}K pulls"
    return f"{value} pulls"


class DockerHubSource(TrendSource):
    name = "dockerhub"
    description = "Docker Hub - popular container images"
    requires_auth = False
    rate_limit = "100 req/5 min (public)"

    URL = "https://hub.docker.com/v2/repositories/library/"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                self.URL,
                params={"page_size": count, "ordering": "-pull_count"},
            )
            resp.raise_for_status()
            data = resp.json()

        items: list[TrendItem] = []
        for repo in data.get("results", []):
            pull_count = repo.get("pull_count", 0)
            items.append(TrendItem(
                keyword=repo.get("name", ""),
                score=min(pull_count / 1_000_000_000, 100),  # 100B pulls = 100
                source=self.name,
                url=f'https://hub.docker.com/_/{repo.get("name", "")}',
                traffic=_format_pulls(pull_count),
                category="devops",
                published=repo.get("last_updated", ""),
                metadata={
                    "star_count": repo.get("star_count", 0),
                    "pull_count": pull_count,
                    "description": (repo.get("description") or "")[:200],
                },
            ))

        return items
