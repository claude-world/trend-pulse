# Custom Sources

Custom sources are regular `TrendSource` subclasses. Implement `fetch_trending()` and return a `list[TrendItem]`.

## Interface

```python
from trend_pulse.sources.base import TrendItem, TrendSource


class MySource(TrendSource):
    name = "my_source"
    description = "My custom trend source"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        ...
```

- `name`: stable source id used in JSON output and source selection.
- `fetch_trending(geo, count)`: fetch up to `count` items. Ignore `geo` if your source is global.
- Return `list[TrendItem]`.

## Return Format

The runtime type is `TrendItem`. The minimum useful fields are:

| Concept | `TrendItem` field | Notes |
|--------|--------------------|-------|
| title | `keyword` | Human-readable trend title or keyword |
| url | `url` | Canonical link for the item |
| source | `source` | Usually `self.name` |
| score | `score` | Normalized `0-100` for cross-source ranking |

Optional fields such as `traffic`, `category`, `published`, and `metadata` can be filled when available.

## Minimal Example

```python
from trend_pulse.sources.base import TrendItem, TrendSource


class MySource(TrendSource):
    name = "my_source"
    description = "Example source"

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
```

## Use With `TrendAggregator`

```python
from trend_pulse.aggregator import TrendAggregator

agg = TrendAggregator(sources=[MySource])
result = await agg.trending(count=10)
```

For a complete RSS-based implementation, see [`examples/custom_rss_source.py`](../examples/custom_rss_source.py).
