"""CLI for trend-pulse."""

from __future__ import annotations

import argparse
import asyncio
import json

from .aggregator import TrendAggregator


def main():
    parser = argparse.ArgumentParser(
        prog="trend-pulse",
        description="Free trending topics aggregator (35+ sources, zero auth, plugin system)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # trending
    p_trend = sub.add_parser("trending", help="Get trending topics")
    p_trend.add_argument("--sources", "-s", help="Comma-separated source names")
    p_trend.add_argument("--geo", "-g", default="", help="Country code (e.g. TW, US, JP)")
    p_trend.add_argument("--count", "-n", type=int, default=20)
    p_trend.add_argument("--save", action="store_true", help="Save snapshot to history DB")

    # search
    p_search = sub.add_parser("search", help="Search trends by keyword")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--sources", "-s", help="Comma-separated source names")
    p_search.add_argument("--geo", "-g", default="")

    # history
    p_hist = sub.add_parser("history", help="Query trend history for a keyword")
    p_hist.add_argument("keyword", help="Keyword to look up")
    p_hist.add_argument("--days", "-d", type=int, default=30, help="Days to look back (default: 30)")
    p_hist.add_argument("--source", default="", help="Filter by source name")

    # snapshot
    p_snap = sub.add_parser("snapshot", help="Take a snapshot (fetch + save to DB)")
    p_snap.add_argument("--sources", "-s", help="Comma-separated source names (default: all)")
    p_snap.add_argument("--geo", "-g", default="", help="Country code")
    p_snap.add_argument("--count", "-n", type=int, default=20)

    # list
    sub.add_parser("sources", help="List available sources")

    args = parser.parse_args()

    if args.command == "sources":
        agg = TrendAggregator()
        print(json.dumps(agg.list_sources(), indent=2, ensure_ascii=False))
        return

    agg = TrendAggregator()

    if args.command == "trending":
        sources = args.sources.split(",") if args.sources else None
        result = asyncio.run(
            agg.trending(sources=sources, geo=args.geo, count=args.count, save=args.save)
        )
    elif args.command == "search":
        sources = args.sources.split(",") if args.sources else None
        result = asyncio.run(agg.search(query=args.query, sources=sources, geo=args.geo))
    elif args.command == "history":
        result = asyncio.run(
            agg.history(keyword=args.keyword, days=args.days, source=args.source)
        )
    elif args.command == "snapshot":
        sources = args.sources.split(",") if args.sources else None
        result = asyncio.run(
            agg.snapshot(sources=sources, geo=args.geo, count=args.count)
        )
    else:
        parser.print_help()
        return

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
