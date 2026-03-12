"""
Content review engine — integrates patent scoring with platform compliance.

Quality gate based on SKILL.md Phase 3.5:
- Viral Score >= 70
- Conversation Durability >= 55
- Hook grabs attention in first line
- CTA is clear and actionable
- Character count within platform limits
"""

import re

from ..patents.scorer import score_post

PLATFORM_LIMITS = {
    "threads": 500,
    "instagram": 2200,
    "facebook": 63206,
}


def review(text: str, platform: str = "threads", auto_fix: bool = False) -> dict:
    """
    Review content against patent scores and platform compliance.

    Args:
        text: The post content to review
        platform: Target platform (threads/instagram/facebook)
        auto_fix: If True, attempt to automatically fix issues

    Returns:
        Dict with:
            verdict: "pass" or "fail"
            scores: 5D patent scoring result
            issues: list of found issues
            fixed_text: corrected text (only if auto_fix=True and issues found)
    """
    scores = score_post(text)
    issues = []
    fixed_text = text

    char_limit = PLATFORM_LIMITS.get(platform, 500)

    # 1. Character limit check
    if len(text) > char_limit:
        issues.append({
            "type": "char_limit",
            "severity": "critical",
            "message": f"超出 {platform} 字數限制 ({len(text)}/{char_limit})",
        })
        if auto_fix:
            fixed_text = fixed_text[:char_limit - 3] + "..."

    # 2. Overall score check (>= 70)
    if scores["overall"] < 70:
        issues.append({
            "type": "low_score",
            "severity": "warning",
            "message": f"整體分數 {scores['overall']} < 70 (Grade {scores['grade']})",
        })

    # 3. Conversation durability check (>= 55)
    convo = scores["dimensions"]["conversation_durability"]
    if convo < 55:
        issues.append({
            "type": "low_conversation",
            "severity": "warning",
            "message": f"對話持久性 {convo} < 55",
        })
        if auto_fix and not re.search(r'[？?]$', fixed_text, re.MULTILINE):
            fixed_text = fixed_text.rstrip() + "\n\n你怎麼看？"

    # 4. Hook check (first line 10-45 chars)
    first_line = text.split('\n')[0] if '\n' in text else text[:50]
    if len(first_line) < 10:
        issues.append({
            "type": "weak_hook",
            "severity": "warning",
            "message": f"Hook 過短 ({len(first_line)} 字)，不夠吸引注意力",
        })
    elif len(first_line) > 45:
        issues.append({
            "type": "long_hook",
            "severity": "info",
            "message": f"Hook 偏長 ({len(first_line)} 字)，建議精簡至 45 字以內",
        })

    # 5. CTA check
    has_cta = bool(re.search(
        r'(留言|評論|分享|按讚|追蹤|轉發|收藏|你怎麼看|你呢|告訴我|歡迎)',
        text,
    ))
    if not has_cta:
        issues.append({
            "type": "missing_cta",
            "severity": "warning",
            "message": "缺少 CTA (行動呼籲)",
        })
        if auto_fix:
            fixed_text = fixed_text.rstrip() + "\n\n---\n你的看法呢？歡迎留言討論"

    # 6. Engagement trigger check
    has_question = bool(re.search(r'[？?]', text))
    if not has_question:
        issues.append({
            "type": "no_question",
            "severity": "info",
            "message": "沒有提問，建議加入問句觸發互動 (Dear Algo)",
        })

    # 7. Format check
    if platform == "threads" and '\n' not in text and len(text) > 100:
        issues.append({
            "type": "no_linebreak",
            "severity": "info",
            "message": "純文字無換行，建議分段提升可讀性",
        })

    # Determine verdict
    has_critical = any(i["severity"] == "critical" for i in issues)
    verdict = "fail" if has_critical or scores["overall"] < 70 or convo < 55 else "pass"

    # Re-check char limit after auto_fix appends (CTA/question may push over)
    if auto_fix and len(fixed_text) > char_limit:
        fixed_text = fixed_text[:char_limit - 3] + "..."

    # Re-score fixed text if modifications were made
    fixed_scores = None
    if auto_fix and fixed_text != text:
        fixed_scores = score_post(fixed_text)
        # Update verdict based on fixed scores
        if fixed_scores["overall"] >= 70 and fixed_scores["dimensions"]["conversation_durability"] >= 55:
            if len(fixed_text) <= char_limit:
                verdict = "pass (after auto-fix)"

    result = {
        "verdict": verdict,
        "scores": scores,
        "platform": platform,
        "char_count": len(text),
        "char_limit": char_limit,
        "issues": issues,
        "issue_count": len(issues),
    }

    if auto_fix and fixed_text != text:
        result["fixed_text"] = fixed_text
        result["fixed_scores"] = fixed_scores

    return result
