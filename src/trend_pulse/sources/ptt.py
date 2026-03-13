"""PTT hot articles via public web scraping (free, no auth).

PTT (ptt.cc) is Taiwan's largest BBS forum, influential in public
opinion on topics like politics, tech jobs, and daily life.
"""

from __future__ import annotations

import re

import httpx

from .base import TrendSource, TrendItem


class PTTSource(TrendSource):
    name = "ptt"
    description = "PTT - Taiwan BBS hot articles"
    requires_auth = False
    rate_limit = "reasonable (web scrape)"

    BASE_URL = "https://www.ptt.cc"
    DEFAULT_BOARDS = ["Gossiping", "Tech_Job", "Stock", "HatePolitics", "LoL"]

    def _parse_articles(self, html: str, board: str) -> list[TrendItem]:
        """Parse PTT board HTML for article listings."""
        items: list[TrendItem] = []

        # Match article entries: push count, title, author, link
        pattern = re.compile(
            r'<div class="nrec"><span[^>]*>([^<]*)</span></div>'
            r'.*?<a href="([^"]+)">([^<]+)</a>'
            r'.*?<div class="author">([^<]*)</div>',
            re.DOTALL,
        )

        for match in pattern.finditer(html):
            push_text, href, title, author = match.groups()
            title = title.strip()
            if not title or title.startswith("(本文已被刪除)"):
                continue

            # Parse push count: number, "爆" (100+), or "X" prefix (negative)
            if push_text == "爆":
                pushes = 100
            elif push_text.startswith("X"):
                pushes = -10
            else:
                try:
                    pushes = int(push_text)
                except (ValueError, TypeError):
                    pushes = 0

            items.append(TrendItem(
                keyword=title,
                score=min(max(pushes, 0) / 1, 100),  # 100 pushes = 100
                source=self.name,
                url=f"{self.BASE_URL}{href}",
                traffic=f"{pushes} pushes",
                category="forum",
                metadata={
                    "board": board,
                    "author": author.strip(),
                    "pushes": pushes,
                },
            ))
        return items

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        all_items: list[TrendItem] = []

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            # PTT requires over-18 cookie for some boards
            client.cookies.set("over18", "1", domain="www.ptt.cc")

            for board in self.DEFAULT_BOARDS:
                try:
                    resp = await client.get(
                        f"{self.BASE_URL}/bbs/{board}/index.html",
                    )
                    resp.raise_for_status()
                    articles = self._parse_articles(resp.text, board)
                    all_items.extend(articles)
                except httpx.HTTPError:
                    continue

        # Sort by score (pushes), return top N
        all_items.sort(key=lambda x: x.score, reverse=True)
        return all_items[:count]
