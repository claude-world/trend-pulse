# trend-pulse

Free trending topics aggregator + viral content generator — 15 sources, zero auth, patent-based scoring.

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
| **Google News** | RSS feed | Real-time | Top news stories by country |
| **Lobste.rs** | JSON API | Real-time | Community-driven tech news |
| **dev.to** | Public API | Daily | Developer community articles |
| **npm** | Downloads API | Daily | JavaScript package download trends |
| **Reddit** | Public JSON | Real-time | Popular posts across all subreddits |
| **CoinGecko** | Public API | Real-time | Trending cryptocurrencies |
| **Docker Hub** | Public API | Daily | Popular container images |
| **Stack Overflow** | Public API | Real-time | Hot questions |

## Install

```bash
# Core (httpx + aiosqlite)
pip install trend-pulse

# With MCP server support
pip install "trend-pulse[mcp]"

# Everything
pip install "trend-pulse[all]"
```

## Quick Start

### CLI

```bash
# What's trending right now? (all 15 sources, merged ranking)
trend-pulse trending

# Taiwan trends from Google + Hacker News
trend-pulse trending --sources google_trends,hackernews --geo TW

# Fetch + save snapshot to history DB
trend-pulse trending --save --count 10

# Take a full snapshot (all sources, auto-saves)
trend-pulse snapshot

# Query historical trends for a keyword
trend-pulse history "Claude" --days 7

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

    # With snapshot saving + velocity enrichment
    result = await agg.trending(count=5, save=True)
    for item in result["merged_top"]:
        print(f"{item['keyword']} — {item['direction']} (velocity: {item['velocity']})")

    # Query history
    history = await agg.history("Claude", days=7)
    for record in history["records"]:
        print(f"  {record['timestamp']}: score={record['score']}")

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

The MCP server exposes 10 tools:

**Trend Tools:**

| Tool | Description |
|------|-------------|
| `get_trending` | Fetch trending topics (all or selected sources, with optional `--save`) |
| `search_trends` | Search across sources by keyword |
| `list_sources` | List available sources and their properties |
| `get_trend_history` | Query historical trend data for a keyword |
| `take_snapshot` | Fetch + save snapshot to history DB |

**Content Tools (v0.3.0):**

| Tool | Description |
|------|-------------|
| `generate_viral_posts` | Generate viral posts scored against Meta's 7 ranking patents |
| `score_viral_post` | Score any text on 5 patent-derived dimensions (0-100 + grade) |
| `generate_content` | Generate complete 3-platform content package (Threads + Instagram + Facebook) |
| `review_content` | Review content against patent scores + platform compliance, with optional auto-fix |
| `generate_reel_script` | Generate Reels/Short video scripts with timing and visual cues |

## CLI Reference

```
trend-pulse trending [--sources SRC] [--geo CODE] [--count N] [--save]
trend-pulse search QUERY [--sources SRC] [--geo CODE]
trend-pulse history KEYWORD [--days N] [--source SRC]
trend-pulse snapshot [--sources SRC] [--geo CODE] [--count N]
trend-pulse sources
```

**`--sources`**: Comma-separated source names:
`google_trends`, `hackernews`, `mastodon`, `bluesky`, `wikipedia`, `github`, `pypi`,
`google_news`, `lobsters`, `devto`, `npm`, `reddit`, `coingecko`, `dockerhub`, `stackoverflow`

**`--geo`**: ISO country code (e.g., `TW`, `US`, `JP`, `DE`).
- Google Trends / Google News: filters by country
- Wikipedia: selects language edition
- GitHub: treated as language filter (e.g., `python`)
- Other sources: ignored (global data)

**`--save`**: Save results to local SQLite DB (`~/.trend-pulse/history.db`) for velocity tracking.

## Velocity & Direction

When history data is available, each trend item includes:

```json
{
  "keyword": "Claude AI",
  "score": 92,
  "direction": "rising",
  "velocity": 15.3,
  "previous_score": 45.0,
  "source": "hackernews"
}
```

| Direction | Meaning |
|-----------|---------|
| `rising` | Velocity > 10 (score increasing rapidly) |
| `stable` | Velocity between -10 and 10 |
| `declining` | Velocity < -10 (score decreasing rapidly) |
| `new` | No previous data in history |

Velocity = (current_score - previous_score) / hours_elapsed

## History Database

Snapshots are stored in SQLite at `~/.trend-pulse/history.db` (override with `TREND_PULSE_DB` env var).

```bash
# Save snapshots over time
trend-pulse trending --save --count 5
# ... wait some time ...
trend-pulse trending --save --count 5

# Query history
trend-pulse history "Claude" --days 7
trend-pulse history "React" --days 30 --source npm
```

## Output Format

All commands return JSON with a unified structure:

```json
{
  "timestamp": "2026-03-12T05:04:12Z",
  "geo": "TW",
  "sources_ok": ["google_trends", "hackernews", "reddit"],
  "sources_error": {"wikipedia": "429 rate limited"},
  "merged_top": [
    {
      "keyword": "Temporal: fixing time in JavaScript",
      "score": 100,
      "source": "hackernews",
      "url": "https://...",
      "traffic": "579 points",
      "category": "tech",
      "direction": "rising",
      "velocity": 12.5,
      "previous_score": 60.0,
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
| Google News | Unlimited | RSS feed |
| Lobste.rs | Unlimited | JSON API |
| dev.to | Unlimited | Public API |
| npm | Unlimited | Public API |
| Reddit | 60 req / min | Requires User-Agent header |
| CoinGecko | 10-30 req / min | Public API |
| Docker Hub | 100 req / 5 min | Public API |
| Stack Overflow | 300 req / day | Without API key |

## Content Generation (v0.3.0)

Generate viral-optimized content scored against Meta's 7 ranking patents (EdgeRank, Andromeda, Dear Algo, Conversation Durability, etc.).

### Python

```python
from trend_pulse.content.generator import generate_posts
from trend_pulse.patents.scorer import score_post
from trend_pulse.content.reviewer import review
from trend_pulse.content.adapter import full_pipeline, generate_reel_script

# Generate scored posts
posts = generate_posts("AI tools", content_type="debate", count=5)
for p in posts:
    print(f"[{p['scores']['grade']}] {p['scores']['overall']}/100 — {p['text'][:60]}...")

# Score any text
result = score_post("Your post text here")
print(f"Score: {result['overall']}/100 ({result['grade']})")
print(f"Dimensions: {result['dimensions']}")

# Review with auto-fix
result = review("Short post", platform="threads", auto_fix=True)
print(f"Verdict: {result['verdict']}, Issues: {result['issue_count']}")

# Full 3-platform content package
packages = full_pipeline("Claude Code", content_type="opinion", count=2)
for pkg in packages["packages"]:
    print(f"Threads: {pkg['platforms']['threads']['chars']} chars")
    print(f"Instagram: {pkg['platforms']['instagram']['post_type']}")

# Reel script
script = generate_reel_script("AI", style="educational", duration=30)
for scene in script["scenes"]:
    print(f"[{scene['time']}] {scene['type']}: {scene['caption']}")
```

### Patent-Based Scoring (5 Dimensions)

| Dimension | Weight | Based On |
|-----------|--------|----------|
| Hook Power | 25% | EdgeRank Weight + Andromeda |
| Engagement Trigger | 25% | Story-Viewer Tuple + Dear Algo |
| Conversation Durability | 20% | Threads 72hr window |
| Velocity Potential | 15% | Andromeda Real-time |
| Format Score | 15% | Multi-modal Indexing |

Grades: **S** (90+), **A** (80+), **B** (70+), **C** (50+), **D** (<50)

### Content Types

`opinion`, `story`, `debate`, `howto`, `list`, `question`, `news`, `meme`

### Platform Limits

| Platform | Char Limit | Content Format |
|----------|-----------|----------------|
| Threads | 500 | Short text + image |
| Instagram | 2200 | Carousel / Single image / Reels |
| Facebook | 63,206 | Long-form + image |

## Requirements

- Python 3.10+
- `httpx` (HTTP client)
- `aiosqlite` (history storage)
- Optional: `mcp[cli]` for MCP server
- Optional: `trendspyg`, `pytrends` for enhanced Google Trends

## License

MIT

## Credits

Built by [Claude World](https://claude-world.com) — the Claude Code community for developers.
