"""Tests for server.py — MCP tool registration and integration."""

import json
import asyncio

import pytest

from trend_pulse.server import mcp


def _tool_names() -> set[str]:
    return {tool.name for tool in asyncio.run(mcp.list_tools())}


class TestServerTools:
    """Test that the MCP tools are registered with correct signatures."""

    def test_total_tool_count(self):
        tools = _tool_names()
        assert len(tools) >= 29  # 29 tools as of v2.0

    def test_data_tools_present(self):
        tools = _tool_names()
        for name in ("get_trending", "search_trends", "list_sources",
                      "get_trend_history", "take_snapshot"):
            assert name in tools, f"Missing data tool: {name}"

    def test_guide_tools_present(self):
        tools = _tool_names()
        for name in ("get_content_brief", "get_scoring_guide", "get_platform_specs",
                      "get_review_checklist", "get_reel_guide"):
            assert name in tools, f"Missing guide tool: {name}"

    def test_removed_tools_not_present(self):
        tools = _tool_names()
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
        # Phase 2 expanded to 8 platforms
        assert {"threads", "instagram", "facebook"} <= set(data.keys())

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


class TestBrowserTool:
    """Test render_page tool registration."""

    def test_render_page_tool_present(self):
        tools = _tool_names()
        assert "render_page" in tools, "Missing browser tool: render_page"


class TestMCPProtocol:
    """Exercise the server end to end through the in-memory MCP client."""

    def test_initialize_list_and_call_tool(self):
        from mcp.client import Client

        from trend_pulse import __version__

        async def session():
            async with Client(mcp) as client:
                listed = await client.list_tools()
                result = await client.call_tool(
                    "get_platform_specs", {"platform": "threads", "lang": "en"}
                )
                return client.server_info, listed, result

        server_info, listed, result = asyncio.run(session())
        assert server_info.name == "trend-pulse"
        assert server_info.version == __version__
        assert {t.name for t in listed.tools} == _tool_names()
        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert data["platform"] == "threads"
        assert data["max_chars"] == 500


class TestServerMain:
    """trend-pulse-server picks the transport from its command-line flags."""

    def test_default_is_stdio(self):
        from unittest.mock import patch

        from trend_pulse import server

        with patch.object(server.mcp, "run") as run, patch("sys.argv", ["trend-pulse-server"]):
            server.main()
        run.assert_called_once_with()

    def test_streamable_http(self):
        from unittest.mock import patch

        from trend_pulse import server

        argv = ["trend-pulse-server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9000"]
        with patch.object(server.mcp, "run") as run, patch("sys.argv", argv):
            server.main()
        run.assert_called_once_with(transport="streamable-http", host="0.0.0.0", port=9000)


class TestVersion:
    def test_version_is_v2(self):
        from trend_pulse import __version__
        from packaging.version import Version
        assert Version(__version__) >= Version("2.0.0")


class TestSSRFGuard:
    """Verify render_page SSRF guard blocks dangerous URLs."""

    def _run(self, coro):
        return asyncio.run(coro)

    @pytest.mark.parametrize("url,expected_error", [
        ("file:///etc/passwd", "Unsupported URL scheme"),
        ("ftp://example.com/", "Unsupported URL scheme"),
        ("http://192.168.1.1/", "Blocked: private/loopback"),
        ("http://127.0.0.1:8080/", "Blocked: private/loopback"),
        ("http://10.0.0.1/secret", "Blocked: private/loopback"),
    ])
    def test_render_page_ssrf_guard(self, url, expected_error):
        from trend_pulse.server import render_page
        result = self._run(render_page(url))
        data = json.loads(result)
        assert "error" in data
        assert expected_error in data["error"]
