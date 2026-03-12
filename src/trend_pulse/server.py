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
                 coingecko, dockerhub, stackoverflow
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
# Content Generation + Review Tools
# ═══════════════════════════════════════════════════════


@mcp.tool()
async def generate_viral_posts(
    topic: str,
    content_type: str = "debate",
    count: int = 5,
) -> str:
    """Generate viral posts scored against Meta's 7 ranking patents.

    Args:
        topic: Subject to generate posts about (e.g. "AI工具", "Claude Code")
        content_type: Post style — opinion, story, debate, howto, list, question, news, meme
        count: Number of posts to generate (default: 5)

    Returns:
        JSON with ranked posts, each including text, 5D patent scores, and grade (S/A/B/C/D)
    """
    from .content.generator import generate_posts

    posts = generate_posts(topic, content_type, count)
    result = {
        "topic": topic,
        "content_type": content_type,
        "count": len(posts),
        "posts": posts,
        "publish_ready": [p for p in posts if p["scores"]["overall"] >= 70],
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def score_viral_post(text: str) -> str:
    """Score a post on 5 patent-derived dimensions.

    Dimensions (weighted):
    - Hook Power 25% (EdgeRank Weight + Andromeda)
    - Engagement Trigger 25% (Story-Viewer Tuple + Dear Algo)
    - Conversation Durability 20% (Threads 72hr window)
    - Velocity Potential 15% (Andromeda Real-time)
    - Format Score 15% (Multi-modal Indexing)

    Args:
        text: The post content to score

    Returns:
        JSON with overall score (0-100), grade (S/A/B/C/D), 5 dimension scores, and suggestions
    """
    from .patents.scorer import score_post as _score

    result = _score(text)
    result["text_preview"] = text[:80] + "..." if len(text) > 80 else text
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def generate_content(
    topic: str,
    content_type: str = "debate",
    count: int = 3,
) -> str:
    """Generate complete 3-platform content package from a single topic.

    Produces adapted content for Threads + Instagram + Facebook, including:
    - Platform-specific text (respecting char limits)
    - Image prompts for AI generation
    - Carousel slide specs for IG
    - Quote card HTML
    - Reel script with scene breakdown
    - Optimal posting schedule

    Args:
        topic: Subject to create content about
        content_type: Post style — opinion, story, debate, howto, list, question, news, meme
        count: Number of content packages (default: 3)

    Returns:
        JSON with complete cross-platform content packages
    """
    from .content.adapter import full_pipeline

    result = full_pipeline(topic, content_type, count)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def review_content(
    text: str,
    platform: str = "threads",
    auto_fix: bool = False,
) -> str:
    """Review content against patent scores and platform compliance.

    Quality gate checks:
    - Viral Score >= 70
    - Conversation Durability >= 55
    - Hook effectiveness (first line 10-45 chars)
    - CTA presence and clarity
    - Character count within platform limits

    Args:
        text: The post content to review
        platform: Target platform — threads (500 chars), instagram (2200), facebook (63206)
        auto_fix: If true, automatically fix issues (trim text, add CTA, strengthen hook)

    Returns:
        JSON with verdict (pass/fail), 5D scores, issues list, and optionally fixed text
    """
    from .content.reviewer import review

    result = review(text, platform, auto_fix)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def generate_reel_script(
    topic: str,
    style: str = "educational",
    duration: int = 30,
) -> str:
    """Generate a Reels/Short video script with timing and visual cues.

    Optimized for Instagram Reels algorithm (completion rate priority).

    Args:
        topic: Subject of the reel
        style: Script style — educational, storytelling, listicle
        duration: Target duration in seconds (default: 30)

    Returns:
        JSON with title, scene-by-scene breakdown (timing, visuals, captions, voiceover),
        music suggestion, editing notes, and post caption
    """
    from .content.adapter import generate_reel_script as _gen_reel

    result = _gen_reel(topic, style, duration)
    return json.dumps(result, indent=2, ensure_ascii=False)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
