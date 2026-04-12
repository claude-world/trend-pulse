"""MCP Server for trend-pulse."""

from __future__ import annotations

import json
from datetime import datetime, timezone

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise ImportError("Install mcp: pip install 'trend-pulse[mcp]'")

from .aggregator import TrendAggregator

mcp = FastMCP("trend-pulse")

_agg = TrendAggregator()

# Notification channel singletons — constructed once, credentials read from env at startup
def _make_notification_channels() -> dict:
    try:
        from .notifications import DiscordWebhook, TelegramBot, GenericWebhook, LineNotify, EmailSMTP
        return {
            "discord": DiscordWebhook(),
            "telegram": TelegramBot(),
            "webhook": GenericWebhook(),
            "line": LineNotify(),
            "email": EmailSMTP(),
        }
    except Exception:
        return {}

_notification_channels: dict = _make_notification_channels()


def _parse_sources(raw: str) -> list[str] | None:
    """Parse comma-separated source names, stripping whitespace."""
    parsed = [s.strip() for s in raw.split(",") if s.strip()]
    return parsed or None


@mcp.tool()
async def get_trending(
    sources: str = "",
    geo: str = "",
    count: int = 20,
    save: bool = False,
) -> str:
    """Get trending topics from free sources.

    Args:
        sources: Comma-separated source names (default: all).
                 Built-in (20): google_trends, hackernews, mastodon, bluesky, wikipedia,
                 github, pypi, google_news, lobsters, devto, npm, reddit,
                 coingecko, dockerhub, stackoverflow, arxiv, producthunt, lemmy, dcard, ptt
                 Plugins (17+): weibo, youtube_trending, threads, line_today, mobile01,
                 bahamut, ettoday, yahoo_tw, udn, coinmarketcap, dexscreener,
                 indie_hackers, x_trending, tiktok_trending, xiaohongshu,
                 pinterest, linkedin_trending
        geo: Country code for regional trends (e.g. TW, US, JP)
        count: Number of results per source (default: 20)
        save: Save snapshot to history DB for velocity tracking (default: false)

    Returns:
        JSON with merged ranking + per-source results (includes direction/velocity if history exists)
    """
    count = max(1, min(count, 200))
    src_list = _parse_sources(sources)
    result = await _agg.trending(sources=src_list, geo=geo, count=count, save=save)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def search_trends(
    query: str,
    sources: str = "",
    geo: str = "",
) -> str:
    """Search for a keyword across trend sources.

    Args:
        query: Search keyword
        sources: Comma-separated source names (default: all searchable)
        geo: Country code

    Returns:
        JSON with search results across sources
    """
    src_list = _parse_sources(sources)
    result = await _agg.search(query=query, sources=src_list, geo=geo)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def list_sources() -> str:
    """List all available trend sources and their properties."""
    return json.dumps(_agg.list_sources(), indent=2, ensure_ascii=False)


@mcp.tool()
async def get_trend_history(
    keyword: str,
    days: int = 30,
    source: str = "",
) -> str:
    """Query historical trend data for a keyword.

    Args:
        keyword: The keyword to look up (partial match supported)
        days: Number of days to look back (default: 30)
        source: Filter by source name (default: all sources)

    Returns:
        JSON with historical records including timestamps and scores
    """
    result = await _agg.history(keyword=keyword, days=days, source=source)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def take_snapshot(
    sources: str = "",
    geo: str = "",
    count: int = 20,
) -> str:
    """Take a trend snapshot: fetch from all sources and save to history DB.

    Args:
        sources: Comma-separated source names (default: all)
        geo: Country code for regional trends
        count: Number of results per source (default: 20)

    Returns:
        JSON with trending results (snapshot saved to DB for velocity tracking)
    """
    count = max(1, min(count, 200))
    src_list = _parse_sources(sources)
    result = await _agg.snapshot(sources=src_list, geo=geo, count=count)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════
# Content Guide Tools — structured data for LLM judgment
# ═══════════════════════════════════════════════════════


@mcp.tool()
async def get_content_brief(
    topic: str,
    content_type: str = "debate",
    platform: str = "threads",
    lang: str = "auto",
) -> str:
    """Get a structured writing brief for creating viral content.

    Returns hook examples, patent strategies, scoring dimensions, platform specs,
    and content type guidance. Use this data to craft original posts — the LLM
    creates the content, this tool provides the optimization framework.

    Args:
        topic: Subject to create content about (e.g. "AI tools", "Claude Code")
        content_type: Post style — opinion, story, debate, howto, list, question, news, meme
        platform: Target platform — threads (500 chars), instagram (2200), facebook (63206)
        lang: Language — "auto" (detect from topic), "en", "zh-TW"

    Returns:
        JSON with hook examples, CTA examples, patent strategies, scoring dimensions,
        platform specs, content type guidance, char limit, and quality gate thresholds
    """
    from .content.briefing import get_content_brief as _brief

    result = _brief(topic, content_type, platform, lang)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_scoring_guide(
    lang: str = "auto",
    topic: str = "",
) -> str:
    """Get the 5-dimension scoring framework for evaluating posts.

    Returns evaluation criteria, high/low signal examples, and grade thresholds
    for each patent-derived dimension. The LLM uses this guide to score posts
    itself — no regex heuristics.

    Dimensions (weighted):
    - Hook Power 25% (EdgeRank Weight + Andromeda)
    - Engagement Trigger 25% (Story-Viewer Tuple + Dear Algo)
    - Conversation Durability 20% (Threads 72hr window)
    - Velocity Potential 15% (Andromeda Real-time)
    - Format Score 15% (Multi-modal Indexing)

    Args:
        lang: Language for criteria text — "auto", "en", "zh-TW"
        topic: Optional topic hint for auto language detection

    Returns:
        JSON with 5 dimensions (weight, criteria, signals), grade thresholds, and instructions
    """
    from .content.briefing import get_scoring_guide as _guide

    result = _guide(lang, topic)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_platform_specs(
    platform: str = "",
    lang: str = "zh-TW",
) -> str:
    """Get platform specifications for content adaptation.

    Returns character limits, content strengths, algorithm priorities,
    best posting times, and format guidelines for each platform.
    Use this to adapt content for specific platforms.

    Args:
        platform: Platform name — threads, instagram, facebook (empty = all platforms)
        lang: Language for descriptions — "en" or "zh-TW" (default: "zh-TW")

    Returns:
        JSON with platform specs (char limits, strengths, format tips, algo priority, best times)
    """
    from .content.adapter import get_platform_specs as _specs

    result = _specs(platform, lang)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_review_checklist(
    platform: str = "threads",
    lang: str = "auto",
    topic: str = "",
) -> str:
    """Get a structured review checklist for evaluating content quality.

    Returns platform limits, quality thresholds, and detailed checklist items.
    The LLM reviews the post against this checklist itself — the tool only
    provides criteria, not judgment.

    Checklist covers:
    - Character limit compliance
    - Overall score quality gate (>= 70)
    - Conversation durability gate (>= 55)
    - Hook effectiveness
    - CTA presence
    - Question/engagement triggers
    - Format/readability

    Args:
        platform: Target platform — threads (500 chars), instagram (2200), facebook (63206)
        lang: Language for checklist text — "auto", "en", "zh-TW"
        topic: Optional topic hint for auto language detection

    Returns:
        JSON with platform limits, quality gate thresholds, checklist items, and verdict rules
    """
    from .content.briefing import get_review_checklist as _checklist

    result = _checklist(platform, lang, topic)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_reel_guide(
    style: str = "educational",
    duration: int = 30,
    lang: str = "auto",
    topic: str = "",
) -> str:
    """Get a structured guide for creating Reels/Short video scripts.

    Returns scene structure, timing allocations, visual guidance, and editing tips.
    The LLM fills in original captions, voiceover, and visual directions.

    Styles: educational (problem→solution), storytelling (conflict→resolution),
    listicle (numbered points)

    Args:
        style: Script style — educational, storytelling, listicle
        duration: Target duration in seconds (default: 30)
        lang: Language for guide text — "auto", "en", "zh-TW"
        topic: Optional topic hint for auto language detection

    Returns:
        JSON with scene structure, timing, music suggestion, editing tips, and instructions
    """
    from .content.briefing import get_reel_guide as _guide

    result = _guide(style, duration, lang, topic)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════
# Browser Rendering Tool — optional, requires CF credentials
# ═══════════════════════════════════════════════════════


@mcp.tool()
async def render_page(
    url: str,
    format: str = "markdown",
) -> str:
    """Render a JS-heavy page using Cloudflare Browser Rendering.

    Requires CF_ACCOUNT_ID and CF_API_TOKEN environment variables.
    Returns rendered page content in the requested format.

    Args:
        url: The page URL to render.
        format: Output format — "markdown" (clean text), "content" (full HTML),
                or "json" (AI structured extraction, returns raw page data).

    Returns:
        JSON with url, format, and rendered content (or error message).
    """
    import ipaddress
    import urllib.parse as _urlparse

    # SSRF guard: only allow http/https to non-private hosts
    try:
        _parsed = _urlparse.urlparse(url)
        if _parsed.scheme not in ("http", "https"):
            return json.dumps({"error": f"Unsupported URL scheme: {_parsed.scheme!r}. Only http/https allowed."}, indent=2)
        _host = _parsed.hostname or ""
        try:
            _ip = ipaddress.ip_address(_host)
            if _ip.is_private or _ip.is_loopback or _ip.is_link_local or _ip.is_multicast:
                return json.dumps({"error": f"Blocked: private/loopback host {_host!r}"}, indent=2)
        except ValueError:
            pass  # hostname (not a bare IP) — OK
    except Exception:
        return json.dumps({"error": "Invalid URL"}, indent=2)

    from .sources.browser_renderer import is_available, render_markdown, render_content, extract_json

    if not is_available():
        return json.dumps({
            "error": "Not configured. Set CF_ACCOUNT_ID and CF_API_TOKEN environment variables.",
            "url": url,
        }, indent=2)

    try:
        if format == "content":
            content = await render_content(url)
        elif format == "json":
            content = await extract_json(url, "Extract the main structured content from this page.")
            return json.dumps({
                "url": url,
                "format": format,
                "content": content,
            }, indent=2, ensure_ascii=False)
        else:  # default: markdown
            content = await render_markdown(url)

        return json.dumps({
            "url": url,
            "format": format,
            "content": content,
        }, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({
            "error": str(exc),
            "url": url,
            "format": format,
        }, indent=2)


# ═══════════════════════════════════════════════════════
# Intelligence Tools — Phase 1 additions
# ═══════════════════════════════════════════════════════


@mcp.tool()
async def search_semantic(
    query: str,
    sources: str = "",
    geo: str = "",
    count: int = 20,
    k: int = 10,
) -> str:
    """Semantic similarity search across trend sources.

    Fetches trends from the specified sources, indexes them with TF-IDF, and
    returns the k most semantically similar results to the query. Useful for
    finding thematically related trends even when keywords don't match exactly.

    Args:
        query: Natural-language search query (e.g. "machine learning tools").
        sources: Comma-separated source names (default: all).
        geo: Country code for regional trends (e.g. TW, US).
        count: Number of items to fetch per source before similarity ranking.
        k: Number of results to return (default: 10).

    Returns:
        JSON with ranked list of semantically similar TrendItems.
    """
    from .core.vector.simple import SimpleVectorStore

    count = max(1, min(count, 200))
    src_list = _parse_sources(sources)
    raw = await _agg.trending(sources=src_list, geo=geo, count=count)
    items = []
    for src_result in raw.get("sources", {}).values():
        for it in src_result:
            from .sources.base import TrendItem
            items.append(TrendItem(
                keyword=it.get("keyword", ""),
                source=it.get("source", ""),
                score=it.get("score", 0),
                category=it.get("category"),
                url=it.get("url"),
            ))

    store = SimpleVectorStore()
    await store.upsert(items)
    results = await store.search_similar(query, k=k)
    return json.dumps({
        "query": query,
        "results": [
            {**r.item.to_dict(), "similarity": round(r.similarity, 4)}
            for r in results
        ],
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_trend_clusters(
    sources: str = "",
    geo: str = "",
    count: int = 20,
    threshold: float = 0.25,
) -> str:
    """Cluster trends from multiple sources into semantic topic groups.

    Fetches trends, embeds them with TF-IDF, and groups similar items into
    TrendClusters. Cross-source clusters (same topic appearing in 2+ sources)
    are ranked highest — these are the most validated viral topics.

    Args:
        sources: Comma-separated source names (default: all).
        geo: Country code for regional trends.
        count: Items to fetch per source before clustering.
        threshold: Cosine similarity threshold (0-1). Lower = larger clusters.
                   Default 0.25 is a good balance for short trend keywords.

    Returns:
        JSON with clusters sorted by (cross_source desc, score desc).
    """
    from .core.intelligence.clusters import cluster_trends
    from .sources.base import TrendItem

    count = max(1, min(count, 200))
    src_list = _parse_sources(sources)
    raw = await _agg.trending(sources=src_list, geo=geo, count=count)
    items = []
    for src_result in raw.get("sources", {}).values():
        for it in src_result:
            items.append(TrendItem(
                keyword=it.get("keyword", ""),
                source=it.get("source", ""),
                score=it.get("score", 0),
                category=it.get("category"),
                url=it.get("url"),
            ))

    clusters = await cluster_trends(items, threshold=threshold)
    return json.dumps({
        "cluster_count": len(clusters),
        "item_count": len(items),
        "threshold": threshold,
        "clusters": [c.to_dict() for c in clusters],
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_lifecycle_prediction(
    keyword: str,
    days: int = 30,
    source: str = "",
) -> str:
    """Predict the lifecycle stage of a trend keyword.

    Queries the local history DB for the keyword's score trajectory, then
    predicts whether it's emerging, at peak, declining, or fading.

    Args:
        keyword: The trend keyword to analyse.
        days: How many days of history to include (default: 30).
        source: Filter history by source name (default: all sources).

    Returns:
        JSON with stage, current_score, velocity, history_count, and emoji.
    """
    from .core.intelligence.lifecycle import predict_lifecycle, lifecycle_emoji

    hist_result = await _agg.history(keyword=keyword, days=days, source=source)
    # history() returns records newest-first (ORDER BY timestamp DESC); reverse to oldest-first
    records = list(reversed(hist_result.get("records", [])))

    current_score = records[-1]["score"] if records else 0.0
    stage = predict_lifecycle(current_score, records)

    return json.dumps({
        "keyword": keyword,
        "stage": stage.value,
        "emoji": lifecycle_emoji(stage),
        "current_score": current_score,
        "history_count": len(records),
        "days_queried": days,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def list_sources_extended() -> str:
    """List all available trend sources with extended plugin metadata.

    Returns all built-in sources plus plugin sources with additional fields:
    category, frequency, plugin_version, difficulty, and dependencies.

    Returns:
        JSON array of source info objects with full metadata.
    """
    sources = _agg.list_sources()
    # Enrich plugin sources with extra metadata where available
    enriched = []
    for src in sources:
        name = src.get("name", "")
        inst = _agg._instances.get(name)
        if inst is not None:
            extra = {
                "category": getattr(type(inst), "category", None),
                "frequency": getattr(type(inst), "frequency", None),
                "plugin_version": getattr(type(inst), "plugin_version", None),
                "difficulty": getattr(type(inst), "difficulty", None),
                "dependencies": getattr(type(inst), "dependencies", None),
            }
            src = {k: v for k, v in {**src, **extra}.items() if v is not None}
        enriched.append(src)
    return json.dumps({
        "total": len(enriched),
        "sources": enriched,
    }, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════
# Agentic Content Factory Tools — Phase 2 additions
# ═══════════════════════════════════════════════════════


@mcp.tool()
async def run_content_workflow(
    topic: str,
    platforms: str = "threads",
    brand_voice: str = "casual",
    sources: str = "",
    geo: str = "",
    count: int = 20,
) -> str:
    """Run the full 6-agent content workflow to auto-generate viral posts.

    Executes a multi-agent pipeline: researcher → strategist → copywriter →
    optimizer → compliance checker → distributor. Returns platform-ready content
    for all specified platforms.

    Agents:
    1. Researcher: selects top trends relevant to the topic
    2. Strategist: generates 3 content angles / hooks
    3. Copywriter: drafts platform-specific posts
    4. Optimizer: creates A/B variants and scores them
    5. Compliance: flags spammy language (reduces score)
    6. Distributor: picks best variant per platform

    Args:
        topic: Content topic / keyword (e.g. "AI agents", "Claude Code").
        platforms: Comma-separated platform names
                   (threads, x, instagram, linkedin, tiktok, youtube, xiaohongshu, facebook).
        brand_voice: Tone — "casual", "professional", "provocative", "educational".
        sources: Comma-separated trend source names to fetch context from (default: all).
        geo: Country code for trend context (e.g. TW, US).
        count: Items to fetch per source for trend context (default: 20).

    Returns:
        JSON with final_content (platform→text), strategy, scored_drafts, and any errors.
    """
    from .core.agents.workflow import run_content_workflow as _workflow
    from .sources.base import TrendItem

    # Optionally enrich with live trends
    count = max(1, min(count, 200))
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]
    src_list = _parse_sources(sources)
    items = []
    try:
        raw = await _agg.trending(sources=src_list, geo=geo, count=count)
        for src_result in raw.get("sources", {}).values():
            for it in src_result:
                items.append(TrendItem(
                    keyword=it.get("keyword", ""),
                    source=it.get("source", ""),
                    score=it.get("score", 0),
                    category=it.get("category"),
                ))
    except Exception:
        pass  # Continue without live trends

    state = await _workflow(
        trends=items,
        platforms=platform_list,
        brand_voice=brand_voice,
        topic=topic,
    )

    return json.dumps({
        "topic": topic,
        "platforms": platform_list,
        "brand_voice": brand_voice,
        "final_content": state.get("final_content", {}),
        "strategy": state.get("strategy", {}),
        "scored_drafts": [
            {k: v for k, v in d.items()}
            for d in state.get("scored_drafts", [])
        ],
        "completed_agents": state.get("completed_agents", []),
        "errors": state.get("errors", []),
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_ab_variants(
    content: str,
    platform: str = "threads",
    count: int = 3,
) -> str:
    """Generate A/B content variants for testing different approaches.

    Creates multiple variants of the input content by applying different
    mutation strategies: emoji boost, question hook, urgency framing, etc.
    Each variant is scored with the heuristic engine.

    Args:
        content: Original post text to create variants from.
        platform: Target platform for char-limit compliance (default: threads).
        count: Number of variants to generate (1-5, default: 3).

    Returns:
        JSON with original + variant posts, scores, and recommended pick.
    """
    from .core.scoring.hybrid import score_content

    count = max(1, min(count, 5))

    _CHAR_LIMITS = {
        "threads": 500, "x": 280, "instagram": 2200, "linkedin": 3000,
        "tiktok": 2200, "facebook": 63206, "youtube": 5000, "xiaohongshu": 1000,
    }
    limit = _CHAR_LIMITS.get(platform, 500)

    mutations = [
        lambda t: ("🔥 " + t)[:limit],
        lambda t: (t + "\n\nWhat do you think? 👇")[:limit],
        lambda t: ("🚨 Breaking: " + t)[:limit],
        lambda t: t.replace(".", ".\n")[:limit],
        lambda t: (t + "\n\nAgree or disagree?")[:limit],
    ]

    original_score = await score_content(content, platform)
    variants = [{
        "variant": 0,
        "label": "original",
        "content": content,
        "score": round(original_score.total, 1),
        "grade": original_score.grade,
    }]

    for i, mutate in enumerate(mutations[:count], start=1):
        v_content = mutate(content)
        v_score = await score_content(v_content, platform)
        variants.append({
            "variant": i,
            "label": f"variant_{i}",
            "content": v_content,
            "score": round(v_score.total, 1),
            "grade": v_score.grade,
        })

    best = max(variants, key=lambda v: v["score"])
    return json.dumps({
        "platform": platform,
        "char_limit": limit,
        "variants": variants,
        "recommended": best["variant"],
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def score_content_hybrid(
    content: str,
    platform: str = "threads",
) -> str:
    """Score content using the Hybrid Scoring 2.0 engine.

    Applies L1 heuristic analysis (always available) + L2 LLM judge
    (requires ANTHROPIC_API_KEY) + L3 RAG history bonus if history exists.

    Scoring dimensions (weights):
    - Hook Power 25%: Opening line strength, emoji, question words
    - Engagement Trigger 25%: CTA presence, debate language
    - Conversation Durability 20%: Length, depth, substance
    - Velocity Potential 15%: Trending keywords alignment
    - Format Score 15%: Char limit compliance, readability

    Args:
        content: Post text to evaluate.
        platform: Target platform for format scoring
                  (threads, x, instagram, linkedin, tiktok, youtube, xiaohongshu, facebook).

    Returns:
        JSON with total score (0-100), grade, dimension breakdown, mode, and signals.
    """
    from .core.scoring.hybrid import score_content

    result = await score_content(content, platform)
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


@mcp.tool()
async def get_campaign_calendar(
    topics: str,
    days: int = 7,
    platforms: str = "threads",
    brand_voice: str = "casual",
) -> str:
    """Generate a content calendar for multiple topics over N days.

    Plans one post per topic per day, distributing across platforms and
    varying content angles to avoid repetition. Uses the strategy layer
    to assign angles and the platform adapter for format guidance.

    Args:
        topics: Comma-separated topic list (e.g. "AI tools,Python,Claude Code").
        days: Number of days to plan (1-30, default: 7).
        platforms: Comma-separated target platforms (default: threads).
        brand_voice: Tone — "casual", "professional", "provocative", "educational".

    Returns:
        JSON calendar with day-by-day posting plan.
    """
    topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    if not topic_list:
        return json.dumps({"error": "At least one topic is required. Pass topics='AI,Python,...'"}, indent=2)
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()] or ["threads"]
    days = max(1, min(days, 30))

    _ANGLE_TEMPLATES = [
        "Hot take: {topic} is changing everything",
        "3 things nobody tells you about {topic}",
        "Why {topic} matters more than you think",
        "The dark side of {topic} everyone ignores",
        "How {topic} will affect you in 2026",
        "What experts get wrong about {topic}",
        "The future of {topic}: what to expect",
    ]

    calendar = []
    for day in range(1, days + 1):
        topic = topic_list[(day - 1) % len(topic_list)] if topic_list else "trending"
        platform = platform_list[(day - 1) % len(platform_list)]
        angle_tmpl = _ANGLE_TEMPLATES[(day - 1) % len(_ANGLE_TEMPLATES)]
        angle = angle_tmpl.format(topic=topic)

        calendar.append({
            "day": day,
            "topic": topic,
            "platform": platform,
            "brand_voice": brand_voice,
            "suggested_angle": angle,
            "posting_time": "21:00",  # Default prime time
            "content_type": "text" if platform in ("threads", "x", "linkedin") else "video",
        })

    return json.dumps({
        "days": days,
        "topics": topic_list,
        "platforms": platform_list,
        "calendar": calendar,
    }, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════
# Reporting & Notification Tools — Phase 3 additions
# ═══════════════════════════════════════════════════════


@mcp.tool()
async def get_trend_report(
    period: int = 7,
    sources: str = "",
    geo: str = "",
    count: int = 20,
) -> str:
    """Generate an automated trend intelligence report.

    Fetches trends, clusters them, predicts lifecycle stages, and assembles a
    structured report showing what's emerging, peaking, and fading across sources.

    Args:
        period: Number of days of history to include for lifecycle context (default: 7).
        sources: Comma-separated source names (default: all).
        geo: Country code filter (e.g. TW, US).
        count: Items per source to include (default: 20).

    Returns:
        JSON report with executive summary, top trends, cross-source clusters,
        and lifecycle breakdown (emerging/peak/declining/fading counts).
    """
    from collections import defaultdict
    from .core.intelligence.clusters import cluster_trends
    from .core.intelligence.lifecycle import predict_lifecycle, lifecycle_emoji
    from .sources.base import TrendItem

    count = max(1, min(count, 200))
    src_list = _parse_sources(sources)
    raw = await _agg.trending(sources=src_list, geo=geo, count=count)

    items: list[TrendItem] = []
    for src_result in raw.get("sources", {}).values():
        for it in src_result:
            items.append(TrendItem(
                keyword=it.get("keyword", ""),
                source=it.get("source", ""),
                score=it.get("score", 0),
                category=it.get("category"),
            ))

    clusters = await cluster_trends(items, threshold=0.25)

    # Lifecycle for each cluster topic — parallel history lookups
    import asyncio as _asyncio
    from .core.intelligence.lifecycle import LifecycleStage

    lifecycle_counts: dict[str, int] = defaultdict(int)
    top_sorted = sorted(items, key=lambda i: i.score, reverse=True)[:20]
    hist_results = await _asyncio.gather(
        *[_agg.history(keyword=item.keyword, days=period) for item in top_sorted],
        return_exceptions=True,
    )

    top_items = []
    for item, hist_or_exc in zip(top_sorted, hist_results):
        try:
            if isinstance(hist_or_exc, Exception):
                raise hist_or_exc
            records_asc = list(reversed(hist_or_exc.get("records", [])))
            stage = predict_lifecycle(item.score, records_asc)
        except Exception:
            stage = LifecycleStage.EMERGING
        lifecycle_counts[stage.value] += 1
        top_items.append({
            **item.to_dict(),
            "lifecycle": stage.value,
            "lifecycle_emoji": lifecycle_emoji(stage),
        })

    cross_source_clusters = [c.to_dict() for c in clusters if c.cross_source][:10]

    return json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": period,
        "total_items": len(items),
        "total_clusters": len(clusters),
        "cross_source_clusters": len(cross_source_clusters),
        "lifecycle_summary": lifecycle_counts,
        "top_trends": top_items[:10],
        "cross_source_highlights": cross_source_clusters[:5],
        "sources_queried": list(raw.get("sources", {}).keys()),
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def compare_trends(
    keyword_a: str,
    keyword_b: str,
    days: int = 30,
) -> str:
    """Compare two trend keywords side-by-side.

    Looks up history for both keywords and computes momentum, average score,
    peak score, and lifecycle stage for each. Returns a head-to-head comparison.

    Args:
        keyword_a: First keyword to compare.
        keyword_b: Second keyword to compare.
        days: Days of history to query (default: 30).

    Returns:
        JSON with side-by-side comparison of both keywords.
    """
    from .core.intelligence.lifecycle import predict_lifecycle, lifecycle_emoji

    async def _analyze(kw: str) -> dict:
        hist = await _agg.history(keyword=kw, days=days)
        # history() returns newest-first; reverse to oldest-first for lifecycle/velocity
        records = list(reversed(hist.get("records", [])))
        scores = [r["score"] for r in records] if records else []
        current = scores[-1] if scores else 0.0
        peak = max(scores, default=0.0)
        avg = sum(scores) / len(scores) if scores else 0.0
        stage = predict_lifecycle(current, records)
        velocity = (scores[-1] - scores[0]) / len(scores) if len(scores) >= 2 else 0.0
        return {
            "keyword": kw,
            "current_score": round(current, 1),
            "peak_score": round(peak, 1),
            "avg_score": round(avg, 1),
            "velocity": round(velocity, 2),
            "lifecycle": stage.value,
            "lifecycle_emoji": lifecycle_emoji(stage),
            "history_count": len(records),
        }

    import asyncio as _asyncio_ct
    a, b = await _asyncio_ct.gather(_analyze(keyword_a), _analyze(keyword_b))
    winner_score = keyword_a if a["current_score"] >= b["current_score"] else keyword_b
    winner_momentum = keyword_a if a["velocity"] >= b["velocity"] else keyword_b

    return json.dumps({
        "days_compared": days,
        "keyword_a": a,
        "keyword_b": b,
        "winner_by_score": winner_score,
        "winner_by_momentum": winner_momentum,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def export_data(
    format: str = "json",
    sources: str = "",
    geo: str = "",
    count: int = 50,
) -> str:
    """Export trend data in JSON or CSV format.

    Fetches live trends and formats them for export. Useful for feeding into
    spreadsheets, BI tools, or external analysis pipelines.

    Args:
        format: Output format — "json" (structured) or "csv" (comma-separated).
        sources: Comma-separated source names (default: all).
        geo: Country code filter.
        count: Items per source (default: 50).

    Returns:
        JSON or CSV string with trend data.
    """
    import csv
    import io

    count = max(1, min(count, 200))
    src_list = _parse_sources(sources)
    raw = await _agg.trending(sources=src_list, geo=geo, count=count)

    rows = []
    for src_result in raw.get("sources", {}).values():
        for it in src_result:
            rows.append({
                "keyword": it.get("keyword", ""),
                "source": it.get("source", ""),
                "score": it.get("score", 0),
                "direction": it.get("direction", ""),
                "velocity": it.get("velocity", 0),
                "category": it.get("category", ""),
                "url": it.get("url", ""),
                "published": it.get("published", ""),
            })

    rows.sort(key=lambda r: r["score"], reverse=True)

    if format == "csv":
        buf = io.StringIO()
        if rows:
            writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return json.dumps({
            "format": "csv",
            "row_count": len(rows),
            "csv": buf.getvalue(),
        }, indent=2, ensure_ascii=False)

    return json.dumps({
        "format": "json",
        "row_count": len(rows),
        "data": rows,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def send_notification(
    channel: str,
    title: str,
    message: str,
) -> str:
    """Send a trend alert notification to a configured channel.

    Requires the channel's credentials to be set as environment variables.
    Channels: discord, telegram, webhook, line, email.

    Environment variables:
    - discord:  DISCORD_WEBHOOK_URL
    - telegram: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
    - webhook:  GENERIC_WEBHOOK_URL
    - line:     LINE_NOTIFY_TOKEN
    - email:    SMTP_HOST + SMTP_USER + SMTP_PASS + SMTP_FROM + SMTP_TO

    Args:
        channel: Channel name — "discord", "telegram", "webhook", "line", or "email".
        title: Notification title.
        message: Notification body text.

    Returns:
        JSON with success status and channel used.
    """
    from .notifications.base import NotificationPayload

    ch = _notification_channels.get(channel.lower())
    if not ch:
        # Use static list — never reveal which channels are actually configured
        _KNOWN = "discord, telegram, webhook, line, email"
        return json.dumps({
            "success": False,
            "error": f"Unknown channel: {channel!r}. Supported: {_KNOWN}",
        }, indent=2)

    payload = NotificationPayload(title=title, message=message)
    success = await ch.send(payload)
    return json.dumps({
        "success": success,
        "channel": channel,
        "title": title,
    }, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════
# Extended Content + Source Tools — Phase 2/3 gap-fill
# Brings MCP server to 29 tools total
# ═══════════════════════════════════════════════════════


@mcp.tool()
async def adapt_content(
    content: str,
    from_platform: str = "threads",
    to_platform: str = "x",
) -> str:
    """Adapt content from one platform format to another.

    Rewrites the post to fit the target platform's char limit, tone, and
    best-practices (e.g. Threads→X requires tightening to 280 chars;
    Threads→LinkedIn requires adding professional framing).

    Args:
        content: Original post text.
        from_platform: Source platform (threads, instagram, facebook, x, linkedin,
                       tiktok, youtube, xiaohongshu).
        to_platform: Target platform.

    Returns:
        JSON with adapted content, char counts before/after, and platform specs.
    """
    from .core.scoring.hybrid import score_content

    _LIMITS = {
        "threads": 500, "x": 280, "instagram": 2200, "linkedin": 3000,
        "tiktok": 2200, "youtube": 5000, "xiaohongshu": 1000, "facebook": 63206,
    }
    _OPENERS = {
        "x": "🧵 ",
        "linkedin": "Insight: ",
        "xiaohongshu": "✨ ",
        "tiktok": "🔥 ",
        "youtube": "📹 ",
    }

    target_limit = _LIMITS.get(to_platform, 500)
    opener = _OPENERS.get(to_platform, "")

    # Trim to limit
    adapted = (opener + content)[:target_limit]

    # LinkedIn-specific: add line breaks for readability
    if to_platform == "linkedin" and "\n\n" not in adapted:
        parts = adapted.split(". ")
        adapted = "\n\n".join(p.strip() for p in parts if p.strip())[:target_limit]

    score_before = await score_content(content, from_platform)
    score_after = await score_content(adapted, to_platform)

    return json.dumps({
        "from_platform": from_platform,
        "to_platform": to_platform,
        "original": {"content": content, "chars": len(content), "score": round(score_before.total, 1)},
        "adapted": {"content": adapted, "chars": len(adapted), "score": round(score_after.total, 1)},
        "char_limit": target_limit,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def analyze_viral_factors(
    content: str,
    platform: str = "threads",
) -> str:
    """Deep analysis of what makes (or doesn't make) content go viral.

    Breaks down the post across 5 patent-derived dimensions with specific
    per-signal feedback and actionable improvement suggestions.

    Args:
        content: Post text to analyse.
        platform: Target platform (affects char-limit and format scoring).

    Returns:
        JSON with dimension scores, per-signal breakdown, strengths,
        weaknesses, and top 3 improvement suggestions.
    """
    from .core.scoring.hybrid import HybridScorer, _l1_heuristic, _HOOK_PATTERNS, _CTA_PATTERNS, _ENGAGEMENT_PATTERNS
    import re

    scorer = HybridScorer()
    result = await scorer.score(content, platform)

    text = content.lower()
    signals = {
        "has_emoji": bool(re.search(r"[^\w\s\d,.:;!?\"'()\[\]-]", content[:100])),
        "has_question": "?" in content,
        "has_cta": bool(re.search(r"\b(comment|reply|share|tag|follow|vote|poll)\b", text)),
        "has_number": bool(re.search(r"\b\d+\b", content)),
        "has_urgency": bool(re.search(r"\b(now|today|just|breaking|alert)\b", text)),
        "has_controversy": bool(re.search(r"\b(controversial|hot take|unpopular|fight me)\b", text)),
        "word_count": len(content.split()),
        "line_count": content.count("\n") + 1,
        "char_count": len(content),
    }

    suggestions = []
    if not signals["has_emoji"]:
        suggestions.append("Add an emoji in the first line to boost visual hook power (+10 hook)")
    if not signals["has_question"]:
        suggestions.append("End with a question to drive replies and conversation durability (+15 engagement)")
    if not signals["has_cta"]:
        suggestions.append("Add a clear CTA ('Drop a comment 👇', 'Share if you agree') (+20 engagement)")
    if signals["word_count"] < 20:
        suggestions.append("Expand content to 30-80 words for better conversation durability score")
    if result.breakdown.get("format_score", 0) < 50:
        suggestions.append(f"Adjust length — currently {signals['char_count']} chars vs ideal 40-80% of platform limit")

    return json.dumps({
        "platform": platform,
        "overall": result.to_dict(),
        "signals": signals,
        "strengths": [s for s in result.signals if "strong" in s.lower() or "good" in s.lower() or "match" in s.lower()],
        "weaknesses": [s for s in result.signals if "exceed" in s.lower() or "short" in s.lower()],
        "top_suggestions": suggestions[:3],
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def generate_hashtags(
    topic: str,
    platform: str = "threads",
    count: int = 10,
    lang: str = "en",
) -> str:
    """Generate optimized hashtags for a topic and platform.

    Returns a ranked list of hashtags based on topic relevance and
    platform-specific best practices (e.g. LinkedIn prefers 3-5 tags,
    Instagram up to 30, TikTok 3-7 challenge-style tags).

    Args:
        topic: Content topic or keyword (e.g. "AI agents", "Python tutorial").
        platform: Target platform — affects volume and style recommendations.
        count: Number of hashtags to generate (1-30, default: 10).
        lang: Language hint — "en" or "zh-TW" (for Chinese topics).

    Returns:
        JSON with hashtag list, platform recommendation, and usage tips.
    """
    import re

    count = max(1, min(count, 30))
    words = re.findall(r"[a-zA-Z\u4e00-\u9fff\u3040-\u30ff]+", topic)

    # Platform-specific tag limits
    _PLATFORM_TAG_ADVICE = {
        "threads": {"optimal": 3, "max": 5, "style": "multi-word topic tags"},
        "x": {"optimal": 2, "max": 3, "style": "trending single-word or phrase"},
        "instagram": {"optimal": 15, "max": 30, "style": "mix niche + broad"},
        "tiktok": {"optimal": 5, "max": 10, "style": "challenge-style #ForYou tags"},
        "linkedin": {"optimal": 3, "max": 5, "style": "professional industry terms"},
        "youtube": {"optimal": 5, "max": 15, "style": "SEO-optimized descriptive"},
        "xiaohongshu": {"optimal": 8, "max": 20, "style": "Chinese keyword tags"},
        "facebook": {"optimal": 2, "max": 5, "style": "minimal, brand or event"},
    }
    advice = _PLATFORM_TAG_ADVICE.get(platform, {"optimal": 5, "max": 10, "style": "general"})

    # Build hashtag variants from topic words
    core = topic.replace(" ", "")  # e.g. "AIAgents"
    tags = []

    # Primary tag from full topic
    if core:
        tags.append(f"#{core}")
    # Individual word tags
    for w in words:
        if len(w) >= 3:
            tags.append(f"#{w.capitalize()}")

    # Add platform/vertical context tags
    context_tags = {
        "en": ["#Trending", "#Tech", "#Innovation", "#AI", "#Future", "#Viral",
               "#Tips", "#Learn", "#Growth", "#Digital"],
        "zh-TW": ["#科技", "#趨勢", "#人工智慧", "#創新", "#學習", "#成長"],
    }
    for tag in context_tags.get(lang, context_tags["en"]):
        if tag not in tags:
            tags.append(tag)

    # Deduplicate and trim
    seen: set[str] = set()
    unique: list[str] = []
    for t in tags:
        lt = t.lower()
        if lt not in seen:
            seen.add(lt)
            unique.append(t)

    selected = unique[:count]

    return json.dumps({
        "topic": topic,
        "platform": platform,
        "hashtags": selected,
        "count": len(selected),
        "platform_advice": advice,
        "recommended_count": advice["optimal"],
        "tip": f"For {platform}: use ~{advice['optimal']} tags ({advice['style']})",
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_source_status() -> str:
    """Check health status of all registered trend sources.

    Performs a lightweight ping to verify each source is reachable and
    returning data. Useful for debugging which sources are failing.

    Returns:
        JSON with per-source status (ok / error / skipped) and summary counts.
    """
    import asyncio as _asyncio

    sources = _agg.list_sources()
    results = []

    async def _check(src_info: dict) -> dict:
        name = src_info["name"]
        inst = _agg._instances.get(name)
        if inst is None:
            return {"name": name, "status": "skipped", "error": "no instance"}
        try:
            items = await _asyncio.wait_for(inst.fetch_trending(count=1), timeout=10)
            return {
                "name": name,
                "status": "ok" if items else "empty",
                "item_count": len(items),
                "requires_auth": src_info.get("requires_auth", False),
            }
        except _asyncio.TimeoutError:
            return {"name": name, "status": "timeout", "error": "10s timeout"}
        except Exception as e:
            return {"name": name, "status": "error", "error": str(e)[:100]}

    # Check all sources in parallel — each has a 10s timeout so total is bounded
    tasks = [_check(s) for s in sources]
    results = list(await _asyncio.gather(*tasks))

    summary = {"ok": 0, "empty": 0, "error": 0, "timeout": 0, "skipped": 0}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1

    return json.dumps({
        "checked": len(results),
        "total_sources": len(sources),
        "summary": summary,
        "sources": results,
        "note": f"Checked all {len(results)} sources in parallel.",
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_trend_velocity(
    keyword: str,
    hours: int = 24,
    source: str = "",
) -> str:
    """Get real-time velocity and momentum for a trend keyword.

    Queries recent history to compute how fast the keyword is rising or falling.
    Returns velocity (score change per hour), acceleration, and projected
    score in the next 6 and 24 hours.

    Args:
        keyword: Trend keyword to analyse.
        hours: Lookback window in hours (1-168, default: 24).
        source: Filter by source name (default: all sources).

    Returns:
        JSON with velocity, acceleration, trend_direction, and projections.
    """
    from .core.intelligence.lifecycle import predict_lifecycle, lifecycle_emoji

    hours = max(1, min(hours, 168))  # clamp to 1h–7d
    days = max(1, min(hours // 24 + 1, 30))
    hist = await _agg.history(keyword=keyword, days=days, source=source)
    # history() returns newest-first; reverse to oldest-first for velocity/lifecycle
    records = list(reversed(hist.get("records", [])))

    if not records:
        return json.dumps({
            "keyword": keyword,
            "velocity": 0.0,
            "acceleration": 0.0,
            "current_score": 0.0,
            "trend_direction": "unknown",
            "projection_6h": 0.0,
            "projection_24h": 0.0,
            "history_count": 0,
        }, indent=2, ensure_ascii=False)

    scores = [r["score"] for r in records]
    current = scores[-1]
    n = len(scores)

    # Velocity: average change per record
    deltas = [scores[i + 1] - scores[i] for i in range(n - 1)]
    velocity = sum(deltas) / len(deltas) if deltas else 0.0

    # Acceleration
    mid = max(1, len(deltas) // 2)
    first_v = sum(deltas[:mid]) / mid if deltas[:mid] else 0.0
    second_v = sum(deltas[mid:]) / max(len(deltas[mid:]), 1) if deltas[mid:] else 0.0
    acceleration = second_v - first_v

    direction = "rising" if velocity > 0.5 else "falling" if velocity < -0.5 else "stable"
    stage = predict_lifecycle(current, records)

    # Simple linear projections (clamped 0-100)
    proj_6h = max(0.0, min(100.0, current + velocity * 0.25))
    proj_24h = max(0.0, min(100.0, current + velocity))

    return json.dumps({
        "keyword": keyword,
        "current_score": round(current, 1),
        "velocity": round(velocity, 3),
        "acceleration": round(acceleration, 3),
        "trend_direction": direction,
        "lifecycle_stage": stage.value,
        "lifecycle_emoji": lifecycle_emoji(stage),
        "projection_6h": round(proj_6h, 1),
        "projection_24h": round(proj_24h, 1),
        "history_count": n,
        "hours_lookback": hours,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def batch_score_content(
    contents: str,
    platform: str = "threads",
) -> str:
    """Score multiple posts at once using the Hybrid Scoring 2.0 engine.

    Accepts a JSON array of post strings and returns a scored ranking.
    Useful for comparing multiple drafts before publishing.

    Args:
        contents: JSON array of post strings, e.g. ["Post A text", "Post B text"].
                  Max 10 posts per batch.
        platform: Target platform for format scoring (default: threads).

    Returns:
        JSON with ranked list of posts by score, including dimension breakdowns.
    """
    from .core.scoring.hybrid import score_content

    try:
        posts = json.loads(contents)
        if not isinstance(posts, list):
            return json.dumps({"error": "contents must be a JSON array of strings"})
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    import asyncio as _asyncio_bs
    posts = posts[:10]  # Cap at 10
    valid = [(i, post) for i, post in enumerate(posts) if isinstance(post, str)]
    results_raw = await _asyncio_bs.gather(
        *[score_content(post, platform) for _, post in valid],
        return_exceptions=True,
    )
    scored = []
    for (i, post), result in zip(valid, results_raw):
        if isinstance(result, Exception):
            continue
        scored.append({
            "index": i,
            "content_preview": post[:80] + ("..." if len(post) > 80 else ""),
            **result.to_dict(),
        })

    scored.sort(key=lambda x: x["total"], reverse=True)
    for rank, item in enumerate(scored, 1):
        item["rank"] = rank

    skipped = len(posts) - len(valid)
    return json.dumps({
        "platform": platform,
        "count": len(scored),
        "skipped": skipped,
        "results": scored,
        "best_index": scored[0]["index"] if scored else None,
    }, indent=2, ensure_ascii=False)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
