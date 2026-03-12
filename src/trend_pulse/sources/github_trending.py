"""GitHub trending repos (free, no auth, scrape-based).

Falls back to Cloudflare Browser Rendering if HTML parsing fails and
CF_ACCOUNT_ID + CF_API_TOKEN are configured.
"""

from __future__ import annotations

import logging
import re

import httpx

from .base import TrendSource, TrendItem

logger = logging.getLogger(__name__)


class GitHubTrendingSource(TrendSource):
    name = "github"
    description = "GitHub trending repositories (daily/weekly/monthly)"
    requires_auth = False
    rate_limit = "reasonable (HTML scrape)"

    URL = "https://github.com/trending"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        # geo is repurposed as language filter (e.g. "python", "typescript")
        language = geo if geo and len(geo) > 2 else ""
        # Validate: only allow alphanumeric, hyphens, plus signs (valid GitHub language slugs)
        if language and not re.fullmatch(r"[A-Za-z0-9+\-]+", language):
            language = ""
        url = f"{self.URL}/{language}" if language else self.URL

        async with httpx.AsyncClient(
            timeout=15, follow_redirects=True, max_redirects=5
        ) as client:
            resp = await client.get(url, headers={"Accept": "text/html"})
            resp.raise_for_status()

        items = self._parse_html(resp.text, count)

        # Fallback: if HTML parsing returned nothing (e.g. GitHub switched to JS
        # rendering), try CF Browser Rendering when available.
        if not items:
            items = await self._fallback_browser(url, count)

        return items

    async def _fallback_browser(self, url: str, count: int) -> list[TrendItem]:
        """Attempt to fetch via CF Browser Rendering as fallback."""
        try:
            from .browser_renderer import is_available, extract_json
        except ImportError:
            return []

        if not is_available():
            logger.debug("CF Browser Rendering not configured, skipping fallback")
            return []

        logger.info("GitHub HTML parse returned 0 items, trying CF Browser Rendering")
        try:
            data = await extract_json(
                url,
                "Extract trending GitHub repositories. For each repo return: "
                "name (owner/repo format), description, stars_today (number), "
                "total_stars (number), language.",
            )
            return self._normalize_browser_data(data, count)
        except Exception:
            logger.warning("CF Browser Rendering fallback failed", exc_info=True)
            return []

    def _normalize_browser_data(self, data: dict, count: int) -> list[TrendItem]:
        """Convert CF extract_json output to TrendItems."""
        items: list[TrendItem] = []
        # The AI extraction may return a list under various keys
        repos = []
        if isinstance(data, list):
            repos = data
        elif isinstance(data, dict):
            for key in ("repositories", "repos", "items", "trending"):
                if isinstance(data.get(key), list):
                    repos = data[key]
                    break

        for repo in repos[:count]:
            if not isinstance(repo, dict):
                continue
            name = repo.get("name", "")
            if not name or "/" not in name:
                continue
            stars_today = int(repo.get("stars_today", 0) or 0)
            total_stars = int(repo.get("total_stars", 0) or 0)
            items.append(TrendItem(
                keyword=name,
                score=min(stars_today / 5, 100) if stars_today else 0,
                source=self.name,
                url=f"https://github.com/{name}",
                traffic=f"{stars_today} stars today ({total_stars:,} total)",
                category="tech",
                metadata={
                    "description": str(repo.get("description", ""))[:200],
                    "language": str(repo.get("language", "")),
                    "stars_today": stars_today,
                    "total_stars": total_stars,
                    "via": "cf-browser-rendering",
                },
            ))

        return items

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
