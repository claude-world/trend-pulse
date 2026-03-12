"""Cloudflare Browser Rendering — optional fallback renderer.

Renders JS-heavy pages via Cloudflare's managed headless Chrome service.
Requires CF_ACCOUNT_ID and CF_API_TOKEN environment variables.

Usage:
    from trend_pulse.sources.browser_renderer import render_markdown, extract_json

    # Render a JS page to clean Markdown
    md = await render_markdown("https://github.com/trending")

    # AI-powered structured extraction
    data = await extract_json(
        "https://news.ycombinator.com",
        "Extract top 10 article titles with their point counts"
    )

REST API docs: https://developers.cloudflare.com/browser-rendering/rest-api/
"""

from __future__ import annotations

import os

import httpx

CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "")
CF_API_TOKEN = os.environ.get("CF_API_TOKEN", "")


def _base_url() -> str:
    """Build base URL, reading env vars at call time (testable)."""
    account_id = os.environ.get("CF_ACCOUNT_ID", "") or CF_ACCOUNT_ID
    return f"https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering"


def _headers() -> dict[str, str]:
    """Auth headers, reading env vars at call time (testable)."""
    token = os.environ.get("CF_API_TOKEN", "") or CF_API_TOKEN
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def is_available() -> bool:
    """Check if CF Browser Rendering credentials are configured."""
    return bool(
        os.environ.get("CF_ACCOUNT_ID", "") or CF_ACCOUNT_ID
    ) and bool(
        os.environ.get("CF_API_TOKEN", "") or CF_API_TOKEN
    )


async def render_markdown(url: str, *, timeout: float = 30) -> str:
    """Render a JS-heavy page to clean Markdown via CF Browser Rendering.

    Args:
        url: The page URL to render.
        timeout: Request timeout in seconds (default: 30).

    Returns:
        Markdown text of the rendered page.

    Raises:
        RuntimeError: If CF credentials are not configured.
        httpx.HTTPStatusError: If the API call fails.
    """
    if not is_available():
        raise RuntimeError(
            "CF Browser Rendering not configured. "
            "Set CF_ACCOUNT_ID and CF_API_TOKEN environment variables."
        )

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{_base_url()}/markdown",
            headers=_headers(),
            json={"url": url},
        )
        resp.raise_for_status()
        data = resp.json()

    # REST API returns {"success": true, "result": "...markdown..."}
    if isinstance(data.get("result"), str):
        return data["result"]
    # Some endpoints nest under result.markdown
    if isinstance(data.get("result"), dict):
        return data["result"].get("markdown", "")
    return ""


async def render_content(url: str, *, timeout: float = 30) -> str:
    """Render a JS-heavy page and return full HTML via CF Browser Rendering.

    Args:
        url: The page URL to render.
        timeout: Request timeout in seconds (default: 30).

    Returns:
        Full rendered HTML string.

    Raises:
        RuntimeError: If CF credentials are not configured.
        httpx.HTTPStatusError: If the API call fails.
    """
    if not is_available():
        raise RuntimeError(
            "CF Browser Rendering not configured. "
            "Set CF_ACCOUNT_ID and CF_API_TOKEN environment variables."
        )

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{_base_url()}/content",
            headers=_headers(),
            json={"url": url},
        )
        resp.raise_for_status()
        data = resp.json()

    if isinstance(data.get("result"), str):
        return data["result"]
    if isinstance(data.get("result"), dict):
        return data["result"].get("html", "")
    return ""


async def extract_json(url: str, prompt: str, *, timeout: float = 30) -> dict:
    """AI-powered structured extraction from a webpage.

    Uses CF Workers AI to extract structured data based on a natural language
    prompt. The model processes the rendered page and returns JSON matching
    the requested schema.

    Args:
        url: The page URL to extract data from.
        prompt: Natural language description of data to extract.
        timeout: Request timeout in seconds (default: 30).

    Returns:
        Extracted data as a dict.

    Raises:
        RuntimeError: If CF credentials are not configured.
        httpx.HTTPStatusError: If the API call fails.
    """
    if not is_available():
        raise RuntimeError(
            "CF Browser Rendering not configured. "
            "Set CF_ACCOUNT_ID and CF_API_TOKEN environment variables."
        )

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{_base_url()}/json",
            headers=_headers(),
            json={"url": url, "prompt": prompt},
        )
        resp.raise_for_status()
        data = resp.json()

    if isinstance(data.get("result"), dict):
        return data["result"]
    return data.get("result", {})
