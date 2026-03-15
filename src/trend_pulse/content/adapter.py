"""
Platform specs and localization for cross-platform content adaptation.
"""

# ═══════════════════════════════════════════
# Platform Specs (Andromeda Cross-Platform)
# ═══════════════════════════════════════════

PLATFORM_SPECS = {
    "threads": {
        "max_chars": 500,
        "strengths": ["text-first", "conversation", "debate", "humor"],
        "format": {
            "zh-TW": "短文字 + 強 Hook + CTA（圖文並茂效果顯著優於純文字）",
            "en": "Short text + strong Hook + CTA (text + media significantly outperforms text-only)",
        },
        "media": {
            "video_max_minutes": 5,
            "video_ratios": ["9:16", "16:9"],
            "carousel_max": 20,
            "tip": {
                "zh-TW": "圖文並茂的貼文表現顯著優於純文字（官方數據）",
                "en": "Posts with text + media perform significantly better than text-only (official data)",
            },
        },
        "posting_frequency": {
            "zh-TW": "每週 2-5 次（頻率越高，每篇平均觀看數越高）",
            "en": "2-5 times per week (higher frequency = more views per post)",
        },
        "reply_strategy": {
            "zh-TW": "回覆約佔 Threads 50% 觀看量——積極回覆留言",
            "en": "Replies account for ~50% of Threads views — reply actively to comments",
        },
        "non_recommendable": {
            "en": [
                "clickbait",
                "engagement bait (e.g. 'like if you agree')",
                "contests / giveaways",
                "cross-posted identical content from IG/FB",
            ],
            "zh-TW": [
                "標題黨",
                "互動誘餌（如「按讚=同意」）",
                "抽獎 / 贈品活動",
                "從 IG/FB 直接複製貼上的相同內容",
            ],
        },
        "topic_tags": {
            "zh-TW": "使用多字 Topic Tags + emoji 觸及感興趣的受眾",
            "en": "Use multi-word topic tags with emojis to reach interested audiences",
        },
        "cross_promotion": {
            "zh-TW": "將 Threads 貼文分享到 IG Stories 可增加觸及",
            "en": "Share Threads posts to IG Stories for extra reach",
        },
        "supported_features": {
            "en": [
                "TEXT — plain text (max 500 chars)",
                "IMAGE — single image (JPEG/PNG, max 8MB)",
                "VIDEO — single video (MP4/MOV, max 5min)",
                "CAROUSEL — 2-20 images/videos",
                "POLL — 2-4 options (max 25 chars each, 24hr duration)",
                "GIF — GIPHY attachment",
                "LINK_ATTACHMENT — link preview card",
                "TEXT_ATTACHMENT — long-form up to 10,000 chars with styling",
                "SPOILER_MEDIA — blur image/video/carousel",
                "SPOILER_TEXT — hide text ranges (up to 10 per post)",
                "GHOST_POST — disappears after 24 hours",
                "QUOTE_POST — quote another post",
                "REPLY_CONTROL — everyone / followers_only / mentioned_only / etc.",
                "TOPIC_TAG — categorize post (1-50 chars)",
                "ALT_TEXT — accessibility description (max 1000 chars)",
            ],
            "zh-TW": [
                "TEXT — 純文字（最多 500 字）",
                "IMAGE — 單張圖片（JPEG/PNG，最大 8MB）",
                "VIDEO — 單支影片（MP4/MOV，最長 5 分鐘）",
                "CAROUSEL — 2-20 張圖片/影片輪播",
                "POLL — 2-4 個選項的投票（每項最多 25 字，24 小時）",
                "GIF — GIPHY GIF 附件",
                "LINK_ATTACHMENT — 連結預覽卡片",
                "TEXT_ATTACHMENT — 長文最多 10,000 字 + 粗體/斜體等格式",
                "SPOILER_MEDIA — 模糊圖片/影片/輪播（防劇透）",
                "SPOILER_TEXT — 遮蔽指定文字段落（每篇最多 10 段）",
                "GHOST_POST — 24 小時後自動消失的限時貼文",
                "QUOTE_POST — 引用他人貼文",
                "REPLY_CONTROL — 回覆權限控制（所有人/粉絲/被提及者等）",
                "TOPIC_TAG — 主題標籤分類（1-50 字）",
                "ALT_TEXT — 無障礙圖片描述（最多 1000 字）",
            ],
        },
        "algo_priority": {
            "zh-TW": "對話持久性 (72hr+ multi-party)",
            "en": "Conversation durability (72hr+ multi-party)",
        },
        "best_times": ["21:00", "12:00", "17:30"],
    },
    "instagram": {
        "max_caption": 2200,
        "strengths": ["visual", "carousel", "reels", "stories"],
        "format": {
            "zh-TW": "視覺主導 + 教學輪播 + Reels 短影片",
            "en": "Visual-first + educational carousel + Reels short video",
        },
        "algo_priority": {
            "zh-TW": "Saves + Shares + Reels 完播率",
            "en": "Saves + Shares + Reels completion rate",
        },
        "best_times": ["12:00", "18:00", "21:00"],
    },
    "facebook": {
        "max_chars": 63206,
        "strengths": ["long-form", "link-sharing", "community", "video"],
        "format": {
            "zh-TW": "長文 + 圖片 + 連結 + 社團分享",
            "en": "Long-form + image + link + community sharing",
        },
        "algo_priority": {
            "zh-TW": "Meaningful Interaction (有意義的互動)",
            "en": "Meaningful Interaction (authentic engagement)",
        },
        "best_times": ["09:00", "13:00", "16:00"],
    },
}


def get_platform_specs(platform: str = "", lang: str = "zh-TW") -> dict:
    """
    Return platform specs with localized format/algo_priority strings.

    Args:
        platform: Platform name (threads/instagram/facebook). Empty = all platforms.
        lang: Language for text fields ("en" or "zh-TW").

    Returns:
        Dict with platform specs, localized text fields resolved to strings.
    """
    def _localize(spec: dict) -> dict:
        result = {}
        for k, v in spec.items():
            if isinstance(v, dict) and "en" in v and "zh-TW" in v:
                result[k] = v.get(lang, v.get("en", ""))
            elif isinstance(v, dict):
                result[k] = _localize(v)
            else:
                result[k] = v
        return result

    if platform and platform in PLATFORM_SPECS:
        return {"platform": platform, **_localize(PLATFORM_SPECS[platform])}

    return {
        name: {"platform": name, **_localize(spec)}
        for name, spec in PLATFORM_SPECS.items()
    }
