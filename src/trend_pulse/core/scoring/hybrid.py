"""Hybrid Scoring 2.0 — L1 Heuristic + L2 LLM Judge (optional) + L3 RAG History.

Usage:
    scorer = HybridScorer()
    result = await scorer.score(content, platform="threads")
    # Returns: {"total": 78.5, "breakdown": {...}, "grade": "B+"}

    # Quick one-shot helper:
    result = await score_content(content, platform="threads")
"""

from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
from typing import Any

# Optional: Anthropic SDK for L2 LLM Judge
try:
    import anthropic as _anthropic_module
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

# Cached Anthropic client — reused across score() calls to avoid per-call connection pool creation
_anthropic_client: "Any | None" = None


def _get_anthropic_client() -> "Any | None":
    """Return a cached AsyncAnthropic client, or None if not configured."""
    global _anthropic_client
    if not _ANTHROPIC_AVAILABLE:
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    if _anthropic_client is None:
        _anthropic_client = _anthropic_module.AsyncAnthropic(api_key=api_key)
    return _anthropic_client


# ──────────────────────────────────────────────
# Score result
# ──────────────────────────────────────────────

@dataclass
class ScoreResult:
    total: float                      # 0-100
    grade: str                        # S/A/B/C/D
    breakdown: dict[str, float] = field(default_factory=dict)
    signals: list[str] = field(default_factory=list)  # Human-readable notes
    mode: str = "heuristic"           # heuristic | llm | hybrid

    def to_dict(self) -> dict:
        return {
            "total": round(self.total, 1),
            "grade": self.grade,
            "mode": self.mode,
            "breakdown": {k: round(v, 1) for k, v in self.breakdown.items()},
            "signals": self.signals,
        }


def _grade(score: float) -> str:
    if score >= 90: return "S"
    if score >= 80: return "A"
    if score >= 70: return "B+"
    if score >= 60: return "B"
    if score >= 50: return "C+"
    if score >= 40: return "C"
    return "D"


# ──────────────────────────────────────────────
# L1 Heuristic scorer
# ──────────────────────────────────────────────

_HOOK_PATTERNS = [
    r"^\s*[^\w\s]{1,2}",           # Starts with emoji
    r"\b(why|how|what|when|who)\b", # Question words
    r"\?",                          # Question mark
    r"\b(breaking|just in|alert|exclusive)\b",
    r"\b(you|your|you're)\b",
]

_CTA_PATTERNS = [
    r"\b(comment|reply|share|tag|follow|dm|vote|poll)\b",
    r"\b(what do you think|tell me|agree|disagree)\b",
    r"\?[^?]*$",                    # Ends with question
]

_ENGAGEMENT_PATTERNS = [
    r"\b(controversial|hot take|unpopular opinion|fight me)\b",
    r"\b(everyone|nobody|always|never|every time)\b",
    r"\b(thread|🧵)\b",
    r"\b(1\/|part 1|first:\s)\b",
]


def _l1_heuristic(content: str, platform: str) -> tuple[float, dict[str, float], list[str]]:
    """Pure-regex heuristic scorer. No API calls, always available."""
    text = content.lower()
    signals: list[str] = []

    # Dimension weights (must sum to 100)
    # hook_power, engagement_trigger, conversation_durability,
    # velocity_potential, format_score
    weights = {
        "hook_power": 25,
        "engagement_trigger": 25,
        "conversation_durability": 20,
        "velocity_potential": 15,
        "format_score": 15,
    }

    # Hook Power (0-100)
    hook = 0.0
    lines = content.strip().splitlines()
    first_line = lines[0] if lines else ""
    for pat in _HOOK_PATTERNS:
        if re.search(pat, first_line, re.IGNORECASE):
            hook += 20
    hook = min(hook, 100)
    if hook >= 60:
        signals.append("Strong hook detected")

    # Engagement Trigger (0-100)
    engage = 0.0
    for pat in _CTA_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            engage += 25
    for pat in _ENGAGEMENT_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            engage += 15
    engage = min(engage, 100)
    if engage >= 50:
        signals.append("Good CTA / engagement trigger")

    # Conversation Durability (0-100) — based on length & substantive content
    word_count = len(content.split())
    if word_count < 10:
        durability = 20.0
    elif word_count < 30:
        durability = 45.0
    elif word_count < 60:
        durability = 70.0
    elif word_count < 150:
        durability = 85.0
    else:
        durability = 95.0

    # Velocity Potential (0-100) — trending keywords boost
    velocity = 50.0  # baseline; boosted externally if trend score is high
    if re.search(r"\b(ai|llm|gpt|claude|viral|trending|breaking)\b", text):
        velocity += 20
    velocity = min(velocity, 100)

    # Format Score (0-100) — platform char limit compliance + readability
    char_limits = {
        "threads": 500, "instagram": 2200, "facebook": 63206,
        "x": 280, "linkedin": 3000, "tiktok": 2200,
        "youtube": 5000, "xiaohongshu": 1000,
    }
    limit = char_limits.get(platform, 500)
    clen = len(content)

    if clen > limit:
        fmt = 0.0
        signals.append(f"Exceeds {platform} char limit ({clen}/{limit})")
    elif clen < limit * 0.1:
        fmt = 30.0
        signals.append("Content very short")
    else:
        # Penalise too-close to limit; reward 40-80% of limit
        ratio = clen / limit
        fmt = 100 - abs(ratio - 0.6) * 60
        fmt = max(fmt, 30.0)

    # Readability bonus
    if "\n" in content or "•" in content or "📌" in content:
        fmt += 10
        fmt = min(fmt, 100)

    breakdown = {
        "hook_power": hook,
        "engagement_trigger": engage,
        "conversation_durability": durability,
        "velocity_potential": velocity,
        "format_score": fmt,
    }
    total = sum(breakdown[k] * weights[k] / 100 for k in weights)
    return total, breakdown, signals


# ──────────────────────────────────────────────
# L2 LLM Judge (optional — Claude API)
# ──────────────────────────────────────────────

_LLM_SYSTEM = (
    "You are a viral content scoring judge. "
    "Score the user-provided post on a 0-100 scale across 5 dimensions. "
    "Return ONLY valid JSON with keys: "
    "hook_power, engagement_trigger, conversation_durability, velocity_potential, format_score, reasoning."
)


async def _l2_llm_judge(content: str, platform: str) -> dict[str, float] | None:
    """Call Claude API for LLM scoring. Returns breakdown dict or None on failure.

    Content is passed as a separate user message (not interpolated into the system
    prompt) to prevent prompt injection via crafted post text.
    """
    client = _get_anthropic_client()
    if client is None:
        return None
    import asyncio
    user_msg = f"Platform: {platform}\n\nPost to score:\n{content}"
    try:
        msg = await asyncio.wait_for(
            client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                system=_LLM_SYSTEM,
                messages=[{"role": "user", "content": user_msg}],
            ),
            timeout=15.0,
        )
        raw = msg.content[0].text
        data = json.loads(raw)
        return {k: float(data[k]) for k in (
            "hook_power", "engagement_trigger", "conversation_durability",
            "velocity_potential", "format_score",
        ) if k in data}
    except Exception as exc:
        logger.debug("L2 LLM judge failed: %s", exc)
        return None


# ──────────────────────────────────────────────
# L3 RAG History boost
# ──────────────────────────────────────────────

def _l3_rag_boost(content: str, history_keywords: list[str]) -> float:
    """Simple keyword overlap with historical high-performers. Returns 0-10 bonus."""
    if not history_keywords:
        return 0.0
    text_words = set(re.findall(r"\w+", content.lower()))
    hist_words = set(w.lower() for kw in history_keywords for w in re.findall(r"\w+", kw))
    overlap = len(text_words & hist_words)
    return min(overlap * 2.0, 10.0)


# ──────────────────────────────────────────────
# HybridScorer
# ──────────────────────────────────────────────

class HybridScorer:
    """Hybrid scoring: L1 heuristic + L2 optional LLM + L3 RAG history.

    Without ANTHROPIC_API_KEY → pure heuristic (mode="heuristic").
    With key → LLM scores blended 40/40/20 (mode="hybrid").
    """

    # Weights per layer (must sum ≤ 100; L3 is additive bonus)
    _L1_WEIGHT = 0.4
    _L2_WEIGHT = 0.4
    _L3_MAX = 10.0   # Bonus points added on top

    async def score(
        self,
        content: str,
        platform: str = "threads",
        history_keywords: list[str] | None = None,
    ) -> ScoreResult:
        """Score content using available layers.

        Args:
            content: The post text to score.
            platform: Target platform name (affects format score).
            history_keywords: Keywords from past viral posts for L3 boost.

        Returns:
            ScoreResult with total, grade, breakdown, and mode.
        """
        content = content[:100_000]  # guard against ReDoS on pathological inputs
        l1_total, l1_breakdown, signals = _l1_heuristic(content, platform)

        # Try L2
        l2_breakdown = await _l2_llm_judge(content, platform)

        if l2_breakdown:
            # Blend L1 + L2
            blended: dict[str, float] = {}
            weights = {"hook_power": 25, "engagement_trigger": 25,
                       "conversation_durability": 20, "velocity_potential": 15,
                       "format_score": 15}
            for dim in weights:
                blended[dim] = (
                    l1_breakdown.get(dim, 0) * self._L1_WEIGHT
                    + l2_breakdown.get(dim, 0) * self._L2_WEIGHT
                ) / (self._L1_WEIGHT + self._L2_WEIGHT)

            total = sum(blended[k] * weights[k] / 100 for k in weights)
            mode = "hybrid"
        else:
            blended = l1_breakdown
            total = l1_total
            mode = "heuristic"

        # L3 RAG bonus
        if history_keywords:
            bonus = _l3_rag_boost(content, history_keywords)
            total = min(total + bonus, 100.0)
            if bonus > 0:
                signals.append(f"History match bonus: +{bonus:.1f}")

        return ScoreResult(
            total=total,
            grade=_grade(total),
            breakdown=blended,
            signals=signals,
            mode=mode,
        )


# ──────────────────────────────────────────────
# Convenience helper
# ──────────────────────────────────────────────

_default_scorer = HybridScorer()


async def score_content(
    content: str,
    platform: str = "threads",
    history_keywords: list[str] | None = None,
) -> ScoreResult:
    """Score content using the default HybridScorer instance."""
    return await _default_scorer.score(content, platform=platform,
                                       history_keywords=history_keywords)
