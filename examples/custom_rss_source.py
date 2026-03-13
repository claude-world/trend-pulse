"""Example custom RSS source for trend-pulse.

Run with the built-in Hacker News RSS feed:
    uv run python examples/custom_rss_source.py

Run against any RSS or Atom feed:
    uv run python examples/custom_rss_source.py https://hnrss.org/frontpage
"""

from __future__ import annotations

import asyncio
import sys
import xml.etree.ElementTree as ET

import httpx

from trend_pulse.aggregator import TrendAggregator
from trend_pulse.sources.base import TrendItem, TrendSource


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class CustomRSSSource(TrendSource):
    """Generic RSS/Atom source that maps feed entries to TrendItem objects."""

    name = "custom_rss"
    description = "Generic RSS/Atom feed source"
    rate_limit = "depends on the feed"

    feed_url: str = ""
    default_category: str = "news"

    def __init__(
        self,
        feed_url: str | None = None,
        *,
        name: str | None = None,
        category: str | None = None,
    ) -> None:
        if feed_url is not None:
            self.feed_url = feed_url
        if name is not None:
            self.name = name
        if category is not None:
            self.default_category = category
        if not self.feed_url:
            raise ValueError("Set feed_url on the class or pass it to __init__().")

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        del geo

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(self.feed_url)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        entries = self._find_entries(root)
        items: list[TrendItem] = []

        for index, entry in enumerate(entries[:count]):
            title = self._entry_text(entry, "title") or "untitled"
            link = self._entry_link(entry)
            published = self._entry_text(entry, "pubDate", "published", "updated")
            category = self._entry_text(entry, "category") or self.default_category

            # Normalize rank to the same 0-100 scale trend-pulse uses elsewhere.
            score = max(100 - index * 4, 10)

            items.append(TrendItem(
                keyword=title.strip(),
                score=score,
                source=self.name,
                url=link,
                category=category,
                published=published,
                metadata={
                    "feed_url": self.feed_url,
                    "rank": index + 1,
                },
            ))

        return items

    def _find_entries(self, root: ET.Element) -> list[ET.Element]:
        channel = next((child for child in root if _local_name(child.tag) == "channel"), None)
        if channel is not None:
            rss_items = [child for child in channel if _local_name(child.tag) == "item"]
            if rss_items:
                return rss_items

        return [elem for elem in root.iter() if _local_name(elem.tag) in {"item", "entry"}]

    def _entry_text(self, entry: ET.Element, *names: str) -> str:
        wanted = set(names)
        for child in entry.iter():
            if _local_name(child.tag) in wanted and child.text:
                text = child.text.strip()
                if text:
                    return text
        return ""

    def _entry_link(self, entry: ET.Element) -> str:
        text_link = self._entry_text(entry, "link")
        if text_link:
            return text_link

        for child in entry.iter():
            if _local_name(child.tag) != "link":
                continue
            href = child.attrib.get("href", "").strip()
            if href:
                return href

        return ""


class HackerNewsRSSSource(CustomRSSSource):
    """Ready-to-use subclass that works with TrendAggregator."""

    name = "hackernews_rss"
    description = "Hacker News front page via RSS"
    feed_url = "https://hnrss.org/frontpage"
    default_category = "tech"


async def main() -> None:
    if len(sys.argv) > 1:
        source = CustomRSSSource(
            sys.argv[1],
            name="custom_rss",
            category="news",
        )
        items = await source.fetch_trending(count=5)
    else:
        agg = TrendAggregator(sources=[HackerNewsRSSSource])
        result = await agg.trending(count=5)
        items = [TrendItem(**item) for item in result["merged_top"]]

    for item in items:
        print(f"[{item.source}] {item.keyword} ({item.score:.0f})")
        if item.url:
            print(f"  {item.url}")


if __name__ == "__main__":
    asyncio.run(main())
