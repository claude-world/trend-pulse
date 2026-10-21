"""Indie Hackers trending posts (free, no auth).

Indie Hackers is a community for bootstrapped founders and indie makers.
IH has no public RSS feed or API, so this parses the ranked post feed on the
server-rendered homepage.
"""

from __future__ import annotations

import html as html_lib
import re

import httpx

from ... import __version__
from ...plugins.base import PluginSource
from ...sources.base import TrendItem


class IndieHackersSource(PluginSource):
    name = "indie_hackers"
    description = "Indie Hackers - trending posts from the indie maker/founder community"
    requires_auth = False
    rate_limit = "moderate (scraping)"
    category = "dev"
    frequency = "daily"

    HOME_URL = "https://www.indiehackers.com/"
    HEADERS = {
        "User-Agent": f"trend-pulse/{__version__} (github.com/claude-world/trend-pulse)",
        "Accept": "text/html",
    }

    _STORY_RE = re.compile(r'<div class="story homepage-post\b')
    _LINK_RE = re.compile(r'class="story__text-link[^"]*" href="(/post/[^"]+)"')
    _TITLE_RE = re.compile(r'<h3 class="story__title">(.*?)</h3>', re.DOTALL)
    _COUNT_RE = re.compile(
        r'story__count--(likes|comments)".*?<span class="story__count-number">([\d,]+)</span>',
        re.DOTALL,
    )

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(self.HOME_URL, headers=self.HEADERS)
                resp.raise_for_status()
        except Exception:
            return []
        return self._parse_home(resp.text, count)

    def _parse_home(self, html: str, count: int) -> list[TrendItem]:
        """Parse the homepage's ranked "organic" feed (skips featured, newest, and ads)."""
        start = html.find('<div class="organic"')
        if start == -1:
            return []
        end = html.find('<div class="featured"', start)
        section = html[start:end if end != -1 else len(html)]

        items: list[TrendItem] = []
        seen: set[str] = set()
        blocks = self._STORY_RE.split(section)[1:]
        for block in blocks:
            link = self._LINK_RE.search(block)
            title_match = self._TITLE_RE.search(block)
            if not link or not title_match:
                continue
            path = link.group(1)
            title = html_lib.unescape(re.sub(r"<[^>]+>", "", title_match.group(1))).strip()
            if not title or path in seen:
                continue
            seen.add(path)

            counts = {kind: int(num.replace(",", "")) for kind, num in self._COUNT_RE.findall(block)}
            votes = counts.get("likes", 0)
            comments = counts.get("comments", 0)
            rank = len(items) + 1
            items.append(TrendItem(
                keyword=title,
                score=min(votes / 2, 100),  # 200 upvotes = 100
                source=self.name,
                url=f"https://www.indiehackers.com{path}",
                traffic=f"{votes} upvotes, {comments} comments",
                category="startup",
                metadata={"votes": votes, "comments": comments, "rank": rank},
            ))
            if len(items) >= count:
                break

        return items


def register() -> IndieHackersSource:
    return IndieHackersSource()
