# Changelog

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
