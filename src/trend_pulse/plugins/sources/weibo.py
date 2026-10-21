"""Weibo (微博) real-time hot search list (free, no auth).

Scrapes the public hot search page: https://s.weibo.com/top/summary
Weibo now routes anonymous clients through its "Sina Visitor System" bot check
(passport.weibo.com); when that gate is served, this source returns no items.
"""

from __future__ import annotations

import html
import logging
import re

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem

logger = logging.getLogger(__name__)


class WeiboTrendingSource(PluginSource):
    name = "weibo"
    description = "微博熱搜 - China's real-time trending topics on Weibo"
    requires_auth = False
    rate_limit = "30 req/min"
    category = "tw"
    frequency = "realtime"

    URL = "https://s.weibo.com/top/summary?cate=realtimehot"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://weibo.com/",
    }

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(self.URL, headers=self.HEADERS)
            resp.raise_for_status()

        if "passport.weibo" in resp.url.host or "Sina Visitor System" in resp.text[:2000]:
            logger.debug("weibo: hot search is behind the Sina Visitor System check; skipping")
            return []

        page = resp.text
        items: list[TrendItem] = []

        # Extract rows — find all <tr> blocks with td-02 (topic) and td-03 (heat)
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', page, re.DOTALL)
        for row in rows:
            if 'td-02' not in row:
                continue

            # Extract topic title and URL
            m_topic = re.search(
                r'td-02[^>]*>.*?<a[^>]+href="([^"]*)"[^>]*>([^<]+)</a>',
                row, re.DOTALL,
            )
            if not m_topic:
                continue

            topic_url_path, title = m_topic.group(1), m_topic.group(2).strip()
            title = html.unescape(title).strip()
            if not title:
                continue

            # Extract heat score
            m_score = re.search(r'td-03[^>]*>.*?<span[^>]*>([0-9,]+)</span>', row, re.DOTALL)
            heat = int(m_score.group(1).replace(",", "")) if m_score else 0

            url = f"https://s.weibo.com{topic_url_path}" if topic_url_path.startswith("/") else topic_url_path

            rank = len(items) + 1
            items.append(TrendItem(
                keyword=title,
                # Use heat if available; fall back to rank-based score for promoted/no-heat slots
                score=min(heat / 1_000_000, 100) if heat else max(0, 100 - rank),
                source=self.name,
                url=url,
                traffic=str(heat) if heat else f"rank #{rank}",
                category="general",
                metadata={"heat": heat, "rank": rank, "platform": "weibo"},
            ))

            if len(items) >= count:
                break

        return items


def register() -> WeiboTrendingSource:
    return WeiboTrendingSource()
