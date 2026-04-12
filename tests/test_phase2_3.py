"""Tests for Phase 2 (content factory + scoring) and Phase 3 (notifications + server tools)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch


def _run(coro):
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════
# Platform adapter — 8 platforms
# ═══════════════════════════════════════════════════════

class TestPlatformAdapterExpanded:
    def test_all_8_platforms_present(self):
        from trend_pulse.content.adapter import PLATFORM_SPECS
        expected = {"threads", "instagram", "facebook", "x", "tiktok", "linkedin", "youtube", "xiaohongshu"}
        assert expected <= set(PLATFORM_SPECS.keys()), f"Missing: {expected - set(PLATFORM_SPECS.keys())}"

    def test_x_char_limit(self):
        from trend_pulse.content.adapter import get_platform_specs
        spec = get_platform_specs("x", "en")
        assert spec["max_chars"] == 280

    def test_linkedin_spec(self):
        from trend_pulse.content.adapter import get_platform_specs
        spec = get_platform_specs("linkedin", "en")
        assert spec["max_chars"] == 3000

    def test_tiktok_spec(self):
        from trend_pulse.content.adapter import get_platform_specs
        spec = get_platform_specs("tiktok", "en")
        assert "video" in spec["format"].lower() or "tiktok" in str(spec)

    def test_youtube_spec(self):
        from trend_pulse.content.adapter import get_platform_specs
        spec = get_platform_specs("youtube", "en")
        assert spec["max_chars"] == 5000

    def test_xiaohongshu_spec_zh(self):
        from trend_pulse.content.adapter import get_platform_specs
        spec = get_platform_specs("xiaohongshu", "zh-TW")
        assert spec["max_chars"] == 1000


# ═══════════════════════════════════════════════════════
# Workflow multi-platform
# ═══════════════════════════════════════════════════════

class TestWorkflowMultiPlatform:
    def test_x_content_within_limit(self):
        from trend_pulse.core.agents.workflow import run_content_workflow
        state = _run(run_content_workflow(
            platforms=["x"],
            topic="Python 3.14",
        ))
        x_content = state["final_content"].get("x", "")
        assert len(x_content) <= 280

    def test_linkedin_content_generated(self):
        from trend_pulse.core.agents.workflow import run_content_workflow
        state = _run(run_content_workflow(
            platforms=["linkedin"],
            brand_voice="professional",
            topic="software engineering",
        ))
        assert "linkedin" in state["final_content"]

    def test_multi_platform_output(self):
        from trend_pulse.core.agents.workflow import run_content_workflow
        platforms = ["threads", "x", "linkedin"]
        state = _run(run_content_workflow(platforms=platforms, topic="AI"))
        for plat in platforms:
            assert plat in state["final_content"]


# ═══════════════════════════════════════════════════════
# Notification channels
# ═══════════════════════════════════════════════════════

class TestNotificationChannels:
    def test_discord_returns_false_no_url(self):
        from trend_pulse.notifications import DiscordWebhook
        from trend_pulse.notifications.base import NotificationPayload
        ch = DiscordWebhook(webhook_url="")
        result = _run(ch.send(NotificationPayload(title="test", message="hello")))
        assert result is False

    def test_telegram_returns_false_no_token(self):
        from trend_pulse.notifications import TelegramBot
        from trend_pulse.notifications.base import NotificationPayload
        ch = TelegramBot(token="", chat_id="")
        result = _run(ch.send(NotificationPayload(title="test", message="hello")))
        assert result is False

    def test_generic_webhook_returns_false_no_url(self):
        from trend_pulse.notifications import GenericWebhook
        from trend_pulse.notifications.base import NotificationPayload
        ch = GenericWebhook(url="")
        result = _run(ch.send(NotificationPayload(title="test", message="hello")))
        assert result is False

    def test_payload_to_text(self):
        from trend_pulse.notifications.base import NotificationPayload
        p = NotificationPayload(title="Alert", message="Trend rising", level="warning")
        text = p.to_text()
        assert "Alert" in text
        assert "Trend rising" in text
        assert "WARNING" in text

    def test_send_text_convenience(self):
        from trend_pulse.notifications import DiscordWebhook
        ch = DiscordWebhook(webhook_url="")
        result = _run(ch.send_text("title", "body"))
        assert result is False  # No URL configured


# ═══════════════════════════════════════════════════════
# New MCP server tools — Phase 2+3
# ═══════════════════════════════════════════════════════

class TestPhase2ServerTools:
    def test_new_tools_registered(self):
        from trend_pulse.server import mcp
        tools = mcp._tool_manager._tools
        expected = {
            "run_content_workflow", "get_ab_variants", "score_content_hybrid",
            "get_campaign_calendar", "get_trend_report", "compare_trends",
            "export_data", "send_notification",
        }
        for name in expected:
            assert name in tools, f"Missing tool: {name}"

    def test_total_tool_count_23(self):
        from trend_pulse.server import mcp
        tools = mcp._tool_manager._tools
        assert len(tools) >= 29  # 29 tools as of v2.0

    def test_score_content_hybrid(self):
        from trend_pulse.server import score_content_hybrid
        result = _run(score_content_hybrid("Why AI matters? Drop a comment 👇", "threads"))
        data = json.loads(result)
        assert "total" in data
        assert "grade" in data
        assert "breakdown" in data
        assert 0 <= data["total"] <= 100

    def test_get_ab_variants(self):
        from trend_pulse.server import get_ab_variants
        result = _run(get_ab_variants("Test content about AI", "threads", 3))
        data = json.loads(result)
        assert "variants" in data
        assert len(data["variants"]) == 4  # original + 3 variants
        assert "recommended" in data

    def test_get_campaign_calendar(self):
        from trend_pulse.server import get_campaign_calendar
        result = _run(get_campaign_calendar("AI,Python", 5, "threads"))
        data = json.loads(result)
        assert data["days"] == 5
        assert len(data["calendar"]) == 5
        for entry in data["calendar"]:
            assert "day" in entry
            assert "topic" in entry
            assert "suggested_angle" in entry

    def test_send_notification_unknown_channel(self):
        from trend_pulse.server import send_notification
        result = _run(send_notification("unknown_channel", "Title", "Message"))
        data = json.loads(result)
        assert data["success"] is False
        assert "Unknown channel" in data["error"]

    def test_send_notification_no_credentials(self):
        from trend_pulse.server import send_notification
        result = _run(send_notification("discord", "Alert", "Trend spike"))
        data = json.loads(result)
        # Discord with no URL configured → False
        assert data["success"] is False

    def test_export_data_json(self):
        """Export data returns valid JSON structure even with no live sources."""
        from trend_pulse.server import export_data
        # Mock the aggregator to avoid live network calls
        with patch("trend_pulse.server._agg") as mock_agg:
            mock_agg.trending = AsyncMock(return_value={
                "sources": {
                    "test": [
                        {"keyword": "python", "source": "test", "score": 80,
                         "direction": "up", "velocity": 5, "category": "dev",
                         "url": "", "published": ""},
                    ]
                }
            })
            result = _run(export_data("json", "", 0))
        data = json.loads(result)
        assert data["format"] == "json"
        assert data["row_count"] >= 1

    def test_export_data_csv(self):
        from trend_pulse.server import export_data
        with patch("trend_pulse.server._agg") as mock_agg:
            mock_agg.trending = AsyncMock(return_value={
                "sources": {
                    "test": [
                        {"keyword": "rust", "source": "test", "score": 75,
                         "direction": "", "velocity": 0, "category": "",
                         "url": "", "published": ""},
                    ]
                }
            })
            result = _run(export_data("csv", "", 0))
        data = json.loads(result)
        assert data["format"] == "csv"
        assert "rust" in data["csv"]


# ═══════════════════════════════════════════════════════
# Phase 1 MCP tools (smoke test)
# ═══════════════════════════════════════════════════════

class TestPhase1ServerTools:
    def test_list_sources_extended(self):
        from trend_pulse.server import list_sources_extended
        result = _run(list_sources_extended())
        data = json.loads(result)
        assert "total" in data
        assert data["total"] >= 20
        assert "sources" in data

    def test_search_semantic_structure(self):
        from trend_pulse.server import search_semantic
        with patch("trend_pulse.server._agg") as mock_agg:
            mock_agg.trending = AsyncMock(return_value={
                "sources": {
                    "test": [
                        {"keyword": "machine learning", "source": "test", "score": 80,
                         "category": "ai", "url": ""},
                        {"keyword": "cooking recipes", "source": "test", "score": 40,
                         "category": "food", "url": ""},
                    ]
                }
            })
            result = _run(search_semantic("artificial intelligence", k=2))
        data = json.loads(result)
        assert "query" in data
        assert "results" in data
        assert isinstance(data["results"], list)


# ═══════════════════════════════════════════════════════
# compare_trends — correctness and parallel execution
# ═══════════════════════════════════════════════════════

class TestCompareTraends:
    def test_compare_trends_shape(self):
        from trend_pulse.server import compare_trends
        with patch("trend_pulse.server._agg") as mock_agg:
            # history() returns newest-first (DESC) — _analyze reverses to oldest-first
            mock_agg.history = AsyncMock(side_effect=[
                {"records": [{"score": s} for s in [90, 70, 50, 30, 20]]},  # rising: oldest=20→newest=90
                {"records": [{"score": s} for s in [10, 30, 50, 70, 90]]},  # falling: oldest=90→newest=10
            ])
            result = _run(compare_trends("rising_topic", "falling_topic", days=7))
        data = json.loads(result)
        assert "keyword_a" in data
        assert "keyword_b" in data
        assert "winner_by_score" in data
        assert "winner_by_momentum" in data
        # rising_topic has positive velocity; falling_topic has negative
        assert data["keyword_a"]["velocity"] > 0
        assert data["keyword_b"]["velocity"] < 0
        assert data["winner_by_momentum"] == "rising_topic"

    def test_compare_trends_winner_by_score(self):
        from trend_pulse.server import compare_trends
        with patch("trend_pulse.server._agg") as mock_agg:
            mock_agg.history = AsyncMock(side_effect=[
                {"records": [{"score": 95}]},
                {"records": [{"score": 40}]},
            ])
            result = _run(compare_trends("hot", "cold", days=7))
        data = json.loads(result)
        assert data["winner_by_score"] == "hot"


# ═══════════════════════════════════════════════════════
# compliance_agent — direct unit test
# ═══════════════════════════════════════════════════════

class TestComplianceAgent:
    def test_compliance_penalty_on_spam(self):
        from trend_pulse.core.agents.workflow import compliance_agent, ScoredDraft, WorkflowState
        draft = ScoredDraft(platform="threads", content="buy now! limited time act now", score=80.0, variant=0)
        state: WorkflowState = {"scored_drafts": [draft], "errors": []}
        result = _run(compliance_agent(state))
        penalized = result["scored_drafts"][0]
        assert penalized["score"] == 40.0  # 80 * 0.5
        assert len(result["errors"]) == 1

    def test_compliance_clean_draft_unchanged(self):
        from trend_pulse.core.agents.workflow import compliance_agent, ScoredDraft, WorkflowState
        draft = ScoredDraft(platform="threads", content="Why AI matters? Drop a comment 👇", score=72.0, variant=0)
        state: WorkflowState = {"scored_drafts": [draft], "errors": []}
        result = _run(compliance_agent(state))
        assert result["scored_drafts"][0]["score"] == 72.0
        assert len(result["errors"]) == 0
