"""Aggregator: combine trends from multiple sources into a unified ranking."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from .sources.base import TrendSource, TrendItem
from .sources import ALL_SOURCES
from .history import TrendDB
from .velocity import enrich_with_velocity

logger = logging.getLogger(__name__)


class TrendAggregator:
    """Fetch and merge trending data from multiple free sources.

    Automatically loads plugin sources from trend_pulse.plugins.sources.*
    in addition to the built-in 20 sources. Plugins are loaded gracefully:
    missing optional dependencies are silently skipped.
    """

    def __init__(
        self,
        sources: list[type[TrendSource]] | None = None,
        include_plugins: bool = True,
    ):
        self.source_classes = sources or ALL_SOURCES
        self._instances: dict[str, TrendSource] = {}
        for cls in self.source_classes:
            self._instances[cls.name] = cls()

        # Load plugin sources (v2.0) — skips on missing optional deps
        if include_plugins and sources is None:
            try:
                from .plugins.registry import PluginRegistry
                plugin_instances = PluginRegistry.load_all(skip_errors=True)
                # Plugins don't override built-in sources with same name
                for name, inst in plugin_instances.items():
                    if name not in self._instances:
                        self._instances[name] = inst
                logger.debug("Loaded %d plugin sources", len(plugin_instances))
            except Exception as exc:
                logger.debug("Plugin loading skipped: %s", exc)

    @property
    def available_sources(self) -> list[str]:
        return list(self._instances.keys())

    def list_sources(self) -> list[dict]:
        """List all sources (built-in + plugins) with their metadata."""
        return [type(inst).info() for inst in self._instances.values()]

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

        names = list(selected.keys())
        coros = [src.fetch_trending(geo=geo, count=count) for src in selected.values()]

        results: dict[str, list[dict]] = {}
        errors: dict[str, str] = {}
        all_items: list[TrendItem] = []

        # Report any requested source names that don't exist
        if sources:
            for n in sources:
                if n not in self._instances:
                    errors[n] = "Unknown source name"

        raw_results = await asyncio.gather(*coros, return_exceptions=True)
        for name, result in zip(names, raw_results):
            if isinstance(result, Exception):
                errors[name] = str(result)
            else:
                all_items.extend(result)

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
            "merged": [it.to_dict() for it in merged[:count]],
            "sources": results,
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

        names_list = list(tasks.keys())
        raw_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for name, result in zip(names_list, raw_results):
            if isinstance(result, Exception):
                errors[name] = str(result)
            else:
                results[name] = [it.to_dict() for it in result]
                all_items.extend(result)

        merged = sorted(all_items, key=lambda x: x.score, reverse=True)

        return {
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources_ok": list(results.keys()),
            "sources_error": errors,
            "merged": [it.to_dict() for it in merged[:20]],
            "sources": results,
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
        selected = {n: self._instances[n] for n in names if n in self._instances}
        return selected
