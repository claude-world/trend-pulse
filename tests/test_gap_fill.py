"""Tests for gap-fill items: 2 new plugins, 6 new MCP tools, LINE/Email channels."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch


def _run(coro):
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════
# New plugin sources — pinterest + linkedin_trending
# ═══════════════════════════════════════════════════════

class TestPluginSources37:
    def test_pinterest_registered(self):
        from trend_pulse.aggregator import TrendAggregator
        agg = TrendAggregator()
        assert "pinterest" in agg._instances

    def test_linkedin_trending_registered(self):
        from trend_pulse.aggregator import TrendAggregator
        agg = TrendAggregator()
        assert "linkedin_trending" in agg._instances

    def test_total_sources_37(self):
        from trend_pulse.aggregator import TrendAggregator
        agg = TrendAggregator()
        assert len(agg.list_sources()) >= 37

    def test_pinterest_graceful_error(self):
        from trend_pulse.plugins.sources.pinterest import PinterestSource
        src = PinterestSource()
        items = _run(src.fetch_trending(count=5))
        # Returns list (empty or with items) — never raises
        assert isinstance(items, list)

    def test_linkedin_trending_graceful_error(self):
        from trend_pulse.plugins.sources.linkedin_trending import LinkedInTrendingSource
        src = LinkedInTrendingSource()
        items = _run(src.fetch_trending(count=5))
        assert isinstance(items, list)


# ═══════════════════════════════════════════════════════
# New notification channels — LINE + Email
# ═══════════════════════════════════════════════════════

class TestNewNotificationChannels:
    def test_line_no_token_returns_false(self):
        from trend_pulse.notifications import LineNotify
        from trend_pulse.notifications.base import NotificationPayload
        ch = LineNotify(token="")
        result = _run(ch.send(NotificationPayload(title="t", message="m")))
        assert result is False

    def test_email_no_host_returns_false(self):
        from trend_pulse.notifications import EmailSMTP
        from trend_pulse.notifications.base import NotificationPayload
        ch = EmailSMTP(host="", user="", to_addr="")
        result = _run(ch.send(NotificationPayload(title="t", message="m")))
        assert result is False

    def test_all_5_channels_in_init(self):
        from trend_pulse.notifications import (
            DiscordWebhook, TelegramBot, GenericWebhook, LineNotify, EmailSMTP,
        )
        assert all(ch is not None for ch in (
            DiscordWebhook, TelegramBot, GenericWebhook, LineNotify, EmailSMTP,
        ))

    def test_send_notification_line_channel(self):
        from trend_pulse.server import send_notification
        result = _run(send_notification("line", "Alert", "Test"))
        data = json.loads(result)
        assert data["success"] is False  # No token configured
        assert data["channel"] == "line"

    def test_send_notification_email_channel(self):
        from trend_pulse.server import send_notification
        result = _run(send_notification("email", "Alert", "Test"))
        data = json.loads(result)
        assert data["success"] is False  # No SMTP configured
        assert data["channel"] == "email"


# ═══════════════════════════════════════════════════════
# 6 new MCP tools (29 total target)
# ═══════════════════════════════════════════════════════

class TestNewMCPTools29:
    def test_29_tools_registered(self):
        from trend_pulse.server import mcp
        tools = mcp._tool_manager._tools
        assert len(tools) >= 29

    def test_new_tools_present(self):
        from trend_pulse.server import mcp
        tools = mcp._tool_manager._tools
        new_tools = {
            "adapt_content", "analyze_viral_factors", "generate_hashtags",
            "get_source_status", "get_trend_velocity", "batch_score_content",
        }
        for name in new_tools:
            assert name in tools, f"Missing tool: {name}"

    def test_adapt_content_threads_to_x(self):
        from trend_pulse.server import adapt_content
        content = "This is a test post about AI trends that is fairly long and has a lot to say."
        result = _run(adapt_content(content, "threads", "x"))
        data = json.loads(result)
        assert data["to_platform"] == "x"
        assert len(data["adapted"]["content"]) <= 280
        assert "score" in data["adapted"]

    def test_adapt_content_to_linkedin(self):
        from trend_pulse.server import adapt_content
        result = _run(adapt_content("AI is transforming work.", "threads", "linkedin"))
        data = json.loads(result)
        assert len(data["adapted"]["content"]) <= 3000

    def test_analyze_viral_factors(self):
        from trend_pulse.server import analyze_viral_factors
        result = _run(analyze_viral_factors("Why AI matters? Comment below 👇", "threads"))
        data = json.loads(result)
        assert "signals" in data
        assert "overall" in data
        assert "top_suggestions" in data
        assert isinstance(data["signals"]["has_question"], bool)

    def test_generate_hashtags_en(self):
        from trend_pulse.server import generate_hashtags
        result = _run(generate_hashtags("AI agents", "threads", 8, "en"))
        data = json.loads(result)
        assert len(data["hashtags"]) <= 8
        assert all(t.startswith("#") for t in data["hashtags"])
        assert "platform_advice" in data

    def test_generate_hashtags_zh(self):
        from trend_pulse.server import generate_hashtags
        result = _run(generate_hashtags("人工智慧", "xiaohongshu", 10, "zh-TW"))
        data = json.loads(result)
        assert len(data["hashtags"]) >= 1

    def test_get_source_status(self):
        from trend_pulse.server import get_source_status
        result = _run(get_source_status())
        data = json.loads(result)
        assert "checked" in data
        assert "summary" in data
        assert "sources" in data
        assert data["checked"] > 0

    def test_get_trend_velocity_no_history(self):
        from trend_pulse.server import get_trend_velocity
        with patch("trend_pulse.server._agg") as mock_agg:
            mock_agg.history = AsyncMock(return_value={"records": []})
            result = _run(get_trend_velocity("nonexistent_keyword_xyz", 24))
        data = json.loads(result)
        assert data["velocity"] == 0.0
        assert data["current_score"] == 0.0

    def test_get_trend_velocity_with_history(self):
        from trend_pulse.server import get_trend_velocity
        # history() returns newest-first (DESC) — code reverses to oldest-first before velocity calc
        records = [{"score": s} for s in [70, 50, 35, 20, 10]]
        with patch("trend_pulse.server._agg") as mock_agg:
            mock_agg.history = AsyncMock(return_value={"records": records})
            result = _run(get_trend_velocity("python", 24))
        data = json.loads(result)
        assert data["velocity"] > 0  # Rising trend
        assert data["trend_direction"] == "rising"
        assert "projection_24h" in data

    def test_batch_score_content(self):
        from trend_pulse.server import batch_score_content
        posts = json.dumps([
            "Why AI matters? 🤔 Drop a comment!",
            "hello",
            "This is a longer post about AI trends with multiple sentences and good structure. What do you think?",
        ])
        result = _run(batch_score_content(posts, "threads"))
        data = json.loads(result)
        assert data["count"] == 3
        assert len(data["results"]) == 3
        assert data["results"][0]["rank"] == 1  # Best first
        assert "best_index" in data

    def test_batch_score_content_invalid_json(self):
        from trend_pulse.server import batch_score_content
        result = _run(batch_score_content("not json", "threads"))
        data = json.loads(result)
        assert "error" in data

    def test_batch_score_content_not_array(self):
        from trend_pulse.server import batch_score_content
        result = _run(batch_score_content('{"key": "value"}', "threads"))
        data = json.loads(result)
        assert "error" in data


# ═══════════════════════════════════════════════════════
# Dashboard API module importable
# ═══════════════════════════════════════════════════════

class TestAggregatorKeyContract:
    """Regression: aggregator must return 'merged' and 'sources' keys (dashboard depends on them)."""

    def test_trending_returns_merged_key(self):
        import asyncio
        from unittest.mock import AsyncMock, patch
        from trend_pulse.aggregator import TrendAggregator
        agg = TrendAggregator(include_plugins=False)

        with patch.object(agg, "_select") as mock_select:
            mock_src = AsyncMock()
            mock_src.fetch_trending = AsyncMock(return_value=[])
            mock_select.return_value = {"test_src": mock_src}
            result = asyncio.run(agg.trending())

        assert "merged" in result, f"Expected 'merged' key, got: {list(result.keys())}"
        assert "sources" in result, f"Expected 'sources' key, got: {list(result.keys())}"
        assert "merged_top" not in result, "Old key 'merged_top' must not appear"
        assert "by_source" not in result, "Old key 'by_source' must not appear"

    def test_search_returns_merged_key(self):
        import asyncio
        from trend_pulse.aggregator import TrendAggregator
        agg = TrendAggregator(include_plugins=False)
        # Use a real aggregator with no sources selected — still validates key contract
        result = asyncio.run(agg.search(query="nonexistent_xyz_abc_123", sources=["hackernews"]))
        assert "merged" in result
        assert "sources" in result


class TestDashboardAPI:
    def test_api_module_importable(self):
        # FastAPI may or may not be installed; either way the module should import
        import trend_pulse.dashboard.api  # noqa: F401

    def test_pages_importable(self):
        import trend_pulse.dashboard.pages.realtime  # noqa: F401
        import trend_pulse.dashboard.pages.clusters  # noqa: F401
        import trend_pulse.dashboard.pages.campaign  # noqa: F401
        import trend_pulse.dashboard.pages.history   # noqa: F401
