"""PluginSource — extended base class for v2.0 plugin sources.

Fully backwards-compatible with TrendSource: all existing sources keep working.
Plugins add category, frequency, and plugin_version metadata without breaking
the existing info() contract.
"""

from __future__ import annotations

from ..sources.base import TrendSource


class PluginSource(TrendSource):
    """Extended base class for plugin-style trend sources.

    Adds extra metadata fields (category, frequency, plugin_version) to the
    standard TrendSource while remaining 100% compatible with TrendAggregator.
    All subclasses still must implement fetch_trending().
    """

    # Additional metadata (all optional with sensible defaults)
    category: str = "global"       # "global", "tw", "dev", "crypto", "social"
    frequency: str = "realtime"    # "realtime", "daily"
    plugin_version: str = "1.0"
    difficulty: str = "low"        # "low", "medium", "high" — scraping difficulty

    @classmethod
    def info(cls) -> dict:
        base = super().info()       # Preserve original keys: name, description, requires_auth, rate_limit
        base["category"] = cls.category
        base["frequency"] = cls.frequency
        base["plugin_version"] = cls.plugin_version
        return base
