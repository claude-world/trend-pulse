"""CLI for trend-mcp."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .aggregator import TrendAggregator


def main():
    parser = argparse.ArgumentParser(
        prog="trend-mcp",
        description="Free trending topics aggregator (7 sources, zero auth)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # trending
    p_trend = sub.add_parser("trending", help="Get trending topics")
    p_trend.add_argument("--sources", "-s", help="Comma-separated source names")
    p_trend.add_argument("--geo", "-g", default="", help="Country code (e.g. TW, US, JP)")
    p_trend.add_argument("--count", "-n", type=int, default=20)

    # search
    p_search = sub.add_parser("search", help="Search trends by keyword")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--sources", "-s", help="Comma-separated source names")
    p_search.add_argument("--geo", "-g", default="")

    # list
    sub.add_parser("sources", help="List available sources")

    args = parser.parse_args()

    if args.command == "sources":
        agg = TrendAggregator()
        print(json.dumps(agg.list_sources(), indent=2, ensure_ascii=False))
        return

    sources = args.sources.split(",") if getattr(args, "sources", None) else None
    agg = TrendAggregator()

    if args.command == "trending":
        result = asyncio.run(agg.trending(sources=sources, geo=args.geo, count=args.count))
    elif args.command == "search":
        result = asyncio.run(agg.search(query=args.query, sources=sources, geo=args.geo))
    else:
        parser.print_help()
        return

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
