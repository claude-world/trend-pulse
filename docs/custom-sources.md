# Custom Sources & Plugin System

trend-pulse supports two ways to add custom trend sources:

1. **PluginSource** — the recommended approach for new sources (v2.0+). Auto-discovered by `PluginRegistry`.
2. **TrendSource** — the base interface, usable for ad-hoc sources passed directly to `TrendAggregator`.

---

## Plugin Sources (recommended)

Drop a file in `src/trend_pulse/plugins/sources/` and implement `register()`. The `PluginRegistry` scans this directory automatically — no registration step needed.

### Interface

```python
from trend_pulse.plugins.base import PluginSource
from trend_pulse.sources.base import TrendItem


class MyPluginSource(PluginSource):
    name = "my_plugin"                  # stable ID used in CLI / JSON output
    description = "My custom source"

    # Optional metadata (displayed by list_sources_extended)
    category = "global"   # global | tw | dev | crypto | social | professional
    frequency = "daily"   # realtime | daily
    plugin_version = "1.0"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        return [
            TrendItem(
                keyword="Trending topic",
                score=85.0,
                source=self.name,
                url="https://example.com/topic",
            )
        ][:count]


def register() -> MyPluginSource:
    return MyPluginSource()
```

### File naming

Use `snake_case` matching the source `name`:

```
plugins/sources/my_plugin.py   →   name = "my_plugin"
```

### Auto-discovery

`PluginRegistry.load_all()` is called by `TrendAggregator.__init__()` and merges all plugins into the aggregator's source pool. No further setup required.

---

## TrendSource (ad-hoc / testing)

For sources you don't want to install as plugins, pass them directly to `TrendAggregator`:

```python
from trend_pulse.aggregator import TrendAggregator
from trend_pulse.sources.base import TrendSource, TrendItem


class MySource(TrendSource):
    name = "my_source"
    description = "Example source"
    requires_auth = False

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        del geo
        return [
            TrendItem(
                keyword="Example topic",
                score=90.0,
                source=self.name,
                url="https://example.com/topic",
            )
        ][:count]


agg = TrendAggregator(sources=[MySource])
result = await agg.trending(count=10)
```

---

## TrendItem fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `keyword` | `str` | Yes | Human-readable trend title |
| `score` | `float` | Yes | Normalized 0–100 for cross-source ranking |
| `source` | `str` | Yes | Usually `self.name` |
| `url` | `str` | No | Canonical link |
| `traffic` | `str` | No | Human-readable traffic/volume (e.g. "1.2M views") |
| `category` | `str` | No | Content category |
| `published` | `str` | No | ISO 8601 timestamp |
| `metadata` | `dict` | No | Source-specific extra data |

Score should be normalized to 0–100 so the aggregator can rank across sources. Example normalizations:
- HN points: `min(points / 5, 100)`
- YouTube views: `min(views / 1_000_000, 100)` (100M views = 100)
- Rank-based: `max(0, 100 - rank)`

---

## Search support (optional)

Override `search()` to make your source searchable via `trend-pulse search` and the `search_trends` MCP tool:

```python
async def search(self, query: str, geo: str = "") -> list[TrendItem]:
    # Return items matching the query
    ...
```

---

## Complete RSS example

See [`examples/custom_rss_source.py`](../examples/custom_rss_source.py) for a working RSS-based plugin implementation.
