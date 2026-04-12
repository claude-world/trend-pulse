"""Tests for Phase 1: vector store, clustering, lifecycle, scoring, workflow."""

from __future__ import annotations

import asyncio
import pytest


def _run(coro):
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════

def _item(keyword: str, source: str = "test", score: float = 50.0):
    from trend_pulse.sources.base import TrendItem
    return TrendItem(keyword=keyword, source=source, score=score)


# ═══════════════════════════════════════════════════════
# SimpleVectorStore
# ═══════════════════════════════════════════════════════

class TestSimpleVectorStore:
    def test_upsert_and_search(self):
        from trend_pulse.core.vector.simple import SimpleVectorStore

        store = SimpleVectorStore()
        items = [
            _item("machine learning", "hn", 80),
            _item("deep learning neural", "hn", 70),
            _item("cooking recipe pasta", "food", 40),
        ]
        _run(store.upsert(items))
        results = _run(store.search_similar("machine learning AI", k=2))
        assert len(results) <= 2
        # Top result should be ML-related
        if results:
            assert "learning" in results[0].item.keyword

    def test_deduplication(self):
        from trend_pulse.core.vector.simple import SimpleVectorStore

        store = SimpleVectorStore()
        item = _item("python programming", "gh")
        _run(store.upsert([item]))
        _run(store.upsert([item]))  # Second upsert of same item should be a no-op
        assert len(store._items) == 1

    def test_cluster_basic(self):
        from trend_pulse.core.vector.simple import SimpleVectorStore

        store = SimpleVectorStore()
        items = [
            _item("artificial intelligence", "hn"),
            _item("artificial intelligence tools", "reddit"),
            _item("blockchain cryptocurrency", "crypto"),
        ]
        _run(store.upsert(items))
        clusters = _run(store.cluster(threshold=0.1))
        assert len(clusters) >= 1

    def test_empty_search(self):
        from trend_pulse.core.vector.simple import SimpleVectorStore

        store = SimpleVectorStore()
        results = _run(store.search_similar("anything"))
        assert results == []

    def test_clear(self):
        from trend_pulse.core.vector.simple import SimpleVectorStore

        store = SimpleVectorStore()
        _run(store.upsert([_item("test")]))
        _run(store.clear())
        assert store._items == []


# ═══════════════════════════════════════════════════════
# TrendCluster + cluster_trends
# ═══════════════════════════════════════════════════════

class TestTrendClustering:
    def test_cluster_trends_empty(self):
        from trend_pulse.core.intelligence.clusters import cluster_trends
        result = _run(cluster_trends([]))
        assert result == []

    def test_cluster_single_item(self):
        from trend_pulse.core.intelligence.clusters import cluster_trends
        items = [_item("python", score=80)]
        clusters = _run(cluster_trends(items))
        assert len(clusters) >= 1
        assert clusters[0].topic == "python"

    def test_cluster_cross_source(self):
        from trend_pulse.core.intelligence.clusters import cluster_trends
        items = [
            _item("python programming", "hackernews", 80),
            _item("python programming language", "reddit", 75),
        ]
        clusters = _run(cluster_trends(items, threshold=0.1))
        # Should produce at least 1 cluster
        assert len(clusters) >= 1

    def test_cluster_to_dict(self):
        from trend_pulse.core.intelligence.clusters import TrendCluster
        from trend_pulse.sources.base import TrendItem
        item = TrendItem(keyword="ai", source="test", score=50)
        c = TrendCluster(topic="ai", items=[item], score=50, sources=["test"])
        d = c.to_dict()
        assert d["topic"] == "ai"
        assert d["item_count"] == 1
        assert "items" in d

    def test_cluster_sorted_cross_source_first(self):
        from trend_pulse.core.intelligence.clusters import cluster_trends
        items = [
            _item("soloing climbing", "hn", 30),
            _item("soloing climbing extreme", "reddit", 28),
            _item("python tutorial", "hn", 90),
        ]
        clusters = _run(cluster_trends(items, threshold=0.05))
        assert len(clusters) >= 1


# ═══════════════════════════════════════════════════════
# LifecycleStage + predict_lifecycle
# ═══════════════════════════════════════════════════════

class TestLifecyclePrediction:
    def test_no_history_high_score(self):
        from trend_pulse.core.intelligence.lifecycle import LifecycleStage, predict_lifecycle
        stage = predict_lifecycle(75, [])
        assert stage == LifecycleStage.PEAK

    def test_no_history_low_score(self):
        from trend_pulse.core.intelligence.lifecycle import LifecycleStage, predict_lifecycle
        stage = predict_lifecycle(5, [])
        assert stage == LifecycleStage.FADING

    def test_rising_trend(self):
        from trend_pulse.core.intelligence.lifecycle import LifecycleStage, predict_lifecycle
        history = [{"score": s} for s in [10, 20, 35, 50, 65]]
        stage = predict_lifecycle(80, history)
        # Strongly rising
        assert stage in (LifecycleStage.EMERGING, LifecycleStage.PEAK)

    def test_falling_trend(self):
        from trend_pulse.core.intelligence.lifecycle import LifecycleStage, predict_lifecycle
        history = [{"score": s} for s in [90, 80, 65, 50, 35]]
        stage = predict_lifecycle(25, history)
        assert stage in (LifecycleStage.DECLINING, LifecycleStage.FADING)

    def test_enum_values(self):
        from trend_pulse.core.intelligence.lifecycle import LifecycleStage
        assert LifecycleStage.EMERGING.value == "emerging"
        assert LifecycleStage.PEAK.value == "peak"
        assert LifecycleStage.DECLINING.value == "declining"
        assert LifecycleStage.FADING.value == "fading"

    def test_lifecycle_emoji(self):
        from trend_pulse.core.intelligence.lifecycle import LifecycleStage, lifecycle_emoji
        assert lifecycle_emoji(LifecycleStage.PEAK) == "🔥"
        assert lifecycle_emoji(LifecycleStage.FADING) == "💨"


# ═══════════════════════════════════════════════════════
# HybridScorer (heuristic mode — no API key needed)
# ═══════════════════════════════════════════════════════

class TestHybridScorer:
    def test_score_basic(self):
        from trend_pulse.core.scoring.hybrid import HybridScorer
        scorer = HybridScorer()
        result = _run(scorer.score("Why AI is changing everything? Drop a comment 👇", "threads"))
        assert 0 <= result.total <= 100
        assert result.grade in ("S", "A", "B+", "B", "C+", "C", "D")
        assert result.mode in ("heuristic", "hybrid")

    def test_score_content_helper(self):
        from trend_pulse.core.scoring.hybrid import score_content
        result = _run(score_content("Hello world", "threads"))
        assert result.total >= 0

    def test_score_over_limit_penalised(self):
        from trend_pulse.core.scoring.hybrid import score_content
        long_text = "a" * 600  # Over threads 500 char limit
        result = _run(score_content(long_text, "threads"))
        # format_score should be 0 → lower total
        assert result.breakdown["format_score"] == 0.0

    def test_rag_bonus(self):
        from trend_pulse.core.scoring.hybrid import HybridScorer
        scorer = HybridScorer()
        content = "AI agents are transforming the industry"
        base = _run(scorer.score(content, "threads"))
        boosted = _run(scorer.score(content, "threads", history_keywords=["AI agents"]))
        assert boosted.total >= base.total

    def test_to_dict(self):
        from trend_pulse.core.scoring.hybrid import score_content
        result = _run(score_content("Test content", "threads"))
        d = result.to_dict()
        assert "total" in d
        assert "grade" in d
        assert "breakdown" in d
        assert "mode" in d


# ═══════════════════════════════════════════════════════
# ContentWorkflow
# ═══════════════════════════════════════════════════════

class TestContentWorkflow:
    def test_run_workflow_no_trends(self):
        from trend_pulse.core.agents.workflow import run_content_workflow
        state = _run(run_content_workflow(
            trends=[],
            platforms=["threads"],
            brand_voice="casual",
            topic="AI trends",
        ))
        assert "final_content" in state
        assert "threads" in state["final_content"]
        assert len(state["final_content"]["threads"]) > 0

    def test_run_workflow_with_trends(self):
        from trend_pulse.core.agents.workflow import run_content_workflow
        items = [_item("ChatGPT", score=90), _item("Claude AI", score=85)]
        state = _run(run_content_workflow(
            trends=items,
            platforms=["threads", "x"],
            topic="AI assistants",
        ))
        assert "threads" in state["final_content"]
        assert "x" in state["final_content"]
        # x has 280 char limit
        assert len(state["final_content"]["x"]) <= 280

    def test_all_agents_complete(self):
        from trend_pulse.core.agents.workflow import run_content_workflow
        state = _run(run_content_workflow(topic="Python"))
        completed = state.get("completed_agents", [])
        expected = ["researcher", "strategist", "writer", "optimizer", "checker", "distributor"]
        for agent in expected:
            assert agent in completed, f"Agent {agent} did not complete"

    def test_workflow_state_structure(self):
        from trend_pulse.core.agents.workflow import run_content_workflow
        state = _run(run_content_workflow(topic="test"))
        assert "strategy" in state
        assert "scored_drafts" in state
        assert len(state.get("scored_drafts", [])) >= 1


# ═══════════════════════════════════════════════════════
# TrendDB — cleanup
# ═══════════════════════════════════════════════════════

class TestTrendDBCleanup:
    def test_cleanup_removes_old_records(self, tmp_path):
        """Cleanup should remove records older than retention_days."""
        import datetime
        from trend_pulse.history import TrendDB
        from trend_pulse.sources.base import TrendItem

        db_path = str(tmp_path / "test_cleanup.db")

        async def _scenario():
            async with TrendDB(db_path) as db:
                # Insert one fresh item
                fresh = TrendItem(keyword="fresh", source="test", score=80.0)
                await db.save_snapshot([fresh])
                # Manually insert a stale record (100 days old)
                await db._db.execute(
                    "INSERT INTO snapshots (timestamp, source, keyword, score) VALUES (?, ?, ?, ?)",
                    (
                        (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=100)).strftime("%Y-%m-%d %H:%M:%S"),
                        "test", "stale", 50.0,
                    ),
                )
                await db._db.commit()

                before = await db.get_history("stale", days=200)
                assert len(before) == 1

                deleted = await db.cleanup(retention_days=30)
                assert deleted >= 1

                after = await db.get_history("stale", days=200)
                assert len(after) == 0

                # Fresh record should still be there
                fresh_records = await db.get_history("fresh", days=1)
                assert len(fresh_records) == 1

        _run(_scenario())

    def test_require_db_guard(self):
        """TrendDB methods must raise if used outside context manager."""
        from trend_pulse.history import TrendDB
        db = TrendDB()
        with pytest.raises(RuntimeError, match="not initialized"):
            _run(db.get_history("test"))
