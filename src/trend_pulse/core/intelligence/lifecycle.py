"""Trend lifecycle prediction — emerging / peak / declining / fading."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...sources.base import TrendItem


class LifecycleStage(str, Enum):
    """Four-stage trend lifecycle model."""
    EMERGING = "emerging"    # Score rising fast, relatively new
    PEAK = "peak"            # Highest scores, velocity slowing
    DECLINING = "declining"  # Score falling, still in top N
    FADING = "fading"        # Very low score / velocity near zero


def predict_lifecycle(
    current_score: float,
    history: list[dict],
    window: int = 7,
) -> LifecycleStage:
    """Predict the lifecycle stage of a trend from its score history.

    Args:
        current_score: Current trend score (0-100).
        history: List of historical records (dicts with "score" key), oldest first.
                 At minimum, each record needs a "score" key.
        window: Number of recent records to consider for velocity / acceleration.

    Returns:
        LifecycleStage enum value.

    Algorithm:
        1. Extract scores from the last ``window`` records + current.
        2. Compute velocity  = mean delta over the window (positive = rising).
        3. Compute acceleration = delta of velocity in first-vs-second half.
        4. Map (velocity, acceleration, current_score) to a stage.
    """
    # Build score series
    scores = [r["score"] for r in history if "score" in r]
    scores.append(current_score)

    if len(scores) < 2:
        # Not enough history — use absolute score heuristic
        if current_score >= 70:
            return LifecycleStage.PEAK
        if current_score >= 40:
            return LifecycleStage.EMERGING
        if current_score >= 15:
            return LifecycleStage.DECLINING
        return LifecycleStage.FADING

    # Use last ``window`` points
    recent = scores[-window:]
    n = len(recent)

    # Velocity: average change per step
    deltas = [recent[i + 1] - recent[i] for i in range(n - 1)]
    velocity = sum(deltas) / len(deltas) if deltas else 0.0

    # Acceleration: velocity of second half minus velocity of first half
    mid = max(1, len(deltas) // 2)
    first_v = sum(deltas[:mid]) / mid if deltas[:mid] else 0.0
    second_v = sum(deltas[mid:]) / max(len(deltas[mid:]), 1) if deltas[mid:] else 0.0
    acceleration = second_v - first_v

    # Peak score in the window
    peak = max(recent)

    # Stage assignment rules (thresholds tuned empirically)
    if velocity > 2.0 and current_score < peak * 0.85:
        return LifecycleStage.EMERGING   # Rising fast, not yet at peak
    if velocity >= -1.0 and current_score >= peak * 0.85:
        return LifecycleStage.PEAK       # At or near peak (rising, stable, or gently slowing)
    if velocity >= -1.0 and current_score < peak * 0.85:
        return LifecycleStage.DECLINING  # Below peak, velocity still gentle (plateau decay)
    if velocity < -1.0 and current_score >= 20:
        return LifecycleStage.DECLINING  # Falling with significant score remaining
    if current_score < 15 or (velocity < -1.0 and current_score < 20):
        return LifecycleStage.FADING

    return LifecycleStage.EMERGING if velocity >= 0 else LifecycleStage.DECLINING


def lifecycle_color(stage: LifecycleStage) -> str:
    """ANSI-free color label for dashboard use."""
    return {
        LifecycleStage.EMERGING: "green",
        LifecycleStage.PEAK: "yellow",
        LifecycleStage.DECLINING: "orange",
        LifecycleStage.FADING: "gray",
    }.get(stage, "gray")


def lifecycle_emoji(stage: LifecycleStage) -> str:
    return {
        LifecycleStage.EMERGING: "🚀",
        LifecycleStage.PEAK: "🔥",
        LifecycleStage.DECLINING: "📉",
        LifecycleStage.FADING: "💨",
    }.get(stage, "")
