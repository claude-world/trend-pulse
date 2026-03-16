# trend-pulse

[![CI](https://github.com/claude-world/trend-pulse/actions/workflows/ci.yml/badge.svg)](https://github.com/claude-world/trend-pulse/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/trend-pulse)](https://pypi.org/project/trend-pulse/)
[![Python](https://img.shields.io/pypi/pyversions/trend-pulse)](https://pypi.org/project/trend-pulse/)
[![License: MIT](https://img.shields.io/github/license/claude-world/trend-pulse)](LICENSE)

Free trending topics aggregator + AI content guides — 20 sources, zero auth, patent-based scoring.

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
| **ArXiv** | RSS/API | Daily | Trending research papers |
| **Product Hunt** | Public API | Daily | Product launches and upvotes |
| **Lemmy** | Public API | Real-time | Federated community posts (lemmy.world) |
| **Dcard** | Public API | Real-time | Taiwan social platform trending posts |
| **PTT** | Web scrape | Real-time | Taiwan BBS hot articles (Gossiping, Tech_Job, etc.) |

## Install

### Zero-install with uvx (recommended)

[uvx](https://docs.astral.sh/uv/guides/tools/) runs Python packages directly — no install, no venv, no setup:

```bash
# Run the CLI instantly
uvx trend-pulse trending

# Run the MCP server
uvx --from "trend-pulse[mcp]" trend-pulse-server
```

> `uvx` is the Python equivalent of `npx`. It comes with [uv](https://docs.astral.sh/uv/) — install uv with `curl -LsSf https://astral.sh/uv/install.sh | sh`

### pip install

```bash
# Core (httpx + aiosqlite)
pip install trend-pulse

# With MCP server support
pip install "trend-pulse[mcp]"

# Everything (MCP + enhanced Google Trends)
pip install "trend-pulse[all]"
```

## Quick Start

### CLI

```bash
# What's trending right now? (all 20 sources, merged ranking)
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

**uvx (zero-install, recommended):**

```json
{
  "mcpServers": {
    "trend-pulse": {
      "command": "uvx",
      "args": ["--from", "trend-pulse[mcp]", "trend-pulse-server"],
      "type": "stdio"
    }
  }
}
```

No `pip install` needed — uvx downloads and caches the package automatically on first run.

**If already installed via pip:**

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

The MCP server exposes 11 tools:

**Trend Tools:**

| Tool | Description |
|------|-------------|
| `get_trending` | Fetch trending topics (all or selected sources, with optional `--save`) |
| `search_trends` | Search across sources by keyword |
| `list_sources` | List available sources and their properties |
| `get_trend_history` | Query historical trend data for a keyword |
| `take_snapshot` | Fetch + save snapshot to history DB |

**Content Guide Tools (v0.3.2):**

All content tools return **structured guides** — the LLM does all judgment and creative work.

| Tool | Description |
|------|-------------|
| `get_content_brief` | Writing brief: hook examples, patent strategies, scoring dimensions, CTA examples |
| `get_scoring_guide` | 5-dimension scoring framework: evaluation criteria, high/low signals, grade thresholds |
| `get_platform_specs` | Platform specs: char limits, format tips, algo priority, best times |
| `get_review_checklist` | Review checklist: platform compliance, quality gates, checklist items with severity |
| `get_reel_guide` | Reel/Short video guide: scene structure, timing, visual guidance, editing tips |

**Browser Rendering Tool (v0.3.3):**

| Tool | Description |
|------|-------------|
| `render_page` | Render JS-heavy pages via Cloudflare Browser Rendering (requires `CF_ACCOUNT_ID` + `CF_API_TOKEN`) |

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
`google_news`, `lobsters`, `devto`, `npm`, `reddit`, `coingecko`, `dockerhub`, `stackoverflow`,
`arxiv`, `producthunt`, `lemmy`, `dcard`, `ptt`

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

## Custom Sources

Custom sources are simple `TrendSource` subclasses that return `list[TrendItem]`.

- Interface docs: [docs/custom-sources.md](docs/custom-sources.md)
- Working RSS example: [examples/custom_rss_source.py](examples/custom_rss_source.py)

```python
from trend_pulse.aggregator import TrendAggregator
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

agg = TrendAggregator(sources=[MySource])
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
| ArXiv | Unlimited | RSS/API |
| Product Hunt | Reasonable | Public API |
| Lemmy | Unlimited | Public API (lemmy.world) |
| Dcard | Reasonable | Public API |
| PTT | Reasonable | Web scrape, don't abuse |

## Content Guide Tools (v0.3.2)

MCP tools provide structured guides for creating viral content optimized against Meta's 7 ranking patents. **The LLM does all judgment and creative work** — tools only provide frameworks and criteria.

### Python

```python
from trend_pulse.content.briefing import (
    get_content_brief,
    get_scoring_guide,
    get_review_checklist,
    get_reel_guide,
)
from trend_pulse.content.adapter import get_platform_specs

# Get writing brief — hook examples, patent strategies, scoring dimensions
brief = get_content_brief("AI tools", "debate", "threads", lang="en")
print(f"Topic: {brief['topic']}, Char limit: {brief['char_limit']}")
print(f"Hook examples: {len(brief['hook_examples'])}")
print(f"Patent strategies: {len(brief['patent_strategies'])}")

# Get scoring guide — 5-dimension evaluation framework
guide = get_scoring_guide("en")
for name, dim in guide["dimensions"].items():
    print(f"{name}: weight={dim['weight']}, {dim['description']}")
print(f"Grades: {list(guide['grade_thresholds'].keys())}")

# Get review checklist — structured quality checks
checklist = get_review_checklist("threads", "en")
for item in checklist["checklist"]:
    print(f"[{item['severity']}] {item['check']}")
print(f"Quality gate: overall >= {checklist['quality_gate']['min_overall']}")

# Get platform specs — char limits, algo priority, best times
specs = get_platform_specs("", "en")  # all platforms
for name, spec in specs.items():
    print(f"{name}: {spec['max_chars']} chars, best at {spec['best_times']}")

# Get reel guide — scene structure for video scripts
guide = get_reel_guide("educational", 30, "en")
for scene in guide["scene_structure"]:
    print(f"[{scene['type']}] {scene['duration_seconds']}s — {scene['purpose']}")
```

### Workflow: MCP Guides LLM

```
1. get_content_brief()      → LLM gets writing guide with hook examples & strategies
2. LLM creates content      → Original text based on brief
3. get_scoring_guide()       → LLM self-scores on 5 dimensions
4. LLM revises              → Iterate until score >= 70
5. get_review_checklist()    → LLM checks against quality gate
6. get_platform_specs()      → LLM adapts for each platform
```

### Patent-Based Scoring (5 Dimensions)

| Dimension | Weight | Based On |
|-----------|--------|----------|
| Hook Power | 25% | EdgeRank Weight + Andromeda |
| Engagement Trigger | 25% | Story-Viewer Tuple + Dear Algo |
| Conversation Durability | 20% | Threads 72hr window |
| Velocity Potential | 15% | Andromeda Real-time |
| Format Score | 15% | Multi-modal Indexing |

Grades: **S** (90+), **A** (80+), **B** (70+), **C** (55+), **D** (<55)

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
