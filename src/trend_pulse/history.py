"""Trend history storage using SQLite."""

from __future__ import annotations

import json
import os
from pathlib import Path

import aiosqlite

from .sources.base import TrendItem


class TrendDB:
    """Async SQLite storage for trend snapshots."""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = os.environ.get(
                "TREND_PULSE_DB",
                str(Path.home() / ".trend-pulse" / "history.db"),
            )
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        """Create database and tables if needed."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT (datetime('now')),
                source TEXT NOT NULL,
                keyword TEXT NOT NULL,
                score REAL NOT NULL,
                traffic_raw TEXT DEFAULT '',
                url TEXT DEFAULT '',
                category TEXT DEFAULT '',
                metadata_json TEXT DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_keyword ON snapshots(keyword);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON snapshots(timestamp);
            CREATE INDEX IF NOT EXISTS idx_source_keyword ON snapshots(source, keyword);
        """)
        await self._db.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def save_snapshot(self, items: list[TrendItem]) -> int:
        """Save a batch of TrendItems as a snapshot. Returns count saved."""
        rows = [
            (item.source, item.keyword, item.score, item.traffic,
             item.url, item.category, json.dumps(item.metadata, ensure_ascii=False))
            for item in items
        ]
        await self._db.executemany(
            "INSERT INTO snapshots (source, keyword, score, traffic_raw, url, category, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        await self._db.commit()
        return len(rows)

    async def get_history(
        self, keyword: str, days: int = 30, source: str = ""
    ) -> list[dict]:
        """Get historical snapshots for a keyword."""
        # Escape LIKE wildcards in user input to prevent injection
        safe_keyword = keyword.replace("%", "\\%").replace("_", "\\_")
        query = """
            SELECT timestamp, source, keyword, score, traffic_raw, url, category, metadata_json
            FROM snapshots
            WHERE keyword LIKE ? ESCAPE '\\'
            AND timestamp >= datetime('now', ?)
        """
        params: list = [f"%{safe_keyword}%", f"-{days} days"]
        if source:
            query += " AND source = ?"
            params.append(source)
        query += " ORDER BY timestamp DESC"

        cursor = await self._db.execute(query, params)
        rows = await cursor.fetchall()
        return [
            {
                "timestamp": row["timestamp"],
                "source": row["source"],
                "keyword": row["keyword"],
                "score": row["score"],
                "traffic": row["traffic_raw"],
                "url": row["url"],
                "category": row["category"],
                "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            }
            for row in rows
        ]

    async def get_latest_scores(
        self, keywords: list[str], source: str = ""
    ) -> dict[str, dict]:
        """Get the most recent score for each (keyword, source) pair.

        Returns dict keyed by "keyword::source" with {score, timestamp, source}.
        Uses a single batch query instead of per-keyword queries.
        """
        if not keywords:
            return {}
        # Deduplicate keywords for the query
        unique_kws = list(set(keywords))
        placeholders = ",".join("?" * len(unique_kws))
        query = f"""
            SELECT keyword, source, score, timestamp
            FROM snapshots
            WHERE keyword IN ({placeholders})
        """
        params: list = list(unique_kws)
        if source:
            query += " AND source = ?"
            params.append(source)
        query += " ORDER BY timestamp DESC"

        cursor = await self._db.execute(query, params)
        rows = await cursor.fetchall()

        # Keep only the most recent per (keyword, source) pair
        results: dict[str, dict] = {}
        for row in rows:
            key = f"{row['keyword']}::{row['source']}"
            if key not in results:
                results[key] = {
                    "score": row["score"],
                    "timestamp": row["timestamp"],
                    "source": row["source"],
                }
        return results

    async def cleanup(self, retention_days: int = 90) -> int:
        """Delete snapshots older than retention_days. Returns count deleted."""
        cursor = await self._db.execute(
            "DELETE FROM snapshots WHERE timestamp < datetime('now', ?)",
            (f"-{retention_days} days",),
        )
        await self._db.commit()
        return cursor.rowcount

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, *args):
        await self.close()
