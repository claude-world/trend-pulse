"""
Content briefing generator — provides structured guides for LLM content creation.

All guide functions return structured data (criteria, examples, checklists) that an LLM
uses to create, score, and review content. The MCP layer provides data; the LLM does
all judgment and creative work.
"""

import unicodedata

from ..patents.database import PATENTS, get_scoring_weights
from ..patents.templates import get_templates, CONTENT_TYPES
from ..content.adapter import PLATFORM_SPECS


def _detect_language(text: str) -> str:
    """Detect language based on CJK character presence."""
    for ch in text:
        if unicodedata.category(ch).startswith("Lo"):
            # CJK Unified Ideographs or other East Asian scripts
            cp = ord(ch)
            if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
                return "zh-TW"
            if 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF:
                return "ja"
            if 0xAC00 <= cp <= 0xD7AF:
                return "ko"
    return "en"


def get_content_brief(
    topic: str,
    content_type: str = "debate",
    platform: str = "threads",
    lang: str = "auto",
) -> dict:
    """
    Return a structured writing brief for LLM content creation.

    Instead of generating posts via templates, this provides:
    - Hook examples and CTA examples (language-aware)
    - Patent strategies and scoring dimensions
    - Platform specs and character limits
    - Content type guidance

    Args:
        topic: Subject to create content about
        content_type: Post style (opinion/story/debate/howto/list/question/news/meme)
        platform: Target platform (threads/instagram/facebook)
        lang: Language code ("auto", "en", "zh-TW"). Auto-detects from topic.

    Returns:
        Dict with structured writing guide data.
    """
    if lang == "auto":
        lang = _detect_language(topic)

    # Get language-specific templates
    hook_templates, body_templates, cta_templates = get_templates(lang)

    # Build hook examples from templates
    hook_examples = []
    for category, data in hook_templates.items():
        examples = data["templates"][:2]  # Top 2 per category
        for ex in examples:
            hook_examples.append({
                "category": category,
                "patent": data["patent"],
                "example": ex.replace("{topic}", topic).replace("{time}", "3 months").replace("{count}", "5"),
            })

    # Build CTA examples
    cta_examples = [cta.strip().lstrip("-\n ") for cta in cta_templates]

    # Patent strategies
    patent_strategies = []
    weights = get_scoring_weights()
    dim_to_patent = {
        "hook_power": ["edgerank", "andromeda"],
        "engagement_trigger": ["story_viewer_tuple", "dear_algo"],
        "conversation_durability": ["conversation_durability"],
        "velocity_potential": ["andromeda"],
        "format_score": ["andromeda"],
    }
    for dim, weight in weights.items():
        patent_keys = dim_to_patent.get(dim, [])
        strategies = []
        for pk in patent_keys:
            p = PATENTS.get(pk)
            if p:
                strategies.append(p["strategy"])
        patent_strategies.append({
            "dimension": dim,
            "weight": weight,
            "strategies": strategies,
        })

    # Scoring dimension tips
    if lang == "en":
        scoring_dimensions = {
            "hook_power": {
                "weight": 0.25,
                "tips": ["Use numbers/stats", "Ask questions", "Counter-intuitive claims", "Create curiosity gaps"],
            },
            "engagement_trigger": {
                "weight": 0.25,
                "tips": ["Address the reader directly (you/your)", "Include CTA (comment/share/save)", "End with a question", "Humorous content officially receives more views on Threads"],
            },
            "conversation_durability": {
                "weight": 0.20,
                "tips": ["Present two sides of an argument", "Use contrast (but/however)", "Ask open-ended questions"],
            },
            "velocity_potential": {
                "weight": 0.15,
                "tips": ["Reference current events", "Use urgency words", "Keep it concise (50-300 chars)"],
            },
            "format_score": {
                "weight": 0.15,
                "tips": ["Use line breaks for readability", "Add numbered lists", "Keep within platform char limit"],
            },
        }
    else:
        scoring_dimensions = {
            "hook_power": {
                "weight": 0.25,
                "tips": ["用數字/數據", "問句開頭", "反直覺觀點", "製造好奇心缺口"],
            },
            "engagement_trigger": {
                "weight": 0.25,
                "tips": ["直接對讀者說話（你/你們）", "加 CTA（留言/分享/收藏）", "以提問結尾", "幽默內容在 Threads 上官方確認獲得更多觀看"],
            },
            "conversation_durability": {
                "weight": 0.20,
                "tips": ["提出兩面性觀點", "用轉折語（但是/然而）", "開放式問題"],
            },
            "velocity_potential": {
                "weight": 0.15,
                "tips": ["蹭即時熱點", "用緊急感詞彙", "精簡篇幅 (50-300字)"],
            },
            "format_score": {
                "weight": 0.15,
                "tips": ["善用換行分段", "加編號列表", "控制在平台字數限制內"],
            },
        }

    # Content type spec
    ctype = CONTENT_TYPES.get(content_type, CONTENT_TYPES["debate"])
    content_type_spec = {
        "key": content_type,
        "label": ctype["label"],
        "multiplier": ctype["multiplier"],
        "best_hooks": ctype["best_hooks"],
    }

    # Platform spec
    spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["threads"])
    platform_spec = {
        "name": platform,
        **spec,
    }

    # Character limit
    char_limits = {"threads": 500, "instagram": 2200, "facebook": 63206}
    char_limit = char_limits.get(platform, 500)

    return {
        "topic": topic,
        "content_type": content_type,
        "language": lang,
        "platform": platform_spec,
        "patent_strategies": patent_strategies,
        "scoring_dimensions": scoring_dimensions,
        "hook_examples": hook_examples,
        "cta_examples": cta_examples,
        "content_type_spec": content_type_spec,
        "char_limit": char_limit,
        "quality_gate": {
            "min_overall": 70,
            "min_conversation": 55,
        },
    }


def get_scoring_guide(lang: str = "auto", topic: str = "") -> dict:
    """
    Return the 5-dimension scoring framework for LLM to evaluate posts.

    The LLM reads this guide and scores posts itself — no regex heuristics.

    Args:
        lang: Language for tips/examples ("auto", "en", "zh-TW").
        topic: Optional topic hint for language auto-detection.

    Returns:
        Dict with dimensions, weights, evaluation criteria, grade thresholds,
        and scoring instructions.
    """
    if lang == "auto":
        lang = _detect_language(topic) if topic else "en"

    weights = get_scoring_weights()

    if lang == "en":
        dimensions = {
            "hook_power": {
                "weight": weights["hook_power"],
                "patent_basis": "EdgeRank Weight + Andromeda",
                "description": "How strongly the first line grabs attention and stops scrolling",
                "evaluate": [
                    "Does the first line create curiosity, tension, or surprise?",
                    "Does it use numbers, questions, or counter-intuitive claims?",
                    "Is the hook length optimal (10-45 characters)?",
                    "Would YOU stop scrolling to read this?",
                ],
                "high_signals": ["curiosity gap", "specific numbers/stats", "bold claim", "direct question", "emotional trigger"],
                "low_signals": ["generic opener", "too long/wordy", "no hook at all", "clickbait without substance"],
            },
            "engagement_trigger": {
                "weight": weights["engagement_trigger"],
                "patent_basis": "Story-Viewer Tuple + Dear Algo",
                "description": "How likely readers are to interact (like, comment, share, save)",
                "evaluate": [
                    "Does it address the reader directly (you/your)?",
                    "Is there a clear CTA (comment/share/save/follow)?",
                    "Does it end with a question or invitation to respond?",
                    "Would readers feel compelled to react?",
                    "Will you actively reply to comments? (Replies ≈ 50% of Threads views)",
                ],
                "high_signals": ["direct address", "clear CTA", "question ending", "relatable content", "actionable advice"],
                "low_signals": ["passive voice", "no CTA", "monologue style", "no reader involvement"],
            },
            "conversation_durability": {
                "weight": weights["conversation_durability"],
                "patent_basis": "Threads 72hr Conversation Window",
                "description": "Will this spark multi-day, multi-party discussion?",
                "evaluate": [
                    "Does it present a debatable topic with two valid sides?",
                    "Are there contrast/tension points (but/however/yet)?",
                    "Would different people have genuinely different opinions?",
                    "Could this conversation sustain 72+ hours of new replies?",
                ],
                "high_signals": ["genuine controversy", "open-ended question", "two-sided argument", "personal experience inviting others to share"],
                "low_signals": ["one-sided statement", "no room for disagreement", "closed question", "pure information dump"],
            },
            "velocity_potential": {
                "weight": weights["velocity_potential"],
                "patent_basis": "Andromeda Real-time Signal",
                "description": "How quickly will this gain traction in the first 30 minutes?",
                "evaluate": [
                    "Does it reference something timely or trending?",
                    "Is it concise enough for quick consumption (50-300 chars ideal)?",
                    "Does the hook create urgency or FOMO?",
                    "Would someone share this immediately?",
                ],
                "high_signals": ["timely reference", "urgency language", "breaking news angle", "concise format", "share-worthy insight"],
                "low_signals": ["evergreen only", "too long for quick share", "no urgency", "requires too much context"],
            },
            "format_score": {
                "weight": weights["format_score"],
                "patent_basis": "Multi-modal Indexing",
                "description": "Is the content well-formatted for the platform?",
                "evaluate": [
                    "Does it use line breaks for readability?",
                    "Are there visual structures (numbered lists, separators)?",
                    "Is the length appropriate for the platform?",
                    "Would it look good on a mobile screen?",
                ],
                "high_signals": ["clear paragraphs", "numbered/bulleted lists", "separator lines", "optimal length", "scannable structure"],
                "low_signals": ["wall of text", "no line breaks", "too long/short", "poor mobile readability"],
            },
        }
    else:
        dimensions = {
            "hook_power": {
                "weight": weights["hook_power"],
                "patent_basis": "EdgeRank Weight + Andromeda",
                "description": "第一行抓住注意力、讓人停下滑動的能力",
                "evaluate": [
                    "第一行是否製造了好奇心、張力或驚喜？",
                    "是否使用了數字、提問或反直覺的觀點？",
                    "Hook 長度是否最佳（10-45 字）？",
                    "你自己會停下來看嗎？",
                ],
                "high_signals": ["好奇心缺口", "具體數字/數據", "大膽宣言", "直接提問", "情緒觸發"],
                "low_signals": ["平淡開頭", "太長太囉嗦", "沒有 Hook", "標題黨但無實質"],
            },
            "engagement_trigger": {
                "weight": weights["engagement_trigger"],
                "patent_basis": "Story-Viewer Tuple + Dear Algo",
                "description": "讀者互動（按讚、留言、分享、收藏）的可能性",
                "evaluate": [
                    "是否直接對讀者說話（你/你們）？",
                    "是否有明確的 CTA（留言/分享/收藏/追蹤）？",
                    "是否以提問或邀請回應結尾？",
                    "讀者會覺得「必須回應」嗎？",
                    "你會積極回覆留言嗎？（回覆 ≈ Threads 50% 觀看量）",
                ],
                "high_signals": ["直接稱呼", "明確 CTA", "提問結尾", "引起共鳴", "可操作建議"],
                "low_signals": ["被動語態", "無 CTA", "獨白式", "無讀者參與感"],
            },
            "conversation_durability": {
                "weight": weights["conversation_durability"],
                "patent_basis": "Threads 72hr 對話窗口",
                "description": "能否引發多天、多方參與的討論？",
                "evaluate": [
                    "是否提出了有正反兩面的議題？",
                    "是否有轉折/張力（但是/然而/不過）？",
                    "不同人會有真正不同的看法嗎？",
                    "這個討論能持續 72 小時以上嗎？",
                ],
                "high_signals": ["真正的爭議性", "開放式問題", "兩面性論點", "邀請分享個人經驗"],
                "low_signals": ["一面倒的陳述", "沒有討論空間", "封閉式問題", "純資訊灌輸"],
            },
            "velocity_potential": {
                "weight": weights["velocity_potential"],
                "patent_basis": "Andromeda 即時信號",
                "description": "前 30 分鐘能多快獲得關注？",
                "evaluate": [
                    "是否與當前熱點或趨勢相關？",
                    "是否足夠精簡以便快速消費（50-300 字最佳）？",
                    "Hook 是否製造了緊迫感？",
                    "看到的人會立刻轉發嗎？",
                ],
                "high_signals": ["即時熱點", "緊急感用語", "突發新聞角度", "精簡格式", "值得分享的洞察"],
                "low_signals": ["純常青內容", "太長不適合快速分享", "無緊迫感", "需要太多背景知識"],
            },
            "format_score": {
                "weight": weights["format_score"],
                "patent_basis": "Multi-modal Indexing",
                "description": "內容在平台上的排版是否合適？",
                "evaluate": [
                    "是否善用換行提升可讀性？",
                    "是否有視覺結構（編號列表、分隔線）？",
                    "長度是否符合平台限制？",
                    "在手機螢幕上看起來好嗎？",
                ],
                "high_signals": ["清晰段落", "編號/項目列表", "分隔線", "最佳長度", "可掃描的結構"],
                "low_signals": ["文字牆", "無換行", "太長/太短", "手機閱讀體驗差"],
            },
        }

    grade_thresholds = {
        "S": {"min": 90, "description": "Exceptional — publish immediately"},
        "A": {"min": 80, "description": "Excellent — minor tweaks optional"},
        "B": {"min": 70, "description": "Good — meets quality gate, publishable"},
        "C": {"min": 55, "description": "Average — needs improvement before publishing"},
        "D": {"min": 0, "description": "Weak — significant rewrite needed"},
    }

    # Penalty pre-checks (must pass before scoring)
    if lang == "en":
        penalty_precheck = {
            "description": "Check these BEFORE scoring. If any fail, rewrite first.",
            "source": "https://creators.instagram.com/threads",
            "penalties": [
                {"id": "no_clickbait", "check": "Hook promises something the body doesn't deliver", "action": "Align hook with content"},
                {"id": "no_engagement_bait", "check": "Explicitly asks for likes/reposts/follows", "action": "Replace with natural CTA"},
                {"id": "no_contest_violation", "check": "Contest/giveaway requires engagement to enter", "action": "Remove or decouple"},
                {"id": "original_content", "check": "Cross-posted from another platform without original angle", "action": "Rewrite with original perspective"},
            ],
        }
    else:
        penalty_precheck = {
            "description": "評分前先檢查這些。任何一項不通過就先改寫。",
            "source": "https://creators.instagram.com/threads",
            "penalties": [
                {"id": "no_clickbait", "check": "Hook 承諾了正文沒兌現的東西", "action": "讓 Hook 與正文對齊"},
                {"id": "no_engagement_bait", "check": "直接要求按讚/轉發/追蹤", "action": "用自然 CTA 替換"},
                {"id": "no_contest_violation", "check": "抽獎/贈品要求互動行為才能參加", "action": "移除或脫鉤"},
                {"id": "original_content", "check": "從其他平台搬運且無原創角度", "action": "加入原創觀點重寫"},
            ],
        }

    return {
        "scoring_method": "Evaluate each dimension 0-100, then compute weighted overall score",
        "penalty_precheck": penalty_precheck,
        "dimensions": dimensions,
        "grade_thresholds": grade_thresholds,
        "quality_gate": {
            "min_overall": 70,
            "min_conversation": 55,
        },
        "instructions": (
            "FIRST: Run penalty pre-check. If any penalty is triggered, rewrite before scoring. "
            "THEN: Score each dimension 0-100 based on the evaluation criteria. "
            "Compute overall = sum(dimension_score * weight). "
            "Assign grade based on thresholds. "
            "List specific strengths and improvement suggestions."
        ),
    }


def get_review_checklist(platform: str = "threads", lang: str = "auto", topic: str = "") -> dict:
    """
    Return a structured review checklist for LLM to evaluate content quality.

    The LLM reads this checklist and reviews the post itself — the tool only
    provides the criteria, thresholds, and platform constraints.

    Args:
        platform: Target platform (threads/instagram/facebook).
        lang: Language for checklist text ("auto", "en", "zh-TW").
        topic: Optional topic hint for language auto-detection.

    Returns:
        Dict with platform limits, quality thresholds, and checklist items.
    """
    if lang == "auto":
        lang = _detect_language(topic) if topic else "en"

    char_limits = {"threads": 500, "instagram": 2200, "facebook": 63206}
    char_limit = char_limits.get(platform, 500)

    if lang == "en":
        checklist = [
            {
                "id": "char_limit",
                "category": "platform_compliance",
                "severity": "critical",
                "check": f"Is the text within {platform} character limit ({char_limit} chars)?",
                "pass_criteria": f"Text length <= {char_limit}",
                "auto_fixable": True,
                "fix_method": "Trim to limit with '...' suffix",
            },
            {
                "id": "overall_score",
                "category": "quality_gate",
                "severity": "critical",
                "check": "Does the post score >= 70 overall (using the 5-dimension scoring guide)?",
                "pass_criteria": "Weighted overall score >= 70",
                "auto_fixable": False,
                "fix_method": "Rewrite weak dimensions based on scoring guide suggestions",
            },
            {
                "id": "conversation_durability",
                "category": "quality_gate",
                "severity": "critical",
                "check": "Does conversation durability score >= 55?",
                "pass_criteria": "Conversation dimension score >= 55",
                "auto_fixable": False,
                "fix_method": "Add debatable angles, open-ended questions, or contrast points",
            },
            {
                "id": "no_clickbait",
                "category": "algorithm_penalty",
                "severity": "critical",
                "check": "Does the hook deliver on its promise? (Clickbait = reduced distribution)",
                "pass_criteria": "Every claim in the hook is substantiated in the body",
                "auto_fixable": False,
                "fix_method": "Align hook with actual content, or tone down the hook",
            },
            {
                "id": "no_engagement_bait",
                "category": "algorithm_penalty",
                "severity": "critical",
                "check": "Does the post avoid engagement bait? (Explicitly penalized by Threads)",
                "pass_criteria": "No 'like if you agree', 'repost this', 'follow for more', or similar",
                "auto_fixable": False,
                "fix_method": "Remove bait language, replace with genuine conversation starters",
            },
            {
                "id": "no_contest_violation",
                "category": "algorithm_penalty",
                "severity": "critical",
                "check": "No contests/giveaways that require engagement actions to enter?",
                "pass_criteria": "No prize offers contingent on likes/follows/reposts",
                "auto_fixable": False,
                "fix_method": "Remove contest mechanics or decouple from engagement requirements",
            },
            {
                "id": "original_content",
                "category": "algorithm_penalty",
                "severity": "critical",
                "check": "Is this original Threads content (not cross-posted from IG/FB)?",
                "pass_criteria": "Written specifically for Threads with original angle — reposts get reduced reach",
                "auto_fixable": False,
                "fix_method": "Rewrite with Threads-native voice and original perspective",
            },
            {
                "id": "hook_effectiveness",
                "category": "content_quality",
                "severity": "warning",
                "check": "Is the first line an effective hook (10-45 chars, grabs attention)?",
                "pass_criteria": "First line is 10-45 characters and creates curiosity/tension",
                "auto_fixable": False,
                "fix_method": "Rewrite first line with numbers, questions, or bold claims",
            },
            {
                "id": "cta_presence",
                "category": "content_quality",
                "severity": "warning",
                "check": "Does the post include a clear Call-to-Action?",
                "pass_criteria": "Contains explicit CTA (comment/share/save/follow/tell me/etc.)",
                "auto_fixable": False,
                "fix_method": "Add a natural CTA at the end",
            },
            {
                "id": "question_presence",
                "category": "engagement",
                "severity": "info",
                "check": "Does the post include at least one question to trigger interaction?",
                "pass_criteria": "Contains at least one question mark",
                "auto_fixable": False,
                "fix_method": "Add a question that invites reader participation",
            },
            {
                "id": "media_enhancement",
                "category": "content_quality",
                "severity": "warning",
                "check": "Does the post include media (image/video/carousel) alongside text?",
                "pass_criteria": "Text + media combination — officially outperforms text-only on Threads",
                "auto_fixable": False,
                "fix_method": "Add a relevant image, video, or carousel",
            },
            {
                "id": "tone_authenticity",
                "category": "content_quality",
                "severity": "warning",
                "check": "Does the post sound authentic with personal voice? (Humor performs well on Threads)",
                "pass_criteria": "Has personal angle, genuine opinion, or humor — not corporate/bot tone",
                "auto_fixable": False,
                "fix_method": "Add personal experience, opinion, or witty observation",
            },
            {
                "id": "topic_tag",
                "category": "discoverability",
                "severity": "warning",
                "check": "Does the post include a relevant topic tag for discoverability?",
                "pass_criteria": "Has --topic-tag with relevant multi-word tag",
                "auto_fixable": True,
                "fix_method": "Add --topic-tag with the post's main subject",
            },
            {
                "id": "format_readability",
                "category": "format",
                "severity": "info",
                "check": "Is the text well-formatted with line breaks and structure?",
                "pass_criteria": "Has line breaks, paragraphs, or lists for readability",
                "auto_fixable": True,
                "fix_method": "Add line breaks after sentences, add separator line before CTA",
            },
            {
                "id": "reply_strategy",
                "category": "engagement",
                "severity": "info",
                "check": "Does the post invite replies? (Replies = ~50% of Threads views)",
                "pass_criteria": "Ends with a question or invites sharing personal experience",
                "auto_fixable": False,
                "fix_method": "Add follow-up question or 'What's your experience?' prompt",
            },
        ]
    else:
        checklist = [
            {
                "id": "char_limit",
                "category": "platform_compliance",
                "severity": "critical",
                "check": f"文字是否在 {platform} 字數限制內（{char_limit} 字）？",
                "pass_criteria": f"文字長度 <= {char_limit}",
                "auto_fixable": True,
                "fix_method": "截斷至限制長度，加 '...' 結尾",
            },
            {
                "id": "overall_score",
                "category": "quality_gate",
                "severity": "critical",
                "check": "整體評分是否 >= 70（使用 5 維度評分指南）？",
                "pass_criteria": "加權整體分數 >= 70",
                "auto_fixable": False,
                "fix_method": "根據評分指南建議改寫弱勢維度",
            },
            {
                "id": "conversation_durability",
                "category": "quality_gate",
                "severity": "critical",
                "check": "對話持久性是否 >= 55？",
                "pass_criteria": "對話維度分數 >= 55",
                "auto_fixable": False,
                "fix_method": "加入可辯論的角度、開放式問題或轉折點",
            },
            {
                "id": "no_clickbait",
                "category": "algorithm_penalty",
                "severity": "critical",
                "check": "Hook 是否兌現了承諾？（標題黨 = 降低觸及）",
                "pass_criteria": "Hook 中的每個宣言都在正文中有實質內容支撐",
                "auto_fixable": False,
                "fix_method": "讓 Hook 與正文對齊，或降低 Hook 的承諾",
            },
            {
                "id": "no_engagement_bait",
                "category": "algorithm_penalty",
                "severity": "critical",
                "check": "是否避免了互動誘餌？（Threads 官方明確處罰）",
                "pass_criteria": "無「按讚=同意」「轉發這篇」「追蹤看更多」等直接要求互動",
                "auto_fixable": False,
                "fix_method": "移除誘餌用語，替換為真誠的對話開場",
            },
            {
                "id": "no_contest_violation",
                "category": "algorithm_penalty",
                "severity": "critical",
                "check": "是否無違規抽獎/贈品活動？",
                "pass_criteria": "無以按讚/追蹤/轉發為參加條件的活動",
                "auto_fixable": False,
                "fix_method": "移除活動機制或將參加條件與互動行為脫鉤",
            },
            {
                "id": "original_content",
                "category": "algorithm_penalty",
                "severity": "critical",
                "check": "是否為 Threads 原創內容（非從 IG/FB 搬運）？",
                "pass_criteria": "專為 Threads 撰寫，有原創角度 — 搬運內容觸及會下降",
                "auto_fixable": False,
                "fix_method": "用 Threads 原生語氣重寫，加入原創觀點",
            },
            {
                "id": "hook_effectiveness",
                "category": "content_quality",
                "severity": "warning",
                "check": "第一行是否是有效的 Hook（10-45 字，吸引注意力）？",
                "pass_criteria": "第一行 10-45 字，製造好奇心或張力",
                "auto_fixable": False,
                "fix_method": "用數字、提問或大膽觀點改寫第一行",
            },
            {
                "id": "cta_presence",
                "category": "content_quality",
                "severity": "warning",
                "check": "是否包含明確的行動呼籲（CTA）？",
                "pass_criteria": "包含明確 CTA（留言/分享/收藏/追蹤/告訴我等）",
                "auto_fixable": False,
                "fix_method": "在結尾加入自然的 CTA",
            },
            {
                "id": "question_presence",
                "category": "engagement",
                "severity": "info",
                "check": "是否包含至少一個問句觸發互動？",
                "pass_criteria": "至少有一個問號",
                "auto_fixable": False,
                "fix_method": "加入邀請讀者參與的問句",
            },
            {
                "id": "media_enhancement",
                "category": "content_quality",
                "severity": "warning",
                "check": "貼文是否搭配圖片/影片/輪播？",
                "pass_criteria": "文字 + 媒體組合 — Threads 官方確認效果顯著優於純文字",
                "auto_fixable": False,
                "fix_method": "加入相關的圖片、影片或輪播",
            },
            {
                "id": "tone_authenticity",
                "category": "content_quality",
                "severity": "warning",
                "check": "語氣是否真實有個人特色？（幽默在 Threads 表現特別好）",
                "pass_criteria": "有個人觀點、真實體驗或幽默感 — 非公司腔/機器人腔",
                "auto_fixable": False,
                "fix_method": "加入個人經歷、觀點或機智的觀察",
            },
            {
                "id": "topic_tag",
                "category": "discoverability",
                "severity": "warning",
                "check": "是否加了相關的 Topic Tag 提升可發現性？",
                "pass_criteria": "有 --topic-tag 且為相關的多字主題標籤",
                "auto_fixable": True,
                "fix_method": "加入 --topic-tag 並填寫貼文的主題",
            },
            {
                "id": "format_readability",
                "category": "format",
                "severity": "info",
                "check": "排版是否有換行和結構？",
                "pass_criteria": "有換行、段落或列表提升可讀性",
                "auto_fixable": True,
                "fix_method": "在句子後加換行，CTA 前加分隔線",
            },
            {
                "id": "reply_strategy",
                "category": "engagement",
                "severity": "info",
                "check": "貼文是否邀請回覆？（回覆 ≈ Threads 50% 觀看量）",
                "pass_criteria": "以問題結尾或邀請分享個人經驗",
                "auto_fixable": False,
                "fix_method": "加入追問或「你的經驗是什麼？」類提示",
            },
        ]

    return {
        "platform": platform,
        "char_limit": char_limit,
        "quality_gate": {
            "min_overall": 70,
            "min_conversation": 55,
        },
        "verdict_rules": {
            "pass": "All critical checks pass",
            "fail": "Any critical check fails",
        },
        "checklist": checklist,
        "instructions": (
            "Review the post against each checklist item. "
            "For each item, determine pass/fail and note specific issues. "
            "Compute final verdict based on critical checks. "
            "Suggest fixes for failed items."
        ),
    }


def get_reel_guide(style: str = "educational", duration: int = 30, lang: str = "auto", topic: str = "") -> dict:
    """
    Return a structured guide for creating Reels/Short video scripts.

    The LLM uses this structure to create original scripts with custom
    captions, voiceover, and visual directions — no template text.

    Args:
        style: Script style (educational/storytelling/listicle).
        duration: Target duration in seconds.
        lang: Language for guide text ("auto", "en", "zh-TW").
        topic: Optional topic hint for language auto-detection.

    Returns:
        Dict with scene structure, timing, guidelines, and best practices.
    """
    if lang == "auto":
        lang = _detect_language(topic) if topic else "en"

    is_en = lang == "en"

    # Scene structures per style
    structures = {
        "educational": {
            "label": "Educational" if is_en else "教學型",
            "scene_flow": [
                {
                    "type": "HOOK",
                    "time_pct": 10,
                    "purpose": "Stop the scroll — create curiosity or challenge an assumption" if is_en else "停止滑動 — 製造好奇心或挑戰假設",
                    "visual_guidance": "Face-to-camera or text animation pop-in" if is_en else "面對鏡頭 / 文字動畫彈入",
                    "tips": ["First 3 seconds determine if viewer stays" if is_en else "前 3 秒決定觀眾是否繼續看"],
                },
                {
                    "type": "PROBLEM",
                    "time_pct": 23,
                    "purpose": "Establish the pain point — make viewer feel understood" if is_en else "建立痛點 — 讓觀眾感到被理解",
                    "visual_guidance": "Show problem scenario / B-roll + text overlay" if is_en else "展示問題場景 / B-roll + 文字疊加",
                    "tips": ["Build empathy with a relatable struggle" if is_en else "用可共鳴的掙扎建立同理心"],
                },
                {
                    "type": "SOLUTION",
                    "time_pct": 40,
                    "purpose": "Deliver the core value — clear, actionable steps" if is_en else "傳遞核心價值 — 清晰、可操作的步驟",
                    "visual_guidance": "Step-by-step demo / screen recording / bullet points" if is_en else "步驟展示 / 螢幕錄製 / 文字列點",
                    "tips": ["This is the meat — keep it focused" if is_en else "核心價值段，保持聚焦"],
                },
                {
                    "type": "PROOF",
                    "time_pct": 17,
                    "purpose": "Show evidence — results, data, before/after" if is_en else "展示證據 — 成果、數據、前後對比",
                    "visual_guidance": "Results screenshot / data / before-after comparison" if is_en else "成果展示 / 數據截圖 / 前後對比",
                    "tips": ["Social proof increases credibility" if is_en else "社會證明增加可信度"],
                },
                {
                    "type": "CTA",
                    "time_pct": 10,
                    "purpose": "Drive action — follow, save, comment" if is_en else "驅動行動 — 追蹤、收藏、留言",
                    "visual_guidance": "Point to follow button / text prompt" if is_en else "指向追蹤按鍵 / 文字提示",
                    "tips": ["CTA should feel natural, not forced" if is_en else "CTA 要自然，不要勉強"],
                },
            ],
            "music_style": "Upbeat lo-fi / light electronic" if is_en else "Upbeat lo-fi / 輕快電子",
        },
        "storytelling": {
            "label": "Storytelling" if is_en else "故事型",
            "scene_flow": [
                {
                    "type": "HOOK",
                    "time_pct": 10,
                    "purpose": "Emotional opening — create intrigue or tension" if is_en else "情緒開場 — 製造懸念或張力",
                    "visual_guidance": "Emotional expression / dramatic visual" if is_en else "情緒表情 / 戲劇性畫面",
                    "tips": ["Start in the middle of the action" if is_en else "從行動的中間開始"],
                },
                {
                    "type": "SETUP",
                    "time_pct": 30,
                    "purpose": "Set the scene — who, when, what was happening" if is_en else "設定場景 — 誰、何時、發生什麼",
                    "visual_guidance": "Narrative visuals / photo flashback" if is_en else "敘事畫面 / 照片回顧",
                    "tips": ["Build context quickly" if is_en else "快速建立脈絡"],
                },
                {
                    "type": "CONFLICT",
                    "time_pct": 33,
                    "purpose": "The turning point — what went wrong or changed" if is_en else "轉折點 — 什麼出了問題或改變了",
                    "visual_guidance": "Transition scene / mood shift" if is_en else "轉折場景 / 情緒轉換",
                    "tips": ["This is where viewers lean in" if is_en else "這是觀眾最投入的地方"],
                },
                {
                    "type": "RESOLUTION",
                    "time_pct": 20,
                    "purpose": "The lesson or outcome — what you learned" if is_en else "結局或教訓 — 你學到了什麼",
                    "visual_guidance": "Positive outcome / smile" if is_en else "正面結果 / 笑容",
                    "tips": ["End with a universal takeaway" if is_en else "以普遍適用的收穫結尾"],
                },
                {
                    "type": "CTA",
                    "time_pct": 7,
                    "purpose": "Invite shared experience" if is_en else "邀請分享類似經歷",
                    "visual_guidance": "Text: 'Had a similar experience?'" if is_en else "文字：「你有類似經歷嗎？」",
                    "tips": ["Story CTAs work best as questions" if is_en else "故事型 CTA 用提問效果最好"],
                },
            ],
            "music_style": "Emotional piano / cinematic" if is_en else "Emotional piano / 鋼琴配樂",
        },
        "listicle": {
            "label": "Listicle" if is_en else "清單型",
            "scene_flow": [
                {
                    "type": "HOOK",
                    "time_pct": 10,
                    "purpose": "Number reveal — set expectation" if is_en else "數字揭示 — 建立期待",
                    "visual_guidance": "Big number pop-in animation" if is_en else "數字大字體彈入",
                    "tips": ["Odd numbers (5, 7) feel more authentic" if is_en else "奇數（5、7）感覺更真實"],
                },
                {
                    "type": "POINTS",
                    "time_pct": 77,
                    "purpose": "Deliver each point — equal pacing, last point gets extra emphasis" if is_en else "逐點展示 — 等速節奏，最後一點加強調",
                    "visual_guidance": "Number emoji + text for each point" if is_en else "數字 emoji + 說明文字",
                    "tips": [
                        "Keep each point to 5 seconds" if is_en else "每點 5 秒",
                        "Last point should be the strongest" if is_en else "最後一點最有份量",
                        "Use consistent visual style" if is_en else "使用一致的視覺風格",
                    ],
                },
                {
                    "type": "CTA",
                    "time_pct": 13,
                    "purpose": "Save prompt — listicles are high-save content" if is_en else "收藏提示 — 清單型是高收藏內容",
                    "visual_guidance": "Save button animation" if is_en else "收藏按鍵動畫",
                    "tips": ["'Save this for later' converts well for listicles" if is_en else "「收藏起來」對清單型轉化率高"],
                },
            ],
            "music_style": "Upbeat pop / rhythmic" if is_en else "Upbeat pop / 節奏明快",
        },
    }

    structure = structures.get(style, structures["educational"])

    # Compute actual timing from percentages
    for scene in structure["scene_flow"]:
        pct = scene["time_pct"]
        seconds = round(duration * pct / 100)
        scene["duration_seconds"] = max(1, seconds)

    editing_tips = [
        "Cut every 2-3 seconds to maintain attention" if is_en else "每 2-3 秒切換畫面",
        "Use pop-in text animations for key points" if is_en else "文字動畫用彈入效果",
        "Background music at 20% volume" if is_en else "背景音樂音量控制在 20%",
        "Add sound effects at transition points" if is_en else "在重點轉換時加 sound effect",
        "Completion rate is the #1 algorithm signal" if is_en else "完播率是演算法最重要的信號",
    ]

    return {
        "style": style,
        "style_label": structure["label"],
        "target_duration": duration,
        "scene_structure": structure["scene_flow"],
        "music_suggestion": structure["music_style"],
        "editing_tips": editing_tips,
        "algorithm_priority": "Completion rate > Saves > Shares > Comments" if is_en else "完播率 > 收藏 > 分享 > 留言",
        "instructions": (
            "Fill in each scene with original captions, voiceover text, and specific visual directions. "
            "Respect the timing allocation. The hook must grab attention in the first 3 seconds."
            if is_en else
            "為每個場景填入原創字幕、旁白和具體視覺指示。"
            "遵守時間分配。Hook 必須在前 3 秒抓住注意力。"
        ),
    }
