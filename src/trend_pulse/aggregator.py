"""Aggregator: combine trends from multiple sources into a unified ranking."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from .sources.base import TrendSource, TrendItem
from .sources import ALL_SOURCES
from .history import TrendDB
from .velocity import enrich_with_velocity


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
        save: bool = False,
    ) -> dict:
        """Fetch trending from selected sources (default: all).

        Args:
            sources: List of source names to query (default: all).
            geo: Country code for regional trends.
            count: Number of results per source.
            save: If True, save snapshot to history DB and enrich with velocity.
        """
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
                all_items.extend(items)
            except Exception as e:
                errors[name] = str(e)

        # History + velocity enrichment
        if all_items:
            db = TrendDB()
            db_exists = Path(db.db_path).exists()
            if save or db_exists:
                try:
                    async with db:
                        await enrich_with_velocity(all_items, db)
                        if save:
                            await db.save_snapshot(all_items)
                except Exception:
                    if save:
                        raise  # Don't swallow errors when user explicitly asked to save

        # Build by_source after enrichment
        for item in all_items:
            results.setdefault(item.source, [])
            results[item.source].append(item.to_dict())

        # Merged ranking: sort by score
        merged = sorted(all_items, key=lambda x: x.score, reverse=True)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources_ok": list(results.keys()),
            "sources_error": errors,
            "merged_top": [it.to_dict() for it in merged[:20]],
            "by_source": results,
        }

    async def history(
        self,
        keyword: str,
        days: int = 30,
        source: str = "",
    ) -> dict:
        """Query historical trend data for a keyword."""
        async with TrendDB() as db:
            records = await db.get_history(keyword, days=days, source=source)
        return {
            "keyword": keyword,
            "days": days,
            "source_filter": source,
            "count": len(records),
            "records": records,
        }

    async def snapshot(
        self,
        sources: list[str] | None = None,
        geo: str = "",
        count: int = 20,
    ) -> dict:
        """Take a snapshot: fetch trending + save to history DB."""
        return await self.trending(
            sources=sources, geo=geo, count=count, save=True,
        )

    def _select(self, names: list[str] | None) -> dict[str, TrendSource]:
        if not names:
            return self._instances
        return {n: self._instances[n] for n in names if n in self._instances}
