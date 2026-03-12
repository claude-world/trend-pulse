"""
Patent-derived 5-dimension post scorer.

Scores text content on 5 dimensions mapped to Meta's ranking patents:
1. Hook Power (EdgeRank Weight + Andromeda)
2. Engagement Trigger (Story-Viewer Tuple + Dear Algo)
3. Conversation Durability (Threads AI 72hr window)
4. Velocity Potential (Andromeda Real-time Signal)
5. Format Score (Multi-modal Indexing)

Pure regex + heuristic — no ML dependencies.
"""

import re


def score_post(text: str) -> dict:
    """
    Score a post on 5 patent-derived dimensions.

    Returns dict with:
        overall: int (0-100)
        grade: str (S/A/B/C/D)
        dimensions: dict of 5 scores
        text_length: int
        within_api_limit: bool
        suggestions: list[str]
    """
    length = len(text)

    # 1. Hook Power (EdgeRank Weight + Andromeda)
    hook = 30
    if re.search(r'[？?]', text):
        hook += 15
    if re.search(r'[！!]', text):
        hook += 10
    if re.search(r'\d+', text):
        hook += 12
    first_line = text.split('\n')[0] if '\n' in text else text[:50]
    if 10 < len(first_line) < 45:
        hook += 15
    if re.search(r'(真相|秘密|其實|沒人|不知道|才發現|顛覆|陷阱|血淚)', text):
        hook += 12
    if re.search(r'(truth|secret|actually|nobody|discovered|shocking|trap|mistake)', text, re.IGNORECASE):
        hook += 12
    if re.search(r'(99%|90%|\d+%)', text):
        hook += 8
    hook = min(98, hook)

    # 2. Engagement Trigger (Story-Viewer Tuple + Dear Algo)
    engage = 35
    if re.search(r'(你|你們|大家)', text):
        engage += 15
    if re.search(r'\b(you|your|everyone)\b', text, re.IGNORECASE):
        engage += 15
    if re.search(r'(留言|評論|分享|按讚|追蹤|轉發|收藏)', text):
        engage += 18
    if re.search(r'\b(comment|share|like|follow|save|repost)\b', text, re.IGNORECASE):
        engage += 18
    if re.search(r'[？?]$', text, re.MULTILINE):
        engage += 12
    if '\n' in text:
        engage += 8
    if re.search(r'(怎麼看|你呢|同意嗎|覺得呢|哪一派|告訴我)', text):
        engage += 15
    if re.search(r'\b(what do you think|agree|thoughts|which side|tell me)\b', text, re.IGNORECASE):
        engage += 15
    engage = min(98, engage)

    # 3. Conversation Durability (Threads AI — 72hr / 3+ participants)
    convo = 30
    if re.search(r'(但是|然而|不過|可是|反而|偏偏)', text):
        convo += 15
    if re.search(r'\b(but|however|yet|instead|surprisingly)\b', text, re.IGNORECASE):
        convo += 15
    q_count = len(re.findall(r'[？?]', text))
    if q_count >= 2:
        convo += 12
    if re.search(r'(爭議|討論|辯論|意見|觀點|unpopular)', text):
        convo += 18
    if re.search(r'\b(controversial|debate|opinion|unpopular)\b', text, re.IGNORECASE):
        convo += 18
    if length > 100:
        convo += 10
    if re.search(r'(你覺得|同意嗎|怎麼看|哪一派)', text):
        convo += 15
    if re.search(r'\b(what do you think|agree|thoughts|which side|tell me)\b', text, re.IGNORECASE):
        convo += 15
    convo = min(98, convo)

    # 4. Velocity Potential (Andromeda Real-time Signal)
    vel = 40
    if hook > 70:
        vel += 20
    if re.search(r'(緊急|剛剛|最新|breaking|速報|今天|重磅)', text):
        vel += 15
    if re.search(r'\b(urgent|just now|latest|breaking|today|exclusive|first time)\b', text, re.IGNORECASE):
        vel += 15
    if 50 <= length <= 300:
        vel += 12
    if re.search(r'(第一|首次|獨家|首度)', text):
        vel += 10
    vel = min(98, vel)

    # 5. Format Score (Multi-modal Indexing)
    fmt = 40
    lines = [line for line in text.split('\n') if line.strip()]
    if len(lines) >= 3:
        fmt += 15
    if '\n\n' in text:
        fmt += 10
    if 80 <= length <= 500:
        fmt += 15
    if re.search(r'[：:]', text):
        fmt += 8
    if re.search(r'\d[.、)）]', text):
        fmt += 10
    fmt = min(98, fmt)

    # Composite score (weighted by patent importance)
    overall = round(hook * 0.25 + engage * 0.25 + convo * 0.20 + vel * 0.15 + fmt * 0.15)

    # Grade
    if overall >= 90:
        grade = "S"
    elif overall >= 80:
        grade = "A"
    elif overall >= 70:
        grade = "B"
    elif overall >= 55:
        grade = "C"
    else:
        grade = "D"

    # Suggestions
    suggestions = []
    if hook < 60:
        suggestions.append("Hook 弱：加數字/提問/懸念 (EdgeRank Weight)")
    if engage < 60:
        suggestions.append("互動不足：加提問或 CTA (Dear Algo)")
    if convo < 60:
        suggestions.append("對話潛力低：加爭議觀點 (Conversation Durability)")
    if vel < 60:
        suggestions.append("爆發力弱：加即時吸引力 (Andromeda)")
    if fmt < 60:
        suggestions.append("排版弱：善用換行分段 (Multi-modal)")
    if length > 500:
        suggestions.append("超出 500 字 API 限制！必須精簡")
    if length < 50:
        suggestions.append("內容過短，展開觀點")
    if not re.search(r'[？?]', text):
        suggestions.append("建議加提問觸發留言 (Dear Algo)")

    return {
        "overall": overall,
        "grade": grade,
        "dimensions": {
            "hook_power": hook,
            "engagement_trigger": engage,
            "conversation_durability": convo,
            "velocity_potential": vel,
            "format_score": fmt,
        },
        "text_length": length,
        "within_api_limit": length <= 500,
        "suggestions": suggestions,
    }
