"""Base class for all trend sources."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class TrendItem:
    """Standardized trending item across all sources."""

    keyword: str
    score: float  # Normalized 0-100
    source: str  # e.g. "google_trends", "hackernews"
    url: str = ""
    traffic: str = ""  # e.g. "200K+", "500 points"
    category: str = ""  # e.g. "tech", "news", "finance"
    published: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v or k in ("keyword", "score", "source")}


class TrendSource(ABC):
    """Base class for trend sources."""

    name: str = "base"
    description: str = ""
    requires_auth: bool = False
    rate_limit: str = "unlimited"

    @abstractmethod
    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        """Fetch currently trending topics."""
        ...

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        """Search trends by keyword. Override if the source supports search."""
        return []

    @classmethod
    def info(cls) -> dict:
        return {
            "name": cls.name,
            "description": cls.description,
            "requires_auth": cls.requires_auth,
            "rate_limit": cls.rate_limit,
        }
