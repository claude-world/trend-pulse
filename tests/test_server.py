"""Tests for server.py — MCP tool registration and integration."""

import json
import pytest
import asyncio

from trend_pulse.server import mcp


class TestServerTools:
    """Test that all 10 MCP tools are registered with correct signatures."""

    def test_total_tool_count(self):
        tools = mcp._tool_manager._tools
        assert len(tools) == 10

    def test_original_5_tools_present(self):
        tools = mcp._tool_manager._tools
        for name in ("get_trending", "search_trends", "list_sources",
                      "get_trend_history", "take_snapshot"):
            assert name in tools, f"Missing original tool: {name}"

    def test_new_5_tools_present(self):
        tools = mcp._tool_manager._tools
        for name in ("generate_viral_posts", "score_viral_post", "generate_content",
                      "review_content", "generate_reel_script"):
            assert name in tools, f"Missing new tool: {name}"

    def test_no_publish_tools(self):
        tools = mcp._tool_manager._tools
        for name in ("publish_threads", "publish_instagram", "publish_all"):
            assert name not in tools, f"Publish tool should be removed: {name}"


class TestServerToolExecution:
    """Test tool execution returns valid JSON."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_generate_viral_posts(self):
        from trend_pulse.server import generate_viral_posts
        result = self._run(generate_viral_posts("AI", "debate", 2))
        data = json.loads(result)
        assert data["topic"] == "AI"
        assert data["count"] == 2
        assert len(data["posts"]) == 2

    def test_score_viral_post(self):
        from trend_pulse.server import score_viral_post
        result = self._run(score_viral_post("AI 面試的真相，你知道嗎？"))
        data = json.loads(result)
        assert "overall" in data
        assert "grade" in data
        assert "dimensions" in data
        assert "text_preview" in data

    def test_generate_content(self):
        from trend_pulse.server import generate_content
        result = self._run(generate_content("AI", "opinion", 1))
        data = json.loads(result)
        assert data["total_packages"] == 1
        assert "packages" in data
        pkg = data["packages"][0]
        assert set(pkg["platforms"].keys()) == {"threads", "instagram", "facebook"}

    def test_review_content(self):
        from trend_pulse.server import review_content
        result = self._run(review_content("短文", "threads", False))
        data = json.loads(result)
        assert "verdict" in data
        assert "scores" in data
        assert "issues" in data
        assert data["platform"] == "threads"

    def test_review_content_auto_fix(self):
        from trend_pulse.server import review_content
        result = self._run(review_content("短文", "threads", True))
        data = json.loads(result)
        assert "verdict" in data
        # auto_fix should produce fixed_text for a short post
        if data.get("fixed_text"):
            assert len(data["fixed_text"]) > len("短文")

    def test_generate_reel_script(self):
        from trend_pulse.server import generate_reel_script
        result = self._run(generate_reel_script("AI", "educational", 30))
        data = json.loads(result)
        assert "scenes" in data
        assert len(data["scenes"]) >= 4
        assert data["duration_seconds"] == 30


class TestVersion:
    def test_version_is_030(self):
        from trend_pulse import __version__
        assert __version__ == "0.3.0"
