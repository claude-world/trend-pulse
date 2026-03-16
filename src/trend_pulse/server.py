"""MCP Server for trend-pulse."""

from __future__ import annotations

import json

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise ImportError("Install mcp: pip install 'trend-pulse[mcp]'")

from .aggregator import TrendAggregator

mcp = FastMCP("trend-pulse")

_agg = TrendAggregator()


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
                 Available: google_trends, hackernews, mastodon, bluesky, wikipedia,
                 github, pypi, google_news, lobsters, devto, npm, reddit,
                 coingecko, dockerhub, stackoverflow, arxiv, producthunt, lemmy,
                 dcard, ptt
        geo: Country code for regional trends (e.g. TW, US, JP)
        count: Number of results per source (default: 20)
        save: Save snapshot to history DB for velocity tracking (default: false)

    Returns:
        JSON with merged ranking + per-source results (includes direction/velocity if history exists)
    """
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


def main():
    mcp.run()


if __name__ == "__main__":
    main()
