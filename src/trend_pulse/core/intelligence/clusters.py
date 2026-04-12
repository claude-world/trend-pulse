"""Trend Knowledge Graph clustering — group TrendItems into cross-source topics."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...sources.base import TrendItem
from ..vector.simple import SimpleVectorStore


@dataclass
class TrendCluster:
    """A group of semantically related TrendItems from multiple sources."""

    topic: str              # Representative keyword (highest-scoring item)
    items: list[TrendItem]  # All items in the cluster
    score: float = 0.0      # Average score (0-100)
    sources: list[str] = field(default_factory=list)    # Unique source names
    keywords: list[str] = field(default_factory=list)   # All unique keywords
    cross_source: bool = False  # True if items come from 2+ distinct sources

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "score": round(self.score, 2),
            "cross_source": self.cross_source,
            "sources": self.sources,
            "keywords": self.keywords[:10],
            "item_count": len(self.items),
            "items": [it.to_dict() for it in self.items],
        }


async def cluster_trends(
    items: list[TrendItem],
    threshold: float = 0.25,
    min_cluster_size: int = 1,
    max_items: int = 500,
) -> list[TrendCluster]:
    """Cluster TrendItems into semantic topic groups.

    Args:
        items: TrendItems to cluster (can be from multiple sources).
        threshold: Cosine similarity threshold for same-cluster assignment (0-1).
                   Lower = more inclusive clusters.
        min_cluster_size: Minimum items per cluster to include in output.
        max_items: Cap on items to cluster (default 500). The algorithm is O(n²),
                   so large corpora must be pre-truncated. Items are sorted by score
                   descending before truncation to preserve the most relevant ones.

    Returns:
        List of TrendClusters sorted by score descending.
    """
    if not items:
        return []

    # Guard O(n²) clustering — truncate to highest-scoring items
    if len(items) > max_items:
        items = sorted(items, key=lambda x: x.score, reverse=True)[:max_items]

    store = SimpleVectorStore()
    await store.upsert(items)
    raw_clusters = await store.cluster(threshold=threshold)

    clusters: list[TrendCluster] = []
    for raw in raw_clusters:
        if len(raw) < min_cluster_size:
            continue

        # Sort by score descending within cluster
        raw_sorted = sorted(raw, key=lambda x: x.score, reverse=True)
        top = raw_sorted[0]

        unique_sources = list(dict.fromkeys(it.source for it in raw))
        unique_keywords = list(dict.fromkeys(it.keyword for it in raw_sorted))
        avg_score = sum(it.score for it in raw) / len(raw)

        clusters.append(TrendCluster(
            topic=top.keyword,
            items=raw_sorted,
            score=avg_score,
            sources=unique_sources,
            keywords=unique_keywords,
            cross_source=len(unique_sources) >= 2,
        ))

    clusters.sort(key=lambda c: (c.cross_source, c.score), reverse=True)
    return clusters
