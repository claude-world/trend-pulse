"""
Hook, body, CTA templates and content types based on Meta's ranking patents.

Each hook category maps to specific patent mechanisms for algorithmic optimization.
"""

import random

# ═══════════════════════════════════════════════════════
# Hook Templates — organized by psychological trigger
# Each maps to specific patent mechanisms
# ═══════════════════════════════════════════════════════

HOOK_TEMPLATES = {
    "curiosity_gap": {
        "patent": "EdgeRank Weight + Andromeda Real-time",
        "templates": [
            "99% 的人不知道的{topic}真相",
            "我花了{time}才搞懂{topic}，結果發現...",
            "你以為的{topic} vs 實際的{topic}",
            "關於{topic}，我必須說一件不舒服的事實",
            "如果你還在用舊方法做{topic}，這篇會顛覆你",
            "{topic}最大的陷阱，99% 的人正在踩",
            "研究{topic}{time}後，我推翻了自己所有結論",
        ],
    },
    "controversy": {
        "patent": "Conversation Durability + Interest Vector",
        "templates": [
            "我知道這會得罪很多人，但{topic}...",
            "大家都在吹{topic}，我卻覺得...",
            "不好意思，{topic}根本是個偽命題",
            "為什麼我勸你別再{topic}了",
            "說一個關於{topic}的 unpopular opinion",
            "大部分人做{topic}的方式，根本是在浪費時間",
            "所有{topic}課程不會告訴你的一件事",
        ],
    },
    "story": {
        "patent": "EdgeRank Affinity + Interaction Flywheel",
        "templates": [
            "去年這個時候，我還在為{topic}焦慮...",
            "一個改變我看{topic}的瞬間",
            "從零開始做{topic}，{time}後我學到的事",
            "三年前我做了一個關於{topic}的決定...",
            "我曾經因為{topic}差點放棄，直到...",
            "分享一個關於{topic}的真實故事（不是雞湯）",
            "那天{topic}讓我徹底崩潰，現在回頭看...",
        ],
    },
    "data_driven": {
        "patent": "EdgeRank Weight (數字型 Hook CTR +37%)",
        "templates": [
            "做了{time}的{topic}，我總結了{count}個血淚教訓",
            "{topic}新手最常犯的{count}個錯誤（附解法）",
            "一張圖看懂{topic}的完整框架",
            "如果你正在{topic}，請先看完這{count}點",
            "沒人告訴你的{topic}{count}個隱藏成本",
            "{topic}的{count}個關鍵指標，你達標了幾個？",
            "我測試了{count}種{topic}方法，只有這個有效",
        ],
    },
    "engagement_trigger": {
        "patent": "Dear Algo Active Signal + Affinity",
        "templates": [
            "先別急著滑走，{topic}的這個細節很重要",
            "你對{topic}怎麼看？評論區見",
            "轉發這篇給正在{topic}的朋友",
            "如果這篇幫到你，幫我按讚讓更多人看到",
            "最後一點最重要，關於{topic}——",
            "{topic}你是哪一派？留言告訴我",
            "看完這篇你的想法會改變——關於{topic}",
        ],
    },
}

BODY_TEMPLATES = [
    "\n\n最近深入研究了{topic}，發現一個大多數人忽略的盲點：\n\n問題不在於你不夠努力，而是方向根本就錯了。\n\n以下是我整理的核心思路：",
    "\n\n身邊太多人在{topic}上踩坑了。\n\n不是能力問題，是認知問題。\n\n分享幾個改變我思維的關鍵轉折點：",
    "\n\n{topic}這件事，我研究了很久。\n\n最後得出一個違反直覺的結論：\n\n大家追求的那個方向，可能從一開始就是個陷阱。",
    "\n\n說一個關於{topic}的真實案例。\n\n不是要販賣焦慮，是希望更多人避開這個坑。",
    "\n\n在{topic}這條路上，我走了太多彎路。\n\n今天一次講清楚——少踩一個坑，就是賺到。",
    "\n\n很多人問我{topic}怎麼入門。\n\n老實說，入門不難，難的是不走偏。\n\n最重要的是第一步就走對方向：",
    "\n\n{topic}的真相比你想的殘酷。\n\n但正因為殘酷，提前知道的人才能贏。",
]

CTA_TEMPLATES = [
    "\n\n---\n你的看法呢？歡迎留言討論",
    "\n\n---\n如果你也有類似經歷，底下留言聊聊",
    "\n\n---\n覺得有幫助的話，轉發給需要的朋友",
    "\n\n---\n追蹤我，每天分享更多乾貨",
    "\n\n---\n同意的按讚，不同意的歡迎反駁",
    "\n\n---\n你最認同哪一點？留言告訴我",
    "\n\n---\n收藏這篇，下次遇到就不怕了",
]

CONTENT_TYPES = {
    "opinion":  {"label": "觀點輸出", "multiplier": 1.3, "best_hooks": ["curiosity_gap", "controversy"]},
    "story":    {"label": "故事敘事", "multiplier": 1.5, "best_hooks": ["story", "curiosity_gap"]},
    "debate":   {"label": "爭議討論", "multiplier": 1.6, "best_hooks": ["controversy", "engagement_trigger"]},
    "howto":    {"label": "教學攻略", "multiplier": 1.2, "best_hooks": ["data_driven", "curiosity_gap"]},
    "list":     {"label": "清單盤點", "multiplier": 1.1, "best_hooks": ["data_driven", "curiosity_gap"]},
    "question": {"label": "提問互動", "multiplier": 1.4, "best_hooks": ["engagement_trigger", "controversy"]},
    "news":     {"label": "熱點評論", "multiplier": 1.35, "best_hooks": ["curiosity_gap", "controversy"]},
    "meme":     {"label": "迷因梗圖", "multiplier": 1.25, "best_hooks": ["controversy", "engagement_trigger"]},
}


def fill_template(template: str, topic: str) -> str:
    """Fill in template variables with topic and randomized values."""
    replacements = {
        "{topic}": topic,
        "{time}": random.choice(["3個月", "半年", "一年", "2年", "3年", "5年"]),
        "{count}": str(random.randint(3, 9)),
    }
    result = template
    for k, v in replacements.items():
        result = result.replace(k, v)
    return result
