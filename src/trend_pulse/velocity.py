"""Trend velocity and direction calculation."""

from __future__ import annotations

from datetime import datetime, timezone

from .sources.base import TrendItem
from .history import TrendDB

_VELOCITY_THRESHOLD = 10.0  # score-per-hour threshold for rising/declining


async def enrich_with_velocity(
    items: list[TrendItem],
    db: TrendDB,
) -> list[TrendItem]:
    """Enrich TrendItems with direction and velocity from historical data.

    Modifies items in-place and returns them.

    Algorithm:
    - Look up previous score for each (keyword, source) pair
    - velocity = (current_score - previous_score) / hours_elapsed
    - direction:
        - velocity > threshold  -> "rising"
        - velocity < -threshold -> "declining"
        - otherwise             -> "stable"
        - no previous data      -> "new"
    """
    keywords = [item.keyword for item in items]
    latest = await db.get_latest_scores(keywords)

    now = datetime.now(timezone.utc)

    for item in items:
        key = f"{item.keyword}::{item.source}"
        prev = latest.get(key)

        if prev is None:
            item.direction = "new"
            item.velocity = 0.0
            item.previous_score = 0.0
            continue

        item.previous_score = prev["score"]

        # Parse previous timestamp (SQLite stores naive UTC strings like "2026-03-12 05:32:56")
        try:
            # Normalize "Z" suffix for Python <3.11 compat (fromisoformat doesn't accept "Z" until 3.11)
            raw_ts = prev["timestamp"].replace("Z", "+00:00")
            dt = datetime.fromisoformat(raw_ts)
            prev_time = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            # Unparseable timestamp — treat as no reliable history
            item.direction = "new"
            item.velocity = 0.0
            continue

        hours_elapsed = max((now - prev_time).total_seconds() / 3600, 0.01)

        item.velocity = round((item.score - prev["score"]) / hours_elapsed, 2)

        if item.velocity > _VELOCITY_THRESHOLD:
            item.direction = "rising"
        elif item.velocity < -_VELOCITY_THRESHOLD:
            item.direction = "declining"
        else:
            item.direction = "stable"

    return items
