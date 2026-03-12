"""ArXiv papers via public Atom API (free, no auth)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from .base import TrendSource, TrendItem

# Atom namespace
_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArXivSource(TrendSource):
    name = "arxiv"
    description = "ArXiv - latest AI/ML/NLP research papers"
    requires_auth = False
    rate_limit = "3 req/s"

    API_URL = "https://export.arxiv.org/api/query"

    def _parse_feed(self, xml_text: str) -> list[TrendItem]:
        root = ET.fromstring(xml_text)
        items: list[TrendItem] = []

        for entry in root.findall("atom:entry", _NS):
            title_el = entry.find("atom:title", _NS)
            title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""

            summary_el = entry.find("atom:summary", _NS)
            summary = summary_el.text.strip()[:200] if summary_el is not None and summary_el.text else ""

            published_el = entry.find("atom:published", _NS)
            published = published_el.text if published_el is not None and published_el.text else ""

            # Get the abstract page link
            url = ""
            for link in entry.findall("atom:link", _NS):
                if link.get("type") == "text/html":
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
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                self.API_URL,
                params={
                    "search_query": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": count,
                },
            )
            resp.raise_for_status()
            text = resp.text

        return self._parse_feed(text)[:count]

    async def search(self, query: str, geo: str = "") -> list[TrendItem]:
        async with httpx.AsyncClient(timeout=15) as client:
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
