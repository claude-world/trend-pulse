# Changelog

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
