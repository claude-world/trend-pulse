"""Aggregator: combine trends from multiple sources into a unified ranking."""

from __future__ import annotations

import asyncio
from datetime import datetime

from .sources.base import TrendSource, TrendItem
from .sources import ALL_SOURCES


class TrendAggregator:
    """Fetch and merge trending data from multiple free sources."""

    def __init__(self, sources: list[type[TrendSource]] | None = None):
        self.source_classes = sources or ALL_SOURCES
        self._instances: dict[str, TrendSource] = {}
        for cls in self.source_classes:
            self._instances[cls.name] = cls()

    @property
    def available_sources(self) -> list[str]:
        return list(self._instances.keys())

    def list_sources(self) -> list[dict]:
        return [cls.info() for cls in self.source_classes]

    async def trending(
        self,
        sources: list[str] | None = None,
        geo: str = "",
        count: int = 20,
    ) -> dict:
        """Fetch trending from selected sources (default: all)."""
        selected = self._select(sources)

        tasks = {
            name: asyncio.create_task(src.fetch_trending(geo=geo, count=count))
            for name, src in selected.items()
        }

        results: dict[str, list[dict]] = {}
        errors: dict[str, str] = {}
        all_items: list[TrendItem] = []

        for name, task in tasks.items():
            try:
                items = await task
                results[name] = [it.to_dict() for it in items]
                all_items.extend(items)
            except Exception as e:
                errors[name] = str(e)

        # Merged ranking: normalize scores, sort
        merged = sorted(all_items, key=lambda x: x.score, reverse=True)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "geo": geo,
            "sources_ok": list(results.keys()),
            "sources_error": errors,
            "merged_top": [it.to_dict() for it in merged[:count]],
            "by_source": results,
        }

    async def search(
        self,
        query: str,
        sources: list[str] | None = None,
        geo: str = "",
    ) -> dict:
        """Search across sources that support search."""
        selected = self._select(sources)

        tasks = {}
        for name, src in selected.items():
            # Only sources that override search()
            if type(src).search is not TrendSource.search:
                tasks[name] = asyncio.create_task(src.search(query=query, geo=geo))

        results: dict[str, list[dict]] = {}
        errors: dict[str, str] = {}
        all_items: list[TrendItem] = []

        for name, task in tasks.items():
            try:
                items = await task
                results[name] = [it.to_dict() for it in items]
                all_items.extend(items)
            except Exception as e:
                errors[name] = str(e)

        merged = sorted(all_items, key=lambda x: x.score, reverse=True)

        return {
            "query": query,
            "timestamp": datetime.utcnow().isoformat(),
            "sources_ok": list(results.keys()),
            "sources_error": errors,
            "merged_top": [it.to_dict() for it in merged[:20]],
            "by_source": results,
        }

    def _select(self, names: list[str] | None) -> dict[str, TrendSource]:
        if not names:
            return self._instances
        return {n: self._instances[n] for n in names if n in self._instances}
