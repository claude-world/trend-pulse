"""
Platform specs and localization for cross-platform content adaptation.
"""

# ═══════════════════════════════════════════
# Platform Specs (Andromeda Cross-Platform)
# ═══════════════════════════════════════════

PLATFORM_SPECS = {
    "threads": {
        "max_chars": 500,
        "strengths": ["text-first", "conversation", "debate"],
        "format": {
            "zh-TW": "短文字 + 強 Hook + CTA",
            "en": "Short text + strong Hook + CTA",
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
            else:
                result[k] = v
        return result

    if platform and platform in PLATFORM_SPECS:
        return {"platform": platform, **_localize(PLATFORM_SPECS[platform])}

    return {
        name: {"platform": name, **_localize(spec)}
        for name, spec in PLATFORM_SPECS.items()
    }
