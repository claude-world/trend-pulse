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

    def test_data_tools_present(self):
        tools = mcp._tool_manager._tools
        for name in ("get_trending", "search_trends", "list_sources",
                      "get_trend_history", "take_snapshot"):
            assert name in tools, f"Missing data tool: {name}"

    def test_guide_tools_present(self):
        tools = mcp._tool_manager._tools
        for name in ("get_content_brief", "get_scoring_guide", "get_platform_specs",
                      "get_review_checklist", "get_reel_guide"):
            assert name in tools, f"Missing guide tool: {name}"

    def test_removed_tools_not_present(self):
        tools = mcp._tool_manager._tools
        for name in ("generate_viral_posts", "score_viral_post", "generate_content",
                      "score_post", "review_content", "generate_reel_script"):
            assert name not in tools, f"Tool should be removed: {name}"


class TestServerToolExecution:
    """Test tool execution returns valid JSON."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_get_content_brief(self):
        from trend_pulse.server import get_content_brief
        result = self._run(get_content_brief("AI tools", "debate", "threads"))
        data = json.loads(result)
        assert data["topic"] == "AI tools"
        assert data["content_type"] == "debate"
        assert data["language"] == "en"
        assert len(data["hook_examples"]) > 0
        assert data["char_limit"] == 500

    def test_get_content_brief_zh(self):
        from trend_pulse.server import get_content_brief
        result = self._run(get_content_brief("AI工具", "debate", "threads"))
        data = json.loads(result)
        assert data["language"] == "zh-TW"

    def test_get_scoring_guide(self):
        from trend_pulse.server import get_scoring_guide
        result = self._run(get_scoring_guide("en"))
        data = json.loads(result)
        assert "dimensions" in data
        assert len(data["dimensions"]) == 5
        assert "grade_thresholds" in data
        assert "instructions" in data

    def test_get_scoring_guide_zh(self):
        from trend_pulse.server import get_scoring_guide
        result = self._run(get_scoring_guide("zh-TW"))
        data = json.loads(result)
        dims = data["dimensions"]
        # Should contain Chinese text
        assert "注意力" in dims["hook_power"]["description"]

    def test_get_platform_specs_single(self):
        from trend_pulse.server import get_platform_specs
        result = self._run(get_platform_specs("threads", "en"))
        data = json.loads(result)
        assert data["platform"] == "threads"
        assert data["max_chars"] == 500

    def test_get_platform_specs_all(self):
        from trend_pulse.server import get_platform_specs
        result = self._run(get_platform_specs("", "zh-TW"))
        data = json.loads(result)
        assert set(data.keys()) == {"threads", "instagram", "facebook"}

    def test_get_review_checklist(self):
        from trend_pulse.server import get_review_checklist
        result = self._run(get_review_checklist("threads", "en"))
        data = json.loads(result)
        assert data["platform"] == "threads"
        assert data["char_limit"] == 500
        assert len(data["checklist"]) >= 7
        assert "instructions" in data

    def test_get_review_checklist_zh(self):
        from trend_pulse.server import get_review_checklist
        result = self._run(get_review_checklist("threads", "zh-TW"))
        data = json.loads(result)
        # Chinese checklist
        assert "字" in data["checklist"][0]["check"]

    def test_get_reel_guide(self):
        from trend_pulse.server import get_reel_guide
        result = self._run(get_reel_guide("educational", 30, "en"))
        data = json.loads(result)
        assert data["style"] == "educational"
        assert data["target_duration"] == 30
        assert len(data["scene_structure"]) >= 4
        assert "instructions" in data

    def test_get_reel_guide_storytelling(self):
        from trend_pulse.server import get_reel_guide
        result = self._run(get_reel_guide("storytelling", 30, "en"))
        data = json.loads(result)
        assert data["style"] == "storytelling"
        scene_types = [s["type"] for s in data["scene_structure"]]
        assert "HOOK" in scene_types
        assert "CONFLICT" in scene_types

    def test_get_reel_guide_listicle(self):
        from trend_pulse.server import get_reel_guide
        result = self._run(get_reel_guide("listicle", 30, "en"))
        data = json.loads(result)
        assert data["style"] == "listicle"


class TestVersion:
    def test_version_is_032(self):
        from trend_pulse import __version__
        assert __version__ == "0.3.2"
