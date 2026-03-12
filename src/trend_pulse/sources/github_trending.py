"""GitHub trending repos (free, no auth, scrape-based)."""

from __future__ import annotations

import re

import httpx

from .base import TrendSource, TrendItem


class GitHubTrendingSource(TrendSource):
    name = "github"
    description = "GitHub trending repositories (daily/weekly/monthly)"
    requires_auth = False
    rate_limit = "reasonable (HTML scrape)"

    URL = "https://github.com/trending"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        # geo is repurposed as language filter (e.g. "python", "typescript")
        language = geo if geo and len(geo) > 2 else ""
        url = f"{self.URL}/{language}" if language else self.URL

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={"Accept": "text/html"})
            resp.raise_for_status()

        return self._parse_html(resp.text, count)

    def _parse_html(self, html: str, count: int) -> list[TrendItem]:
        items: list[TrendItem] = []

        # Extract repo articles using regex (avoid heavy dependency)
        articles = re.findall(
            r'<article class="Box-row">(.+?)</article>',
            html,
            re.DOTALL,
        )

        for article in articles[:count]:
            # Repo name: /user/repo (must be a simple path, not login/sponsors)
            name_match = re.search(r'href="(/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"', article)
            repo_path = name_match.group(1).strip() if name_match else ""
            repo_name = repo_path.lstrip("/")
            if not repo_name or "/" not in repo_name:
                continue

            # Description
            desc_match = re.search(r'<p class="[^"]*col-9[^"]*">\s*(.+?)\s*</p>', article, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else ""
            description = re.sub(r'<[^>]+>', '', description).strip()

            # Stars today
            stars_match = re.search(r'(\d[\d,]*)\s+stars\s+today', article)
            stars_today = int(stars_match.group(1).replace(",", "")) if stars_match else 0

            # Total stars
            total_match = re.findall(r'href="[^"]*stargazers[^"]*"[^>]*>\s*([\d,]+)\s*</a>', article)
            total_stars = int(total_match[0].replace(",", "")) if total_match else 0

            # Language
            lang_match = re.search(r'<span itemprop="programmingLanguage">([^<]+)</span>', article)
            language = lang_match.group(1).strip() if lang_match else ""

            items.append(TrendItem(
                keyword=repo_name,
                score=min(stars_today / 5, 100),  # 500 stars/day = 100
                source=self.name,
                url=f"https://github.com{repo_path}",
                traffic=f"{stars_today} stars today ({total_stars:,} total)",
                category="tech",
                metadata={
                    "description": description[:200],
                    "language": language,
                    "stars_today": stars_today,
                    "total_stars": total_stars,
                },
            ))

        return items
