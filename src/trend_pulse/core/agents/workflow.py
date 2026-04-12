"""Agentic Content Factory — pure Python multi-agent workflow (no LangGraph dep).

Six sequential agents with a shared WorkflowState TypedDict:
  1. researcher   — picks top trends
  2. strategist   — generates content angles
  3. writer       — drafts platform-specific content
  4. optimizer    — A/B variant selection
  5. checker      — basic compliance/safety
  6. distributor  — final output formatting

Usage:
    state = await run_content_workflow(
        trends=[...],          # list[TrendItem]
        platforms=["threads", "x"],
        brand_voice="casual",
        topic="AI agents",
    )
    print(state["final_content"])  # {"threads": "...", "x": "..."}
"""

from __future__ import annotations

import copy
import re
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from ...sources.base import TrendItem


# ──────────────────────────────────────────────
# Shared workflow state
# ──────────────────────────────────────────────

class ContentStrategy(TypedDict, total=False):
    angles: list[str]       # Content angles / hooks
    tone: str               # e.g. "informative", "provocative"
    cta: str                # Call-to-action directive
    target_audience: str


class ScoredDraft(TypedDict):
    platform: str
    content: str
    score: float
    variant: int            # 0 = original, 1+ = A/B variants


class WorkflowState(TypedDict, total=False):
    trends: list[Any]              # list[TrendItem]
    topic: str
    platforms: list[str]
    brand_voice: str
    strategy: ContentStrategy
    drafts: list[str]
    scored_drafts: list[ScoredDraft]
    final_content: dict[str, str]  # platform → content string
    errors: list[str]
    completed_agents: list[str]


# ──────────────────────────────────────────────
# Platform char limits
# ──────────────────────────────────────────────

_CHAR_LIMITS: dict[str, int] = {
    "threads": 500,
    "instagram": 2200,
    "facebook": 63206,
    "x": 280,
    "linkedin": 3000,
    "tiktok": 2200,
    "youtube": 5000,
    "xiaohongshu": 1000,
}


# ──────────────────────────────────────────────
# Agent 1: Researcher
# ──────────────────────────────────────────────

async def trend_researcher_agent(state: WorkflowState) -> WorkflowState:
    """Select top trends relevant to the topic."""
    trends = state.get("trends", [])
    topic = state.get("topic", "")

    if not trends and not topic:
        state.setdefault("errors", []).append("researcher: no trends or topic provided")
        state.setdefault("completed_agents", []).append("researcher")
        return state

    # Sort by score, keep top 5
    sorted_trends = sorted(trends, key=lambda t: getattr(t, "score", 0), reverse=True)
    top = sorted_trends[:5]

    # Build keyword summary for downstream agents
    keywords = [getattr(t, "keyword", str(t)) for t in top]
    if topic and topic not in keywords:
        keywords.insert(0, topic)

    state["trends"] = top
    state["topic"] = topic or (keywords[0] if keywords else "trending")
    state.setdefault("completed_agents", []).append("researcher")
    return state


# ──────────────────────────────────────────────
# Agent 2: Strategist
# ──────────────────────────────────────────────

_ANGLE_TEMPLATES = [
    "Hot take: {topic} is changing everything",
    "3 things nobody tells you about {topic}",
    "Why {topic} matters more than you think",
    "The dark side of {topic} everyone ignores",
    "How {topic} will affect you in 2026",
]

_TONE_MAP = {
    "casual": "conversational, emoji-friendly",
    "professional": "authoritative, data-driven",
    "provocative": "contrarian, debate-sparking",
    "educational": "clear, structured, informative",
}


async def idea_strategist_agent(state: WorkflowState) -> WorkflowState:
    """Generate content angles and strategy."""
    topic = state.get("topic", "this trend")
    brand_voice = state.get("brand_voice", "casual")
    tone = _TONE_MAP.get(brand_voice, brand_voice)

    angles = [tmpl.format(topic=topic) for tmpl in _ANGLE_TEMPLATES[:3]]

    strategy: ContentStrategy = {
        "angles": angles,
        "tone": tone,
        "cta": "What do you think? Drop a comment 👇",
        "target_audience": "tech-savvy social media users",
    }
    state["strategy"] = strategy
    state.setdefault("completed_agents", []).append("strategist")
    return state


# ──────────────────────────────────────────────
# Agent 3: Multimodal Copywriter
# ──────────────────────────────────────────────

def _draft_for_platform(topic: str, angle: str, cta: str, platform: str) -> str:
    """Generate a draft post for a platform. Pure template-based."""
    limit = _CHAR_LIMITS.get(platform, 500)

    if platform == "x":
        base = f"{angle} #{topic.replace(' ', '')} {cta}"
        return base[:limit]
    if platform == "linkedin":
        return (
            f"{angle}\n\n"
            f"As someone following {topic} closely, here's what I've noticed:\n\n"
            f"• The trend is accelerating faster than most realize\n"
            f"• Early adopters are already seeing results\n"
            f"• The window to act is narrowing\n\n"
            f"{cta}"
        )[:limit]
    if platform == "threads":
        return (
            f"{angle}\n\n"
            f"Here's why this matters for {topic}:\n\n"
            f"{cta}"
        )[:limit]
    # Default for other platforms
    return f"{angle}\n\n{cta}"[:limit]


async def multimodal_copywriter_agent(state: WorkflowState) -> WorkflowState:
    """Draft content for each target platform."""
    topic = state.get("topic", "trending topic")
    strategy = state.get("strategy", {})
    platforms = state.get("platforms", ["threads"])

    angles = strategy.get("angles", [f"Why {topic} matters"])
    cta = strategy.get("cta", "What do you think?")
    angle = angles[0] if angles else f"Trending: {topic}"

    drafts: list[str] = []
    for plat in platforms:
        draft = _draft_for_platform(topic, angle, cta, plat)
        drafts.append(draft)

    state["drafts"] = drafts
    state.setdefault("completed_agents", []).append("writer")
    return state


# ──────────────────────────────────────────────
# Agent 4: A/B Optimizer
# ──────────────────────────────────────────────

async def ab_optimizer_agent(state: WorkflowState) -> WorkflowState:
    """Score drafts and create A/B variants."""
    drafts = state.get("drafts", [])
    platforms = state.get("platforms", ["threads"])

    scored: list[ScoredDraft] = []
    for i, (draft, plat) in enumerate(zip(drafts, platforms)):
        # Simple heuristic score (no API call needed)
        score = _simple_score(draft, plat)
        scored.append(ScoredDraft(
            platform=plat,
            content=draft,
            score=score,
            variant=0,
        ))
        # Generate variant B
        variant_b = _mutate_draft(draft, plat)
        scored.append(ScoredDraft(
            platform=plat,
            content=variant_b,
            score=_simple_score(variant_b, plat),
            variant=1,
        ))

    state["scored_drafts"] = scored
    state.setdefault("completed_agents", []).append("optimizer")
    return state


def _simple_score(text: str, platform: str) -> float:
    """Fast heuristic score for A/B ranking."""
    score = 50.0
    if "?" in text: score += 10
    if re.search(r"[^\w\s]{1,2}", text[:50]): score += 10  # emoji in first 50 chars
    if "\n" in text: score += 5
    limit = _CHAR_LIMITS.get(platform, 500)
    ratio = len(text) / limit
    if 0.3 <= ratio <= 0.8: score += 15
    return min(score, 100.0)


def _mutate_draft(draft: str, platform: str) -> str:
    """Create a variant by tweaking the opening line."""
    lines = draft.splitlines()
    if lines:
        lines[0] = "🔥 " + lines[0] if not lines[0].startswith("🔥") else lines[0][len("🔥 "):]
    return "\n".join(lines)


# ──────────────────────────────────────────────
# Agent 5: Compliance Checker
# ──────────────────────────────────────────────

_BLOCKED_PATTERNS = [
    r"\b(buy now|guaranteed|100% free|make money fast)\b",
    r"\b(click here|limited time|act now)\b",
]


async def compliance_agent(state: WorkflowState) -> WorkflowState:
    """Basic spam / compliance filter on scored drafts."""
    scored = state.get("scored_drafts", [])
    errors = state.setdefault("errors", [])

    clean: list[ScoredDraft] = []
    for draft in scored:
        text = draft["content"].lower()
        flagged = any(re.search(p, text, re.IGNORECASE) for p in _BLOCKED_PATTERNS)
        if flagged:
            errors.append(f"Compliance flag on {draft['platform']} variant {draft['variant']}")
            draft = ScoredDraft(
                platform=draft["platform"],
                content=draft["content"],
                score=draft["score"] * 0.5,  # penalise but keep
                variant=draft["variant"],
            )
        clean.append(draft)

    state["scored_drafts"] = clean
    state.setdefault("completed_agents", []).append("checker")
    return state


# ──────────────────────────────────────────────
# Agent 6: Distributor
# ──────────────────────────────────────────────

async def distributor_agent(state: WorkflowState) -> WorkflowState:
    """Pick the best variant per platform and format final output."""
    scored = state.get("scored_drafts", [])
    platforms = state.get("platforms", ["threads"])

    best: dict[str, str] = {}
    for plat in platforms:
        candidates = [d for d in scored if d["platform"] == plat]
        if candidates:
            top = max(candidates, key=lambda d: d["score"])
            best[plat] = top["content"]

    state["final_content"] = best
    state.setdefault("completed_agents", []).append("distributor")
    return state


# ──────────────────────────────────────────────
# ContentWorkflow orchestrator
# ──────────────────────────────────────────────

_AGENTS = [
    trend_researcher_agent,
    idea_strategist_agent,
    multimodal_copywriter_agent,
    ab_optimizer_agent,
    compliance_agent,
    distributor_agent,
]


class ContentWorkflow:
    """Sequential 6-agent content pipeline."""

    async def run(self, initial_state: WorkflowState) -> WorkflowState:
        """Execute all agents in sequence, passing state through each."""
        state = copy.deepcopy(dict(initial_state))
        state.setdefault("errors", [])
        state.setdefault("completed_agents", [])

        for agent in _AGENTS:
            try:
                state = await agent(state)  # type: ignore[assignment]
            except Exception as exc:
                state["errors"].append(f"{agent.__name__}: {exc}")

        return state


async def run_content_workflow(
    trends: list[Any] | None = None,
    platforms: list[str] | None = None,
    brand_voice: str = "casual",
    topic: str = "",
) -> WorkflowState:
    """Convenience function: run the full 6-agent workflow.

    Args:
        trends: list[TrendItem] from aggregator.
        platforms: Target platforms (default: ["threads"]).
        brand_voice: Tone — "casual", "professional", "provocative", "educational".
        topic: Explicit topic override (uses top trend keyword if not set).

    Returns:
        WorkflowState with "final_content" key containing platform→content dict.
    """
    initial: WorkflowState = {
        "trends": trends or [],
        "platforms": platforms or ["threads"],
        "brand_voice": brand_voice,
        "topic": topic,
    }
    workflow = ContentWorkflow()
    return await workflow.run(initial)
