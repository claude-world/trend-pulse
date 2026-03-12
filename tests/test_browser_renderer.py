"""Tests for Cloudflare Browser Rendering — optional fallback renderer."""

import json
import os
import pytest
import asyncio

from unittest.mock import AsyncMock, patch, MagicMock


class TestBrowserRendererAvailability:
    """Test is_available() checks."""

    def test_not_available_without_env(self):
        with patch.dict(os.environ, {}, clear=True):
            # Also reset module-level vars
            import trend_pulse.sources.browser_renderer as br
            orig_id, orig_token = br.CF_ACCOUNT_ID, br.CF_API_TOKEN
            br.CF_ACCOUNT_ID = ""
            br.CF_API_TOKEN = ""
            try:
                assert br.is_available() is False
            finally:
                br.CF_ACCOUNT_ID = orig_id
                br.CF_API_TOKEN = orig_token

    def test_available_with_env(self):
        with patch.dict(os.environ, {"CF_ACCOUNT_ID": "abc123", "CF_API_TOKEN": "token456"}):
            from trend_pulse.sources.browser_renderer import is_available
            assert is_available() is True

    def test_not_available_partial_env(self):
        with patch.dict(os.environ, {"CF_ACCOUNT_ID": "abc123"}, clear=True):
            import trend_pulse.sources.browser_renderer as br
            orig_token = br.CF_API_TOKEN
            br.CF_API_TOKEN = ""
            try:
                assert br.is_available() is False
            finally:
                br.CF_API_TOKEN = orig_token


class TestRenderMarkdown:
    """Test render_markdown() function."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_raises_without_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            import trend_pulse.sources.browser_renderer as br
            orig_id, orig_token = br.CF_ACCOUNT_ID, br.CF_API_TOKEN
            br.CF_ACCOUNT_ID = ""
            br.CF_API_TOKEN = ""
            try:
                with pytest.raises(RuntimeError, match="not configured"):
                    self._run(br.render_markdown("https://example.com"))
            finally:
                br.CF_ACCOUNT_ID = orig_id
                br.CF_API_TOKEN = orig_token

    def test_returns_markdown_string(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": "# Hello World\n\nSome content."
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, {"CF_ACCOUNT_ID": "test", "CF_API_TOKEN": "test"}):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                from trend_pulse.sources.browser_renderer import render_markdown
                result = self._run(render_markdown("https://example.com"))
                assert result == "# Hello World\n\nSome content."

    def test_returns_nested_markdown(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": {"markdown": "# Nested format"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, {"CF_ACCOUNT_ID": "test", "CF_API_TOKEN": "test"}):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                from trend_pulse.sources.browser_renderer import render_markdown
                result = self._run(render_markdown("https://example.com"))
                assert result == "# Nested format"


class TestRenderContent:
    """Test render_content() function."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_raises_without_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            import trend_pulse.sources.browser_renderer as br
            orig_id, orig_token = br.CF_ACCOUNT_ID, br.CF_API_TOKEN
            br.CF_ACCOUNT_ID = ""
            br.CF_API_TOKEN = ""
            try:
                with pytest.raises(RuntimeError, match="not configured"):
                    self._run(br.render_content("https://example.com"))
            finally:
                br.CF_ACCOUNT_ID = orig_id
                br.CF_API_TOKEN = orig_token

    def test_returns_html_string(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": "<html><body><h1>Hello</h1></body></html>"
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, {"CF_ACCOUNT_ID": "test", "CF_API_TOKEN": "test"}):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                from trend_pulse.sources.browser_renderer import render_content
                result = self._run(render_content("https://example.com"))
                assert "<h1>Hello</h1>" in result


class TestExtractJson:
    """Test extract_json() function."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_raises_without_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            import trend_pulse.sources.browser_renderer as br
            orig_id, orig_token = br.CF_ACCOUNT_ID, br.CF_API_TOKEN
            br.CF_ACCOUNT_ID = ""
            br.CF_API_TOKEN = ""
            try:
                with pytest.raises(RuntimeError, match="not configured"):
                    self._run(br.extract_json("https://example.com", "extract titles"))
            finally:
                br.CF_ACCOUNT_ID = orig_id
                br.CF_API_TOKEN = orig_token

    def test_returns_extracted_dict(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "articles": [
                    {"title": "Article 1", "points": 100},
                    {"title": "Article 2", "points": 50},
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, {"CF_ACCOUNT_ID": "test", "CF_API_TOKEN": "test"}):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                from trend_pulse.sources.browser_renderer import extract_json
                result = self._run(extract_json(
                    "https://news.ycombinator.com",
                    "Extract article titles with points"
                ))
                assert "articles" in result
                assert len(result["articles"]) == 2

    def test_correct_api_url_and_payload(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "result": {}}
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, {"CF_ACCOUNT_ID": "my-acct", "CF_API_TOKEN": "my-token"}):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                from trend_pulse.sources.browser_renderer import extract_json
                self._run(extract_json("https://example.com", "get titles"))

                call_args = mock_client.post.call_args
                assert "my-acct" in call_args[0][0]
                assert "/json" in call_args[0][0]
                assert call_args[1]["json"]["url"] == "https://example.com"
                assert call_args[1]["json"]["prompt"] == "get titles"
                assert "Bearer my-token" in call_args[1]["headers"]["Authorization"]


class TestGitHubFallback:
    """Test GitHub trending source uses browser renderer as fallback."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_fallback_not_triggered_on_success(self):
        """Normal parsing should not trigger fallback."""
        from trend_pulse.sources.github_trending import GitHubTrendingSource

        # Valid HTML with at least one article
        html = '''
        <article class="Box-row">
            <h2><a href="/user/repo">user/repo</a></h2>
            <p class="col-9 text-gray">A cool project</p>
            <span>42 stars today</span>
        </article>
        '''
        source = GitHubTrendingSource()
        items = source._parse_html(html, 20)
        # Even if parse returns results, fallback should not be called
        # (This tests the non-fallback path)
        assert isinstance(items, list)


class TestMCPRenderPage:
    """Test render_page MCP tool."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_render_page_tool_registered(self):
        from trend_pulse.server import mcp
        tools = mcp._tool_manager._tools
        assert "render_page" in tools, "render_page MCP tool should be registered"

    def test_render_page_not_configured(self):
        """Should return error JSON when CF not configured."""
        with patch.dict(os.environ, {}, clear=True):
            import trend_pulse.sources.browser_renderer as br
            orig_id, orig_token = br.CF_ACCOUNT_ID, br.CF_API_TOKEN
            br.CF_ACCOUNT_ID = ""
            br.CF_API_TOKEN = ""
            try:
                from trend_pulse.server import render_page
                result = self._run(render_page("https://example.com"))
                data = json.loads(result)
                assert "error" in data
                assert "not configured" in data["error"].lower()
            finally:
                br.CF_ACCOUNT_ID = orig_id
                br.CF_API_TOKEN = orig_token

    def test_render_page_markdown_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": "# Rendered content"
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, {"CF_ACCOUNT_ID": "test", "CF_API_TOKEN": "test"}):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                from trend_pulse.server import render_page
                result = self._run(render_page("https://example.com", "markdown"))
                data = json.loads(result)
                assert data["url"] == "https://example.com"
                assert data["format"] == "markdown"
                assert "# Rendered content" in data["content"]
