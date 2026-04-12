"""SimpleVectorStore — pure Python TF-IDF cosine similarity, zero external deps.

Suitable for single-session use or small corpora (< 10K items).
For production scale, swap in QdrantVectorStore or ChromaVectorStore.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict

from ...sources.base import TrendItem
from .base import SimilarityResult, VectorStore


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer, handles CJK chars."""
    text = text.lower()
    # Split on non-alphanum (keep CJK as single chars)
    tokens = re.findall(r"[\w\u4e00-\u9fff\u3040-\u30ff\u1100-\u11ff]+", text)
    return [t for t in tokens if len(t) >= 2]


def _tf(tokens: list[str]) -> dict[str, float]:
    """Term frequency (normalized)."""
    freq: dict[str, int] = defaultdict(int)
    for t in tokens:
        freq[t] += 1
    n = max(len(tokens), 1)
    return {t: c / n for t, c in freq.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity between two TF-IDF vectors."""
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SimpleVectorStore(VectorStore):
    """In-memory TF-IDF vector store. Thread-safe for async read-only access.

    IDF is computed lazily when the corpus changes. Suitable for < 50K items.
    """

    def __init__(self) -> None:
        self._items: list[TrendItem] = []
        self._tfs: list[dict[str, float]] = []   # TF per item
        self._idf: dict[str, float] = {}          # IDF over corpus
        self._dirty: bool = False                  # Recompute IDF on next query

    async def upsert(self, items: list[TrendItem]) -> None:
        """Add items; deduplicates by keyword+source."""
        existing = {(i.keyword, i.source) for i in self._items}
        new = [i for i in items if (i.keyword, i.source) not in existing]
        for item in new:
            tokens = _tokenize(self._text(item))
            self._items.append(item)
            self._tfs.append(_tf(tokens))
        if new:
            self._dirty = True

    async def search_similar(self, query: str, k: int = 10) -> list[SimilarityResult]:
        self._maybe_recompute_idf()
        q_tf = _tf(_tokenize(query))
        q_tfidf = {t: q_tf[t] * self._idf.get(t, 0) for t in q_tf}

        scored: list[tuple[float, TrendItem]] = []
        for item, tf in zip(self._items, self._tfs):
            tfidf = {t: tf[t] * self._idf.get(t, 0) for t in tf}
            sim = _cosine(q_tfidf, tfidf)
            if sim > 0:
                scored.append((sim, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [SimilarityResult(item=item, similarity=sim) for sim, item in scored[:k]]

    async def cluster(self, threshold: float = 0.3) -> list[list[TrendItem]]:
        """Single-pass greedy clustering by cosine similarity.

        The inner loop is O(n²) synchronous CPU work. Items are passed to a
        thread executor to avoid blocking the asyncio event loop.
        """
        import asyncio
        self._maybe_recompute_idf()
        if not self._items:
            return []

        # Snapshot state for the executor (avoid closure over mutable self)
        items = list(self._items)
        tfs = list(self._tfs)
        idf = dict(self._idf)

        def _cluster_sync() -> list[list[TrendItem]]:
            vecs = [{t: tf[t] * idf.get(t, 0) for t in tf} for tf in tfs]
            n = len(items)
            assigned = [-1] * n
            clusters: list[list[int]] = []

            for i in range(n):
                if assigned[i] != -1:
                    continue
                cluster_idx = len(clusters)
                clusters.append([i])
                assigned[i] = cluster_idx
                for j in range(i + 1, n):
                    if assigned[j] != -1:
                        continue
                    if _cosine(vecs[i], vecs[j]) >= threshold:
                        clusters[cluster_idx].append(j)
                        assigned[j] = cluster_idx

            return [[items[idx] for idx in cluster] for cluster in clusters]

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _cluster_sync)

    async def clear(self) -> None:
        self._items.clear()
        self._tfs.clear()
        self._idf.clear()
        self._dirty = False

    def _text(self, item: TrendItem) -> str:
        """Concatenate keyword + category for richer tokenization."""
        parts = [item.keyword, item.category or ""]
        # Add URL domain as a weak signal
        if item.url:
            m = re.search(r"//([^/]+)", item.url)
            if m:
                parts.append(m.group(1))
        return " ".join(parts)

    def _maybe_recompute_idf(self) -> None:
        if not self._dirty:
            return
        n = len(self._tfs)
        if n == 0:
            return

        # Document frequency
        df: dict[str, int] = defaultdict(int)
        for tf in self._tfs:
            for term in tf:
                df[term] += 1

        # IDF: log((N + 1) / (df + 1)) + 1  (smooth, avoids zero)
        self._idf = {
            term: math.log((n + 1) / (count + 1)) + 1
            for term, count in df.items()
        }
        self._dirty = False
