"""VectorStore abstract base — pluggable backend for semantic search."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ...sources.base import TrendItem


@dataclass
class SimilarityResult:
    """A TrendItem with its similarity score to a query."""
    item: TrendItem
    similarity: float  # 0.0 - 1.0


class VectorStore(ABC):
    """Abstract backend for storing and querying TrendItem vectors.

    Default implementation: SimpleVectorStore (pure Python TF-IDF, zero deps).
    Optional: QdrantVectorStore, ChromaVectorStore (install separately).
    """

    @abstractmethod
    async def upsert(self, items: list[TrendItem]) -> None:
        """Insert or update TrendItems in the vector store."""

    @abstractmethod
    async def search_similar(self, query: str, k: int = 10) -> list[SimilarityResult]:
        """Find the k most similar TrendItems to the query string."""

    @abstractmethod
    async def cluster(self, threshold: float = 0.3) -> list[list[TrendItem]]:
        """Group stored TrendItems into semantic clusters.

        Args:
            threshold: Minimum cosine similarity to be in the same cluster (0-1).
        """

    async def clear(self) -> None:
        """Remove all stored items. Override if backend needs explicit cleanup."""
