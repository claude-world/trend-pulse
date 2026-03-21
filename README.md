# trend-pulse

[![CI](https://github.com/claude-world/trend-pulse/actions/workflows/ci.yml/badge.svg)](https://github.com/claude-world/trend-pulse/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/trend-pulse)](https://pypi.org/project/trend-pulse/)
[![Python](https://img.shields.io/pypi/pyversions/trend-pulse)](https://pypi.org/project/trend-pulse/)
[![License: MIT](https://img.shields.io/github/license/claude-world/trend-pulse)](LICENSE)

Free trending topics aggregator + AI content guides — 20 sources, zero auth, patent-based scoring.

Use as a **Python library**, **CLI tool**, or **MCP server** for Claude Code / AI agents.

**One-line MCP setup (zero install):**

```json
{ "mcpServers": { "trend-pulse": { "command": "uvx", "args": ["--from", "trend-pulse[mcp]", "trend-pulse-server"], "type": "stdio" } } }
```

> Paste into `.mcp.json` and you're done. Requires [uv](https://docs.astral.sh/uv/) (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`).

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

#### Step 1: Install uv (if you don't have it)

```bash
# macOS
brew install uv

# Linux / WSL
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Step 2: Add to `.mcp.json`

Create or edit `.mcp.json` in your project root (or `~/.claude/.mcp.json` for global):

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

That's it. No `pip install`, no venv, no Python version management. uvx downloads and caches the package automatically on first run.

#### Step 3 (optional): Enable browser rendering

The `render_page` tool uses Cloudflare Browser Rendering to fetch JS-heavy pages. If you want this feature, add your Cloudflare credentials:

```json
{
  "mcpServers": {
    "trend-pulse": {
      "command": "uvx",
      "args": ["--from", "trend-pulse[mcp]", "trend-pulse-server"],
      "type": "stdio",
      "env": {
        "CF_ACCOUNT_ID": "your-cloudflare-account-id",
        "CF_API_TOKEN": "your-cloudflare-api-token"
      }
    }
  }
}
```

> Get these from [Cloudflare Dashboard](https://dash.cloudflare.com/) → Workers & Pages → Overview. Skip this step if you don't need it — all other 10 tools work without any credentials.

#### Alternative: pip install

If you prefer a traditional install instead of uvx:

```bash
pip install "trend-pulse[mcp]"
```

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

#### Available tools (11)

**Trend Tools (zero auth):**

| Tool | Description |
|------|-------------|
| `get_trending` | Fetch trending topics (all or selected sources, with optional `--save`) |
| `search_trends` | Search across sources by keyword |
| `list_sources` | List available sources and their properties |
| `get_trend_history` | Query historical trend data for a keyword |
| `take_snapshot` | Fetch + save snapshot to history DB |

**Content Guide Tools (zero auth):**

All content tools return **structured guides** — the LLM does all judgment and creative work.

| Tool | Description |
|------|-------------|
| `get_content_brief` | Writing brief: hook examples, patent strategies, scoring dimensions, CTA examples |
| `get_scoring_guide` | 5-dimension scoring framework + 4 Threads algorithm penalty pre-checks |
| `get_platform_specs` | Platform specs: char limits, Threads creator insights, algo priority, best times |
| `get_review_checklist` | 15-item review checklist (7 critical / 5 warning / 3 info) with severity and fix methods |
| `get_reel_guide` | Reel/Short video guide: scene structure, timing, visual guidance, editing tips |

**Browser Rendering Tool (optional, requires Cloudflare credentials):**

| Tool | Description |
|------|-------------|
| `render_page` | Render JS-heavy pages via Cloudflare Browser Rendering |

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

## Content Guide Tools

MCP tools provide structured guides for creating viral content optimized against Meta's 7 ranking patents. **The LLM does all judgment and creative work** — tools only provide frameworks and criteria.

### Threads Algorithm Penalty Pre-Checks (v0.5.3)

Before scoring, content is checked against 4 **officially penalized** patterns from the [Threads Creator Page](https://creators.instagram.com/threads). Any violation blocks publishing:

| Penalty | What Threads Penalizes | Action |
|---------|----------------------|--------|
| `no_clickbait` | Hook promises something the body doesn't deliver | Align hook with content |
| `no_engagement_bait` | Explicitly asks for likes/reposts/follows | Replace with natural CTA |
| `no_contest_violation` | Contest/giveaway requires engagement to enter | Remove or decouple |
| `original_content` | Cross-posted from IG/FB without original angle | Rewrite with original perspective |

### Patent-Based Scoring (5 Dimensions)

| Dimension | Weight | Based On |
|-----------|--------|----------|
| Hook Power | 25% | EdgeRank Weight + Andromeda |
| Engagement Trigger | 25% | Story-Viewer Tuple + Dear Algo |
| Conversation Durability | 20% | Threads 72hr window |
| Velocity Potential | 15% | Andromeda Real-time |
| Format Score | 15% | Multi-modal Indexing |

Grades: **S** (90+), **A** (80+), **B** (70+), **C** (55+), **D** (<55)

Quality gate: overall >= 70, conversation durability >= 55.

### Review Checklist (15 Items)

| Severity | Count | Examples |
|----------|-------|---------|
| **critical** | 7 | char limit, overall score, conversation durability, 4 algorithm penalties |
| **warning** | 5 | hook effectiveness, CTA presence, media enhancement, tone authenticity, topic tag |
| **info** | 3 | question presence, format readability, reply strategy |

Verdict: **pass** = all critical checks pass, **fail** = any critical check fails.

### Threads Creator Insights (v0.5.0)

Key signals from the [official Threads Creator Page](https://creators.instagram.com/threads):

- **Posting frequency**: 2-5 times per week (higher = more views per post)
- **Replies**: Account for ~50% of Threads views — actively reply to comments
- **Media**: Text + media significantly outperforms text-only
- **Humor**: Officially documented as performing well on Threads
- **Topic tags**: Multi-word tags with emojis increase reach
- **15 content types**: TEXT, IMAGE, VIDEO, CAROUSEL, POLL, GIF, LINK_ATTACHMENT, TEXT_ATTACHMENT, SPOILER_MEDIA, SPOILER_TEXT, GHOST_POST, QUOTE_POST, REPLY_CONTROL, TOPIC_TAG, ALT_TEXT

### Workflow: MCP Guides LLM

```
1. get_content_brief()      → LLM gets writing guide with hook examples & strategies
2. LLM creates content      → Original text based on brief
3. get_scoring_guide()       → LLM runs penalty pre-checks, then self-scores 5 dimensions
4. LLM revises              → Iterate until score >= 70
5. get_review_checklist()    → LLM checks 15 items (7 critical / 5 warning / 3 info)
6. get_platform_specs()      → LLM adapts for each platform
```

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

# Get scoring guide — penalty pre-checks + 5-dimension evaluation framework
guide = get_scoring_guide("en")
print(f"Penalty pre-checks: {len(guide['penalty_precheck']['penalties'])}")
for name, dim in guide["dimensions"].items():
    print(f"{name}: weight={dim['weight']}, {dim['description']}")
print(f"Grades: {list(guide['grade_thresholds'].keys())}")

# Get review checklist — 15 structured quality checks (7 critical)
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
