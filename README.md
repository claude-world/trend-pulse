# trend-pulse

Free trending topics aggregator — 7 sources, zero auth, one unified API.

Use as a **Python library**, **CLI tool**, or **MCP server** for Claude Code / AI agents.

## Sources

All sources are free and require **zero authentication**:

| Source | Data | Freshness | What you get |
|--------|------|-----------|-------------|
| **Google Trends** | RSS feed | Real-time | Trending searches by country + related news |
| **Hacker News** | Firebase + Algolia | Real-time | Top stories with points, comments, search |
| **Mastodon** | Public API | Real-time | Trending hashtags + trending links |
| **Bluesky** | AT Protocol | Real-time | Trending topics + post search |
| **Wikipedia** | Pageviews API | Daily | Most viewed pages by language/country |
| **GitHub** | Trending page | Daily | Trending repos with stars, language |
| **PyPI** | pypistats.org | Daily | Package download trends + growth signals |

## Install

```bash
# Core (just httpx, no optional deps)
pip install trend-pulse

# With MCP server support
pip install "trend-pulse[mcp]"

# Everything
pip install "trend-pulse[all]"
```

## Quick Start

### CLI

```bash
# What's trending right now? (all 7 sources, merged ranking)
trend-pulse trending

# Taiwan trends from Google + Hacker News
trend-pulse trending --sources google_trends,hackernews --geo TW

# Search across sources
trend-pulse search "AI agent"

# List available sources
trend-pulse sources
```

### Python

```python
import asyncio
from trend_pulse.aggregator import TrendAggregator

async def main():
    agg = TrendAggregator()

    # All sources, merged ranking
    result = await agg.trending(geo="TW", count=10)
    for item in result["merged_top"]:
        print(f"[{item['source']}] {item['keyword']} ({item.get('traffic', '')})")

    # Search
    result = await agg.search("Claude AI")
    for item in result["merged_top"][:5]:
        print(f"{item['keyword']} - {item['score']:.0f}")

asyncio.run(main())
```

### Single Source

```python
import asyncio
from trend_pulse.sources import HackerNewsSource

async def main():
    hn = HackerNewsSource()
    items = await hn.fetch_trending(count=5)
    for item in items:
        print(f"{item.keyword} ({item.traffic})")

    # HN also supports search
    results = await hn.search("Python")
    for item in results[:3]:
        print(f"  {item.keyword}")

asyncio.run(main())
```

### MCP Server (for Claude Code / AI agents)

Add to your Claude Code MCP config (`.mcp.json`):

```json
{
  "mcpServers": {
    "trend-pulse": {
      "command": "trend-pulse-server",
      "type": "stdio"
    }
  }
}
```

Or with uvx (no install needed):

```json
{
  "mcpServers": {
    "trend-pulse": {
      "command": "uvx",
      "args": ["trend-pulse[mcp]"],
      "type": "stdio"
    }
  }
}
```

The MCP server exposes 3 tools:

| Tool | Description |
|------|-------------|
| `get_trending` | Fetch trending topics (all or selected sources) |
| `search_trends` | Search across sources by keyword |
| `list_sources` | List available sources and their properties |

## CLI Reference

```
trend-pulse trending [--sources SRC] [--geo CODE] [--count N]
trend-pulse search QUERY [--sources SRC] [--geo CODE]
trend-pulse sources
```

**`--sources`**: Comma-separated source names:
`google_trends`, `hackernews`, `mastodon`, `bluesky`, `wikipedia`, `github`, `pypi`

**`--geo`**: ISO country code (e.g., `TW`, `US`, `JP`, `DE`).
- Google Trends: filters by country
- Wikipedia: selects language edition
- GitHub: treated as language filter (e.g., `python`)
- Other sources: ignored (global data)

## Output Format

All commands return JSON with a unified structure:

```json
{
  "timestamp": "2026-03-12T05:04:12Z",
  "geo": "TW",
  "sources_ok": ["google_trends", "hackernews", "bluesky"],
  "sources_error": {"wikipedia": "429 rate limited"},
  "merged_top": [
    {
      "keyword": "Temporal: fixing time in JavaScript",
      "score": 100,
      "source": "hackernews",
      "url": "https://...",
      "traffic": "579 points",
      "category": "tech",
      "metadata": {}
    }
  ],
  "by_source": {}
}
```

Each item has a normalized `score` (0-100) for cross-source comparison.

## Add Your Own Source

```python
from trend_pulse.sources.base import TrendSource, TrendItem

class MySource(TrendSource):
    name = "my_source"
    description = "My custom trend source"
    requires_auth = False

    async def fetch_trending(self, geo="", count=20) -> list[TrendItem]:
        # Fetch data from your source
        return [
            TrendItem(
                keyword="trending topic",
                score=85.0,
                source=self.name,
                url="https://...",
            )
        ]
```

Then register it:

```python
from trend_pulse.aggregator import TrendAggregator
from my_module import MySource

agg = TrendAggregator(sources=[MySource, ...])
```

## Rate Limits

| Source | Limit | Notes |
|--------|-------|-------|
| Google Trends RSS | Unlimited | RSS feed, no rate limit |
| Hacker News | Unlimited | Firebase + Algolia, very generous |
| Mastodon | 300 req / 5 min | Per instance |
| Bluesky | 3000 req / 5 min | Public API |
| Wikipedia | 100 req / s | Very generous |
| GitHub | Reasonable | HTML scrape, don't abuse |
| PyPI Stats | 1 req / day / endpoint | Data updates daily |

## Requirements

- Python 3.10+
- `httpx` (only required dependency)
- Optional: `mcp[cli]` for MCP server
- Optional: `trendspyg`, `pytrends` for enhanced Google Trends

## License

MIT

## Credits

Built by [Claude World](https://claude-world.com) — the Claude Code community for developers.
