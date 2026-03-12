"""MCP Server for trend-mcp."""

from __future__ import annotations

import json

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise ImportError("Install mcp: pip install 'trend-mcp[mcp]'")

from .aggregator import TrendAggregator

mcp = FastMCP("trend-mcp")

_agg = TrendAggregator()


@mcp.tool()
async def get_trending(
    sources: str = "",
    geo: str = "",
    count: int = 20,
) -> str:
    """Get trending topics from free sources.

    Args:
        sources: Comma-separated source names (default: all).
                 Available: google_trends, hackernews, mastodon, bluesky, wikipedia, github, pypi
        geo: Country code for regional trends (e.g. TW, US, JP)
        count: Number of results per source (default: 20)

    Returns:
        JSON with merged ranking + per-source results
    """
    src_list = [s.strip() for s in sources.split(",") if s.strip()] or None
    result = await _agg.trending(sources=src_list, geo=geo, count=count)
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
    src_list = [s.strip() for s in sources.split(",") if s.strip()] or None
    result = await _agg.search(query=query, sources=src_list, geo=geo)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def list_sources() -> str:
    """List all available trend sources and their properties."""
    return json.dumps(_agg.list_sources(), indent=2, ensure_ascii=False)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
