"""Trend Intelligence — clustering and lifecycle prediction."""

from .clusters import TrendCluster, cluster_trends
from .lifecycle import LifecycleStage, predict_lifecycle

__all__ = ["TrendCluster", "cluster_trends", "LifecycleStage", "predict_lifecycle"]
