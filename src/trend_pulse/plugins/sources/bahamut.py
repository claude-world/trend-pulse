"""巴哈姆特 (Bahamut) trending topics (free, no auth).

Bahamut is Taiwan's largest anime/game/entertainment community.
Uses the public 哈啦區 hot-board ranking (boards ordered by popularity), with
the official GNN news RSS feed as a fallback.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET

import httpx

from ...plugins.base import PluginSource
from ...sources.base import TrendItem


def _clean(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


class BahamutSource(PluginSource):
    name = "bahamut"
    description = "巴哈姆特 - Taiwan's largest anime/gaming community trending topics"
    requires_auth = False
    rate_limit = "moderate"
    category = "tw"
    frequency = "daily"

    # 哈啦區 home lists the hottest boards in popularity order
    FORUM_URL = "https://forum.gamer.com.tw/"
    GNN_RSS_URL = "https://gnn.gamer.com.tw/rss.xml"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9",
    }

    _BOARD_RE = re.compile(
        r'<a href="https://forum\.gamer\.com\.tw/B\.php\?bsn=(\d+)"[^>]*>\s*<h3[^>]*>(.*?)</h3>',
        re.DOTALL,
    )
    _POPULARITY_RE = re.compile(r'<data value="(\d+)"')
    _THREAD_RE = re.compile(
        r'<a href="(https://forum\.gamer\.com\.tw/C\.php\?bsn=\d+&amp;snA=\d+)"[^>]*>\s*<h5[^>]*>(.*?)</h5>',
        re.DOTALL,
    )

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            try:
                resp = await client.get(self.FORUM_URL, headers=self.HEADERS)
                if resp.status_code == 200:
                    items = self._parse_boards(resp.text, count)
                    if items:
                        return items
            except Exception:
                pass

            # Fallback: official GNN news feed
            resp = await client.get(self.GNN_RSS_URL, headers=self.HEADERS)
            resp.raise_for_status()
            return self._parse_gnn_rss(resp.content, count)

    def _parse_boards(self, page: str, count: int) -> list[TrendItem]:
        boards = list(self._BOARD_RE.finditer(page))
        parsed: list[tuple[str, str, int, str, str]] = []
        for i, m in enumerate(boards):
            end = boards[i + 1].start() if i + 1 < len(boards) else len(page)
            card = page[m.end():end]
            board_name = _clean(m.group(2))
            if not board_name:
                continue
            m_pop = self._POPULARITY_RE.search(card)
            m_thread = self._THREAD_RE.search(card)
            parsed.append((
                m.group(1),
                board_name,
                int(m_pop.group(1)) if m_pop else 0,
                _clean(m_thread.group(2)) if m_thread else "",
                html.unescape(m_thread.group(1)) if m_thread else "",
            ))
            if len(parsed) >= count:
                break

        top = max((p[2] for p in parsed), default=0)
        items: list[TrendItem] = []
        for rank, (bsn, board_name, popularity, thread_title, thread_url) in enumerate(parsed, 1):
            items.append(TrendItem(
                keyword=board_name,
                # Popularity relative to the hottest board; rank-based if the index is missing
                score=round(popularity / top * 100, 1) if top else max(0, 100 - rank),
                source=self.name,
                url=f"https://forum.gamer.com.tw/B.php?bsn={bsn}",
                traffic=f"{popularity:,} 人氣" if popularity else f"rank #{rank}",
                category="entertainment",
                metadata={
                    "rank": rank,
                    "popularity": popularity,
                    "hot_thread": thread_title,
                    "hot_thread_url": thread_url,
                },
            ))
        return items

    def _parse_gnn_rss(self, content: bytes, count: int) -> list[TrendItem]:
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return []

        items: list[TrendItem] = []
        for entry in root.findall(".//item"):
            title = (entry.findtext("title") or "").strip()
            if not title:
                continue
            rank = len(items) + 1
            items.append(TrendItem(
                keyword=title,
                score=max(0, 100 - rank),
                source=self.name,
                url=(entry.findtext("link") or "").strip(),
                traffic=f"rank #{rank}",
                category="entertainment",
                published=entry.findtext("pubDate") or "",
                metadata={"rank": rank, "feed": "gnn"},
            ))
            if len(items) >= count:
                break
        return items


def register() -> BahamutSource:
    return BahamutSource()
