# Changelog

## [2.1.0] - 2026-10-21

### Fixed

- **MCP server failed to start on fresh installs.** 2.0.0 declared `mcp>=1.0` with no upper bound, so `pip install "trend-pulse[mcp]"` and `uvx --from "trend-pulse[mcp]" trend-pulse-server` now resolve mcp 2.x, where `mcp.server.fastmcp` no longer exists, and the server exited with `ImportError: Install mcp`. The server is ported to mcp 2.x (`MCPServer`) and the extra is pinned to `mcp>=2.3,<3`.
- Sources broken by upstream changes since April:
  - `reddit`: official RSS feeds (`/r/popular/.rss`, `/search.rss`); the JSON endpoints return 403 to anonymous clients
  - `producthunt`: official Atom feed instead of a blocked homepage scrape
  - `arxiv`: 5 s budget on the export API, with the official RSS listing as fallback when it is throttled
  - `google_trends`: scores were all 0 after Google changed the `ht:` namespace URI
  - `dockerhub`: most-pulled images first again (Docker Hub flipped its sort direction)
  - `github`: no longer parses the Sponsor button as a `sponsors/<user>` repo
  - `stackoverflow`: downvoted questions score 0 instead of a negative value
  - `x_trending`: crashed with `'coroutine' object is not subscriptable` (twikit 2.x `get_trends` is async); it now also loads on Python 3.15, where twikit's js2py dependency cannot import
  - `pinterest` (Pinterest Trends), `indie_hackers` (ranked homepage feed), `bahamut` (forum hot boards, GNN RSS fallback), `line_today` (realtime most-viewed listing): returned nothing, now return real data
  - `dexscreener`: token names and symbols instead of truncated addresses; scores relative to the most-boosted token
  - `threads`, `linkedin_trending`, `xiaohongshu`: returned junk (HTML entities, nav labels, page titles) from login and block pages; they now return nothing
  - `weibo`: dropped the visitor-token workaround; returns nothing while its bot check is served
- Docker: the `mcp` service ran a stdio server that exited as soon as it started; it now serves streamable HTTP on port 8080.
- Dashboard: every action failed with "attempted relative import with no known parent package" under `streamlit run`; it now uses absolute imports and shows the real version.
- Docs: README and `examples/custom_rss_source.py` used a `merged_top` key that does not exist (`merged`); fixed the notifications and lifecycle examples and the Docker Compose service table.

### Changed

- `anthropic` extra requires `anthropic>=1.17`; the L2 judge uses `claude-haiku-5-5` (was `claude-haiku-4-5-20251001`).
- `trend-pulse-server` gains `--transport {stdio,streamable-http,sse}`, `--host`, and `--port` (stdio stays the default) and reports its version to MCP clients.
- `youtube_trending` uses the official YouTube Data API (`chart=mostPopular`) and needs a free `YOUTUBE_API_KEY`; YouTube retired its Trending page in July 2025.
- Dashboard requires `streamlit>=1.51` and uses `width="stretch"` instead of the deprecated `use_container_width`.
- `social` extra requires `twikit>=2.0`.
- The `google`, `browser`, and `zh` extras are deprecated and empty: no code uses `trendspyg`, `pytrends`, `playwright`, or `beautifulsoup4`. They are no longer part of `all`.
- Lockfile refreshed: mcp 2.3.0, anthropic 1.17.0, Streamlit 1.66, plotly 7.1, pandas 3.0 (2.3 on Python 3.10), FastAPI 0.156, pytest 9.1, ruff 0.17.
- Docker images use `python:3.14-slim`. Compose drops the obsolete `version` key, publishes the MCP port on localhost only, and health-checks the port. Added `.dockerignore` and `.env.example`.
- CI tests Python 3.10 through 3.15 with `uv sync --locked`, and builds and `twine check`s the package. Actions bumped to `checkout@v7`, `setup-python@v7`, `setup-uv@v10.3.0` (it publishes only immutable full-version tags), and `codeql-action@v4`. Dependabot now covers uv, GitHub Actions, and Docker monthly, with minor and patch updates grouped.
- Ruff is pinned to the classic rule set (`E4`, `E7`, `E9`, `F`); ruff 0.16 expanded its defaults from 59 to 413 rules.
- Dev container uses Python 3.14 and `uv sync --all-extras --dev` (the old command installed nothing).
- Tests use the public `MCPServer.list_tools()` instead of private internals; 324 tests (was 291), including an end-to-end MCP protocol test and a mocked Claude judge test.

### Known limitations

- `dcard` (Cloudflare 403), `weibo` (visitor check), `xiaohongshu` (signed requests), `mobile01` (403 for non-browser clients), `threads` and `linkedin_trending` (login walls), and `tiktok_trending` (Creative Center now requires login) return no data. trend-pulse does not try to get around these blocks.
- `x_trending` needs a logged-in twikit session or `X_BEARER_TOKEN`; `youtube_trending` needs `YOUTUBE_API_KEY`.
- LINE Notify was shut down on 2025-03-31, so the `line` notification channel cannot deliver.

## [2.0.0] - 2026-04-13

### Added

**Plugin System (Phase 0)**
- New `plugins/` architecture with `PluginSource` base class and `PluginRegistry` auto-discovery
- 17 new plugin sources: Weibo, YouTube Trending, Threads, X/Twitter, TikTok, LINE Today TW, Mobile01, Bahamut, ETtoday, Yahoo TW, UDN, CoinMarketCap, DexScreener, Pinterest, LinkedIn Trending, Indie Hackers, Xiaohongshu
- Total: **37 trend sources** (20 built-in + 17 plugins)
- Plugin categories: `global`, `tw`, `dev`, `crypto`, `social`, `professional`

**Trend Intelligence Core (Phase 1)**
- `core/vector/simple.py` — pure-Python TF-IDF vector store with similarity search and O(n²) clustering (runs in thread executor)
- `core/intelligence/lifecycle.py` — 4-stage lifecycle prediction (emerging/peak/declining/fading) with velocity/acceleration analysis
- `core/intelligence/clusters.py` — cross-source trend clustering with `TrendCluster` model and `to_dict()` serialization
- 5 new MCP tools: `search_semantic`, `get_trend_clusters`, `get_lifecycle_prediction`, `list_sources_extended`, `get_trend_velocity`

**Agentic Content Factory (Phase 2)**
- `core/agents/workflow.py` — 6-agent LangGraph-style workflow: researcher → strategist → writer → optimizer → compliance checker → distributor
- `core/scoring/hybrid.py` — Hybrid Scoring 2.0:
  - L1: heuristic (patent-based, always on)
  - L2: Claude API judge (optional, requires `ANTHROPIC_API_KEY`, 15s timeout)
  - L3: RAG history (SQLite-based pattern matching)
  - Auto-degrades to pure heuristic without API key
- 8 new MCP tools: `run_content_workflow`, `get_ab_variants`, `get_campaign_calendar`, `score_content_hybrid`, `adapt_content`, `generate_hashtags`, `analyze_viral_factors`, `batch_score_content`
- Platform support expanded to 8: Threads, Instagram, Facebook, X, TikTok, LinkedIn, YouTube Shorts, Xiaohongshu

**Web Dashboard + Notifications (Phase 3)**
- `dashboard/app.py` — Streamlit dashboard with 4 pages: Realtime, Clusters, Campaign, History
- `dashboard/api.py` — FastAPI REST API with 12 endpoints (`/trending`, `/search`, `/sources`, `/history`, `/snapshot`, `/clusters`, `/lifecycle/{keyword}`, `/content/score`, `/health`, etc.)
- `notifications/channels.py` — 5 notification channels: Discord Webhook, Telegram Bot, LINE Notify, Email SMTP, Generic Webhook
- 5 new MCP tools: `get_trend_report`, `compare_trends`, `get_source_status`, `send_notification`, `export_data`
- **Total MCP tools: 29** (was 11)

**Infrastructure**
- `Dockerfile`, `Dockerfile.dashboard`, `docker-compose.yml` — one-command Docker Compose deployment (api + worker + dashboard)
- `[dashboard]` and `[llm]` pip extras added
- `asyncio.gather(return_exceptions=True)` parallelism throughout aggregator, server, and scoring

**Tests**
- **291 tests** (was ~183): added `test_core_intelligence.py`, `test_phase2_3.py`, `test_gap_fill.py`, `test_plugins.py`
- Full coverage: vector store, lifecycle, clustering, hybrid scoring, all 6 workflow agents, all 29 MCP tools, SSRF guard, DB cleanup

### Changed

- `TrendAggregator.trending()` and `search()` now use `asyncio.gather` for true parallel source fetching
- `TrendDB` now requires context manager (`async with`) — all methods raise `RuntimeError` outside it
- `pyproject.toml` description and classifiers updated to reflect v2.0.0 scope

### Fixed

- SSRF vulnerability in `render_page`: added scheme whitelist (http/https only) + private/loopback IP block
- Prompt injection in LLM judge: content isolated via `system` param, not interpolated into template
- YouTube InnerTube: replaced catastrophic-backtracking `re.DOTALL` regex with safe `json.JSONDecoder().raw_decode()` approach
- `dashboard/api.py`: `list_sources()` called twice on `/sources` endpoint — cached in variable
- `lifecycle.py`: collapsed two redundant PEAK branches; removed unreachable dead code
- `weibo.py`: items with `heat=0` now get rank-based score instead of 0.0
- All MCP tools with `count`/`hours`/`days` parameters now clamp input to safe bounds
- `notifications/channels.py`: EmailSMTP uses `charset="utf-8"`; Telegram drops `parse_mode: Markdown` to prevent 400 errors on special chars

### Security

- SSRF guard in `render_page` (scheme whitelist + `ipaddress` library private IP check)
- Prompt injection isolation in hybrid scoring LLM judge (`system` param separation)
- `x_trending.py`: removed hardcoded bearer token fallback — empty string short-circuits guest API call
- `threads.py`: added recursion depth guard (`depth > 25`) in `_walk()` to prevent stack overflow on malformed responses

---

## [0.5.3] - 2026-03-22

### Added

- **Threads algorithm penalty pre-checks** — 4 blocking checks before scoring, based on [official Threads Creator Page](https://creators.instagram.com/threads):
  - `no_clickbait` — hook must deliver on its promise
  - `no_engagement_bait` — no explicit asks for likes/reposts/follows
  - `no_contest_violation` — contests must not tie engagement to entry
  - `original_content` — cross-posted content gets reduced reach
- **Enhanced review checklist** — expanded from 9 to 15 items across 3 severity levels:
  - 7 critical (including 4 new algorithm penalty checks)
  - 5 warning (media_enhancement upgraded from info to warning)
  - 3 info
- Penalty pre-checks integrated into both `get_scoring_guide()` and `get_review_checklist()`
- Full bilingual support (EN + zh-TW) for all new penalty checks

## [0.5.2] - 2026-03-17

### Added

- **PyPI auto-publish** — GitHub Releases now auto-publish to PyPI via Trusted Publisher (no token needed)
- **uvx zero-install** — promoted as recommended install method in README

### Changed

- README: added one-line MCP setup snippet at the top for quick copy-paste
- README: reordered MCP config to show uvx first, pip second
- README: added uv install instructions (`brew install uv` / `curl`)

## [0.5.1] - 2026-03-16

### Fixed

- Replaced all deprecated `datetime.utcnow()` / `utcfromtimestamp()` with timezone-aware alternatives (Python 3.12+ compat)
- Defensive timezone handling in velocity calculation — correctly handles both naive and aware timestamps
- Normalize `Z`-suffix timestamps via `.replace("Z", "+00:00")` for Python 3.10 compat in velocity parsing
- Unparseable timestamps now return `direction="new"` instead of false velocity spike
- MCP `get_trending` tool docstring now lists all 20 sources (was missing arxiv, producthunt, lemmy, dcard, ptt)
- `published` field in Reddit/StackOverflow items now uses `+00:00` offset instead of `Z` suffix (both valid ISO 8601)

### Added

- `py.typed` marker (PEP 561) for downstream type-checking support
- 62 unit tests for all 20 sources with mocked HTTP responses (`test_sources.py`)
- 7 velocity enrichment tests covering rising/declining/stable/new/invalid-timestamp/z-suffix/aware-timestamp paths
- Total test count: 121 → **183**

## [0.5.0] - 2026-03-14

### Added

- **Dcard** — Taiwan's largest social platform trending posts (public API, zero auth)
- **PTT** — Taiwan BBS hot articles from Gossiping, Tech_Job, Stock, HatePolitics, LoL boards
- Total sources expanded from 18 to **20** (10 searchable)
- **Threads Creator Page insights** — integrated official data from https://creators.instagram.com/threads:
  - Posting frequency guidance (2-5x/week)
  - Reply strategy (replies ≈ 50% of Threads views)
  - Media enhancement (text + media outperforms text-only)
  - Humor as officially documented strength
  - Topic tag best practices
  - 15 supported content types (TEXT, IMAGE, VIDEO, CAROUSEL, POLL, GIF, etc.)
  - Non-recommendable content list (clickbait, engagement bait, cross-posts)

### Changed

- Updated all references from "15 sources" to "20 sources" (README, CLI, pyproject.toml)
- Added Dcard, PTT, ArXiv, Product Hunt, Lemmy to README sources table and rate limits

## [0.4.0] - 2026-03-12

### Added

- **Search support for 6 new sources** (2/15 → 8/18 search-enabled)
  - Reddit — `/search.json` with relevance sorting
  - Stack Overflow — `/2.3/search` with intitle matching
  - dev.to — tag-based article search
  - Product Hunt — HTML scraping with JSON-LD parsing (new source)
  - ArXiv — Atom API full-text search for AI/ML/NLP papers (new source)
  - Lemmy — lemmy.world federated search (new source)
- 3 new trending sources: Product Hunt (product), ArXiv (research), Lemmy (community)
- Shared `_parse_*` helpers in Reddit, dev.to, Stack Overflow to eliminate duplication

### Fixed

- ArXiv API URL `http://` → `https://` (was causing redirect errors)
- Product Hunt GraphQL 403 → replaced with HTML scraping approach
- dev.to / ArXiv: `resp.json()`/`resp.text` now read inside `async with` block
- Lemmy: `metadata["url"]` renamed to `"external_url"` to avoid shadowing `TrendItem.url`
- ArXiv: removed manual `quote()` that caused double URL-encoding via httpx params

## [0.3.3] - 2026-03-12

### Added

- CF Browser Rendering fallback + `render_page` MCP tool

## [0.3.2] - 2026-03-12

### Architecture Change

MCP tools now provide **structured guides** instead of generating content directly. The LLM does all judgment and creative work — tools only provide frameworks and criteria.

### Added

- `get_content_brief` — Writing brief with hook examples, patent strategies, scoring dimensions, CTA examples
- `get_scoring_guide` — 5-dimension evaluation framework (weights, criteria, high/low signals, grade thresholds)
- `get_platform_specs` — Platform specs: char limits, format tips, algo priority signals, best posting times
- `get_review_checklist` — Quality gate checklist with severity levels, pass criteria, fix methods
- `get_reel_guide` — Video script guide: scene structure, timing, visual guidance, editing tips (3 styles)
- Bilingual support (en + zh-TW) for all guide tools with auto language detection
- English hook/body/CTA templates and English regex patterns in scorer

### Removed

- `generate_viral_posts` — Replaced by `get_content_brief` (LLM creates content from guide)
- `generate_content` — Replaced by `get_platform_specs` (LLM adapts per platform)
- `score_viral_post` — Renamed to `score_post`

### Security

- LIKE wildcard escaping in history queries
- Input validation for GitHub trending language parameter
- Added `.gemini/`, `AGENTS.md`, `GEMINI.md` to `.gitignore`

## [0.3.0] - 2026-03-11

### Added

- 10 MCP tools (5 data + 5 content)
- Patent-based scoring (7 Meta patents, 5 scoring dimensions)
- Content generation and review pipeline
- Reel script generator (educational / storytelling / listicle)
- 82 tests

## [0.2.0] - 2026-03-10

### Added

- History database (SQLite) with velocity tracking
- Snapshot save/restore
- Direction detection (rising/stable/declining/new)
- `take_snapshot` and `get_trend_history` tools

## [0.1.0] - 2026-03-09

### Added

- Initial release: 15 free trend sources
- TrendAggregator with cross-source merged ranking
- CLI (`trend-pulse trending/search/sources`)
- MCP server (`trend-pulse-server`)
- Python library API
