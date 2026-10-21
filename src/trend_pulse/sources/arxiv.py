"""ArXiv papers via public Atom API (free, no auth).

Falls back to the official arXiv RSS/Atom listing when the export API is
throttled (429) or times out.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

from .base import TrendSource, TrendItem
from .. import __version__

# Atom namespace (+ Dublin Core, used by the RSS listing for authors)
_NS = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/"}


class ArXivSource(TrendSource):
    name = "arxiv"
    description = "ArXiv - latest AI/ML/NLP research papers"
    requires_auth = False
    rate_limit = "3 req/s"

    API_URL = "https://export.arxiv.org/api/query"
    LISTING_URL = "https://rss.arxiv.org/atom/cs.AI+cs.CL+cs.LG"
    HEADERS = {"User-Agent": f"trend-pulse/{__version__} (github.com/claude-world/trend-pulse)"}

    def _parse_feed(self, xml_text: str) -> list[TrendItem]:
        root = ET.fromstring(xml_text)
        items: list[TrendItem] = []

        for entry in root.findall("atom:entry", _NS):
            # The listing also announces replaced versions of older papers; skip them
            announce_type = entry.findtext("{http://arxiv.org/schemas/atom}announce_type", "")
            if announce_type.startswith("replace"):
                continue

            title_el = entry.find("atom:title", _NS)
            title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""

            summary_el = entry.find("atom:summary", _NS)
            summary = summary_el.text.strip() if summary_el is not None and summary_el.text else ""
            # Listing summaries start with "arXiv:<id> Announce Type: new Abstract: ..."
            summary = re.sub(r"^arXiv:\S+\s+Announce Type:\s*\S+\s*Abstract:\s*", "", summary)[:200]

            published_el = entry.find("atom:published", _NS)
            published = published_el.text if published_el is not None and published_el.text else ""

            # Get the abstract page link (the listing's only link has no type)
            url = ""
            for link in entry.findall("atom:link", _NS):
                if link.get("type") == "text/html":
                    url = link.get("href", "")
                    break
            if not url:
                for link in entry.findall("atom:link", _NS):
                    if link.get("type") is None and link.get("rel", "alternate") == "alternate":
                        url = link.get("href", "")
                        break
            if not url:
                id_el = entry.find("atom:id", _NS)
                url = id_el.text if id_el is not None and id_el.text else ""

            # Extract categories
            categories = [
                cat.get("term", "")
                for cat in entry.findall("atom:category", _NS)
            ]

            # Authors
            authors = []
            for author in entry.findall("atom:author", _NS):
                name_el = author.find("atom:name", _NS)
                if name_el is not None and name_el.text:
                    authors.append(name_el.text)
            if not authors:
                creators = entry.findtext("dc:creator", "", _NS)
                authors = [a.strip() for a in creators.split(",") if a.strip()]

            items.append(TrendItem(
                keyword=title,
                score=max(100 - len(items) * 5, 10),  # Rank-based score
                source=self.name,
                url=url,
                category="research",
                published=published,
                metadata={
                    "summary": summary,
                    "authors": authors[:5],
                    "categories": categories,
                },
            ))

        return items

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15, headers=self.HEADERS) as client:
            try:
                resp = await client.get(
                    self.API_URL,
                    params={
                        "search_query": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
                        "sortBy": "submittedDate",
                        "sortOrder": "descending",
                        "max_results": count,
                    },
                    timeout=5,  # A healthy API answers in under a second
                )
                resp.raise_for_status()
            except httpx.HTTPError:
                # Export API throttled or down: use today's official listing
                resp = await client.get(self.LISTING_URL, timeout=30)
                resp.raise_for_status()
            text = resp.text

        return self._parse_feed(text)[:count]

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15, headers=self.HEADERS) as client:
            resp = await client.get(
                self.API_URL,
                params={
                    "search_query": f"all:{query}",
                    "sortBy": "relevance",
                    "sortOrder": "descending",
                    "max_results": 20,
                },
            )
            resp.raise_for_status()
            text = resp.text

        return self._parse_feed(text)
