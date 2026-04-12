"""TrendPulse AI — FastAPI REST endpoints.

Exposes trend data as a REST API for webhook integrations and external tools.

Run:
    uvicorn trend_pulse.dashboard.api:app --reload --port 8000

Requires:
    pip install 'trend-pulse[dashboard]'
"""

from __future__ import annotations

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

from ..aggregator import TrendAggregator

if _FASTAPI_AVAILABLE:
    app = FastAPI(
        title="TrendPulse AI API",
        description="REST API for trend data, clustering, and content generation",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    _agg = TrendAggregator()

    # ──────────────────────────────────────
    # Trend endpoints
    # ──────────────────────────────────────

    @app.get("/trending")
    async def trending(
        sources: str = Query("", description="Comma-separated source names"),
        geo: str = Query("", description="Country code"),
        count: int = Query(20, ge=1, le=100),
        save: bool = Query(False),
    ):
        """Fetch trending topics from all or specified sources."""
        src_list = [s.strip() for s in sources.split(",") if s.strip()] or None
        return await _agg.trending(sources=src_list, geo=geo, count=count, save=save)

    @app.get("/search")
    async def search(
        q: str = Query(..., description="Search query"),
        sources: str = Query(""),
        geo: str = Query(""),
    ):
        """Search for a keyword across trend sources."""
        src_list = [s.strip() for s in sources.split(",") if s.strip()] or None
        return await _agg.search(query=q, sources=src_list, geo=geo)

    @app.get("/sources")
    async def list_sources():
        """List all available trend sources."""
        sources_list = _agg.list_sources()
        return {"sources": sources_list, "total": len(sources_list)}

    @app.get("/history")
    async def history(
        keyword: str = Query(...),
        days: int = Query(30, ge=1, le=365),
        source: str = Query(""),
    ):
        """Query historical trend data for a keyword."""
        return await _agg.history(keyword=keyword, days=days, source=source)

    @app.post("/snapshot")
    async def snapshot(
        sources: str = Query(""),
        geo: str = Query(""),
        count: int = Query(20, ge=1, le=100),
    ):
        """Take a trend snapshot and save to history DB."""
        src_list = [s.strip() for s in sources.split(",") if s.strip()] or None
        return await _agg.snapshot(sources=src_list, geo=geo, count=count)

    # ──────────────────────────────────────
    # Intelligence endpoints
    # ──────────────────────────────────────

    @app.get("/clusters")
    async def clusters(
        sources: str = Query(""),
        geo: str = Query(""),
        count: int = Query(20),
        threshold: float = Query(0.25, ge=0.05, le=0.9),
    ):
        """Get semantic trend clusters."""
        from ..core.intelligence.clusters import cluster_trends
        from ..sources.base import TrendItem

        src_list = [s.strip() for s in sources.split(",") if s.strip()] or None
        raw = await _agg.trending(sources=src_list, geo=geo, count=count)
        items = []
        for src_result in raw.get("sources", {}).values():
            for it in src_result:
                items.append(TrendItem(
                    keyword=it.get("keyword", ""),
                    source=it.get("source", ""),
                    score=it.get("score", 0),
                ))

        clust = await cluster_trends(items, threshold=threshold)
        return {
            "cluster_count": len(clust),
            "threshold": threshold,
            "clusters": [c.to_dict() for c in clust],
        }

    @app.get("/lifecycle/{keyword}")
    async def lifecycle(
        keyword: str,
        days: int = Query(30, ge=1, le=365),
    ):
        """Predict lifecycle stage of a keyword."""
        from ..core.intelligence.lifecycle import predict_lifecycle, lifecycle_emoji

        hist = await _agg.history(keyword=keyword, days=days)
        # history() returns newest-first; reverse to oldest-first for lifecycle
        records = list(reversed(hist.get("records", [])))
        current = records[-1]["score"] if records else 0.0
        stage = predict_lifecycle(current, records)
        return {
            "keyword": keyword,
            "stage": stage.value,
            "emoji": lifecycle_emoji(stage),
            "current_score": current,
            "history_count": len(records),
        }

    # ──────────────────────────────────────
    # Content endpoints
    # ──────────────────────────────────────

    class _ContentScoreRequest(BaseModel):
        content: str
        platform: str = "threads"

    @app.post("/content/score")
    async def score_content(request: _ContentScoreRequest):
        """Score content with Hybrid Scoring 2.0."""
        from ..core.scoring.hybrid import score_content as _score
        result = await _score(request.content, request.platform)
        return result.to_dict()

    @app.get("/health")
    async def health():
        """API health check."""
        from .. import __version__
        return {
            "status": "ok",
            "version": __version__,
            "sources": len(_agg.list_sources()),
        }

else:
    # Stub for environments without FastAPI
    app = None  # type: ignore[assignment]
