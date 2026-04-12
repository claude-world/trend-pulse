# Changelog

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
