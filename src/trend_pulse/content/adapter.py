"""
Cross-platform content adapter.

Adapts content for Threads, Instagram, and Facebook from a single topic.
Includes quote card HTML generation and Reel script generation.
"""

import html as html_mod
import random
from collections import Counter
from datetime import datetime

from ..patents.templates import (
    HOOK_TEMPLATES,
    BODY_TEMPLATES,
    CTA_TEMPLATES,
    CONTENT_TYPES,
    fill_template,
)
from ..patents.scorer import score_post
from .generator import generate_posts

# ═══════════════════════════════════════════
# Platform Specs (Andromeda Cross-Platform)
# ═══════════════════════════════════════════

PLATFORM_SPECS = {
    "threads": {
        "max_chars": 500,
        "strengths": ["text-first", "conversation", "debate"],
        "format": "短文字 + 強 Hook + CTA",
        "algo_priority": "對話持久性 (72hr+ multi-party)",
        "best_times": ["21:00", "12:00", "17:30"],
    },
    "instagram": {
        "max_caption": 2200,
        "strengths": ["visual", "carousel", "reels", "stories"],
        "format": "視覺主導 + 教學輪播 + Reels 短影片",
        "algo_priority": "Saves + Shares + Reels 完播率",
        "best_times": ["12:00", "18:00", "21:00"],
    },
    "facebook": {
        "max_chars": 63206,
        "strengths": ["long-form", "link-sharing", "community", "video"],
        "format": "長文 + 圖片 + 連結 + 社團分享",
        "algo_priority": "Meaningful Interaction (有意義的互動)",
        "best_times": ["09:00", "13:00", "16:00"],
    },
}


# ═══════════════════════════════════════════
# Platform Adapters
# ═══════════════════════════════════════════

def adapt_for_threads(topic: str, hook: str, body_points: list, cta: str) -> dict:
    """Generate Threads-optimized short text post (max 500 chars)."""
    body = "\n\n".join(body_points[:3])
    full = f"{hook}\n\n{body}\n\n---\n{cta}"
    if len(full) > 500:
        body = "\n\n".join(body_points[:2])
        full = f"{hook}\n\n{body}\n\n---\n{cta}"
    # Hard clamp to 500
    if len(full) > 500:
        full = full[:497] + "..."
    return {"platform": "threads", "text": full, "chars": len(full)}


def adapt_for_instagram(topic: str, hook: str, body_points: list, cta: str, has_image: bool = True) -> dict:
    """Generate Instagram-optimized content with caption + visual guidance."""
    caption_lines = [hook, ""]
    for point in body_points:
        caption_lines.append(f"◉ {point}")
    caption_lines.extend(["", f"💬 {cta}", ""])
    hashtags = generate_hashtags(topic, count=15)
    caption_lines.append(" ".join(hashtags))

    caption = "\n".join(caption_lines)
    if len(caption) > 2200:
        caption = caption[:2197] + "..."

    slides = [{"slide": 1, "type": "cover", "text": hook, "design": "Bold title on branded background"}]
    for i, point in enumerate(body_points[:5]):
        slides.append({"slide": i + 2, "type": "content", "text": point, "design": "Icon + short text on clean background"})
    slides.append({"slide": len(slides) + 1, "type": "cta", "text": cta, "design": "CTA with follow/save prompt"})

    return {
        "platform": "instagram",
        "caption": caption,
        "chars": len(caption),
        "post_type": "carousel" if len(body_points) > 2 else "single_image",
        "carousel_slides": slides,
        "image_prompt": generate_image_prompt(topic, "instagram"),
        "story_prompt": f"新貼文上線！滑過去看看關於{topic}的觀點 👉",
    }


def adapt_for_facebook(topic: str, hook: str, body_points: list, cta: str) -> dict:
    """Generate Facebook-optimized long-form content."""
    sections = [hook, "", "—" * 20, ""]
    for i, point in enumerate(body_points):
        sections.append(f"【第 {i + 1} 點】{point}")
        sections.append(generate_elaboration(point, topic))
        sections.append("")
    sections.extend(["—" * 20, "", f"💡 {cta}", "", f"#{''.join(topic.split())} #個人成長 #乾貨分享"])

    message = "\n".join(sections)
    return {
        "platform": "facebook",
        "message": message,
        "chars": len(message),
        "post_type": "long_text_with_image",
        "image_prompt": generate_image_prompt(topic, "facebook"),
    }


# ═══════════════════════════════════════════
# Helper Generators
# ═══════════════════════════════════════════

def generate_hashtags(topic: str, count: int = 15) -> list:
    """Generate relevant hashtags for Instagram."""
    base_tags = [
        "#threads", "#自媒體", "#個人品牌", "#內容創作", "#乾貨",
        "#知識分享", "#成長", "#學習", "#思維", "#觀點",
    ]
    # Split on spaces for multi-word topics; always add the joined form
    words = topic.split()
    topic_tags = [f"#{w}" for w in words if len(w) > 1]
    joined = "".join(words)
    if joined not in [t.lstrip("#") for t in topic_tags]:
        topic_tags.append(f"#{joined}")

    all_tags = topic_tags + base_tags
    random.shuffle(all_tags)
    return list(dict.fromkeys(all_tags))[:count]


def generate_elaboration(point: str, topic: str) -> str:
    """Generate a brief elaboration paragraph for Facebook long-form."""
    templates = [
        f"很多人在{topic}上忽略了這一點。但根據我的經驗，這恰恰是最容易拉開差距的地方。",
        "這不是什麼新概念，但真正能做到的人不到 10%。關鍵在於執行的細節。",
        f"如果你曾經在{topic}上卡關，很可能就是這個環節出了問題。",
        "我見過太多人在這一步犯錯。不是不努力，是方向需要調整。",
        "這一點可能會有爭議，但數據不會說謊。實際測試後你就會明白。",
    ]
    return random.choice(templates)


def generate_image_prompt(topic: str, platform: str) -> dict:
    """Generate AI image generation prompt based on platform needs."""
    if platform == "instagram":
        return {
            "style": "modern minimalist infographic",
            "prompt": (
                f"Create a clean, modern infographic-style image about {topic}. "
                f"Use a bold color palette (deep blue, white, accent orange). "
                f"Include geometric shapes, clean lines, and professional typography. "
                f"Aspect ratio: 1:1 (1080x1080). No text on the image itself."
            ),
            "dimensions": "1080x1080",
            "format": "PNG",
        }
    elif platform == "facebook":
        return {
            "style": "editorial hero image",
            "prompt": (
                f"Create a professional editorial-style hero image related to {topic}. "
                f"Cinematic lighting, shallow depth of field effect. "
                f"Aspect ratio: 16:9 (1200x630). Clean and modern aesthetic."
            ),
            "dimensions": "1200x630",
            "format": "PNG",
        }
    else:  # threads
        return {
            "style": "quote card background",
            "prompt": (
                f"Create an abstract gradient background for a quote card about {topic}. "
                f"Dark mode friendly, subtle texture. 1:1 ratio."
            ),
            "dimensions": "1080x1080",
            "format": "PNG",
        }


# ═══════════════════════════════════════════
# Quote Card Generator (HTML -> Screenshot)
# ═══════════════════════════════════════════

def generate_quote_card_html(text: str, author: str = "", theme: str = "dark") -> str:
    """Generate a quote card as HTML that can be screenshotted to image."""
    themes = {
        "dark": {"bg": "#0f172a", "text": "#f1f5f9", "accent": "#3b82f6", "sub": "#94a3b8"},
        "light": {"bg": "#ffffff", "text": "#0f172a", "accent": "#2563eb", "sub": "#64748b"},
        "gradient": {"bg": "linear-gradient(135deg, #1e3a5f, #0f172a)", "text": "#f1f5f9", "accent": "#38bdf8", "sub": "#94a3b8"},
        "warm": {"bg": "#1c1917", "text": "#fafaf9", "accent": "#f59e0b", "sub": "#a8a29e"},
    }
    t = themes.get(theme, themes["dark"])
    bg = t["bg"]

    safe_text = html_mod.escape(text)
    safe_author = html_mod.escape(author) if author else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  width: 1080px; height: 1080px;
  background: {bg};
  display: flex; align-items: center; justify-content: center;
  font-family: 'Noto Sans TC', 'Inter', system-ui, sans-serif;
}}
.card {{ width: 900px; padding: 80px; text-align: left; }}
.quote {{
  font-size: 42px; font-weight: 700; line-height: 1.6;
  color: {t['text']}; margin-bottom: 40px;
  border-left: 4px solid {t['accent']}; padding-left: 30px;
}}
.author {{ font-size: 20px; color: {t['sub']}; padding-left: 34px; }}
.accent {{ width: 60px; height: 4px; background: {t['accent']}; margin-bottom: 30px; }}
</style></head>
<body>
<div class="card">
  <div class="accent"></div>
  <div class="quote">{safe_text}</div>
  {f'<div class="author">&mdash; {safe_author}</div>' if safe_author else ''}
</div>
</body></html>"""


# ═══════════════════════════════════════════
# Reel / Short Video Script Generator
# ═══════════════════════════════════════════

def generate_reel_script(topic: str, style: str = "educational", duration: int = 30) -> dict:
    """
    Generate a Reels/Short video script with timing, visuals, and captions.
    Optimized for Instagram Reels algorithm (completion rate is king).

    Args:
        topic: Subject of the reel
        style: One of "educational", "storytelling", "listicle"
        duration: Target duration in seconds

    Returns:
        Dict with title, scenes, music suggestion, editing notes, and caption.
    """
    if style == "educational":
        return {
            "title": f"{topic}你必須知道的事",
            "duration_seconds": duration,
            "hook_seconds": 3,
            "scenes": [
                {"time": "0:00-0:03", "type": "HOOK", "visual": "面對鏡頭 / 文字動畫彈入", "caption": f"關於{topic}，大多數人都搞錯了...", "voiceover": f"如果你還在用舊方法做{topic}，這支影片會改變你的想法。", "note": "前 3 秒決定觀眾是否繼續看。"},
                {"time": "0:03-0:10", "type": "PROBLEM", "visual": "展示問題場景 / B-roll + 文字疊加", "caption": f"常見的{topic}錯誤", "voiceover": f"很多人做{topic}的第一步就走錯了。", "note": "建立痛點，讓觀眾產生共鳴。"},
                {"time": "0:10-0:22", "type": "SOLUTION", "visual": "步驟展示 / 螢幕錄製 / 文字列點", "caption": "正確的做法是...", "voiceover": f"其實{topic}的關鍵只有三點。", "note": "核心價值段。"},
                {"time": "0:22-0:27", "type": "PROOF", "visual": "成果展示 / 數據截圖 / 前後對比", "caption": "結果呢？", "voiceover": "用了這個方法之後，結果完全不一樣。", "note": "社會證明。"},
                {"time": "0:27-0:30", "type": "CTA", "visual": "指向追蹤按鍵 / 文字: 「追蹤學更多」", "caption": "追蹤我，每天學一招", "voiceover": "追蹤我，我每天分享一個實用技巧。", "note": "CTA 要自然。"},
            ],
            "music_suggestion": "Upbeat lo-fi / 輕快電子",
            "editing_notes": ["每 2-3 秒切換畫面", "文字動畫用彈入效果", "背景音樂音量控制在 20%", "加 sound effect 在重點轉換時"],
            "caption_for_post": f"關於{topic}，你確定方法是對的嗎？\n\n💬 你最認同哪一點？留言告訴我\n\n#{''.join(topic.split())} #reels #學習 #成長",
        }
    elif style == "storytelling":
        return {
            "title": f"我的{topic}故事",
            "duration_seconds": duration,
            "hook_seconds": 3,
            "scenes": [
                {"time": "0:00-0:03", "type": "HOOK", "visual": "情緒表情 / 戲劇性畫面", "caption": f"那次{topic}差點讓我崩潰...", "voiceover": f"這是我在{topic}上最慘痛的經歷。"},
                {"time": "0:03-0:12", "type": "SETUP", "visual": "敘事畫面 / 照片回顧", "caption": "事情是這樣的...", "voiceover": "那時候我以為一切都在掌控之中..."},
                {"time": "0:12-0:22", "type": "CONFLICT", "visual": "轉折場景 / 情緒轉換", "caption": "但是...", "voiceover": "直到有一天，所有計畫全部崩盤。"},
                {"time": "0:22-0:28", "type": "RESOLUTION", "visual": "正面結果 / 笑容", "caption": "後來我學到...", "voiceover": "這件事教會了我一個道理。"},
                {"time": "0:28-0:30", "type": "CTA", "visual": "文字: 「你有類似經歷嗎？」", "caption": "留言分享你的故事", "voiceover": "你有過類似的經歷嗎？"},
            ],
            "music_suggestion": "Emotional piano / 鋼琴配樂",
            "editing_notes": ["故事型要注重情緒節奏", "轉折點加重音效", "用色調變化暗示情緒轉換"],
            "caption_for_post": f"那次{topic}的經歷改變了我。\n\n你有過類似的故事嗎？\n\n#{''.join(topic.split())} #故事 #人生 #成長",
        }
    else:  # listicle
        return {
            "title": f"{topic}必知的 5 件事",
            "duration_seconds": duration,
            "scenes": [
                {"time": "0:00-0:03", "type": "HOOK", "caption": f"{topic}的 5 個真相", "visual": "數字 5 大字體彈入"},
                {"time": "0:03-0:08", "type": "POINT_1", "caption": "第一：...", "visual": "1️⃣ + 說明文字"},
                {"time": "0:08-0:13", "type": "POINT_2", "caption": "第二：...", "visual": "2️⃣ + 說明文字"},
                {"time": "0:13-0:18", "type": "POINT_3", "caption": "第三：...", "visual": "3️⃣ + 說明文字"},
                {"time": "0:18-0:23", "type": "POINT_4", "caption": "第四：...", "visual": "4️⃣ + 說明文字"},
                {"time": "0:23-0:28", "type": "POINT_5", "caption": "第五（最重要）", "visual": "5️⃣ + 放大強調"},
                {"time": "0:28-0:30", "type": "CTA", "caption": "收藏起來", "visual": "收藏按鍵動畫"},
            ],
            "music_suggestion": "Upbeat pop / 節奏明快",
            "editing_notes": ["每點 5 秒，節奏統一", "最後一點停留更久表示重要性"],
            "caption_for_post": f"{topic}你知道幾個？\n\n#{''.join(topic.split())} #知識 #必知",
        }


# ═══════════════════════════════════════════
# Full Pipeline: Topic -> 3-Platform Content
# ═══════════════════════════════════════════

def full_pipeline(topic: str, content_type: str = "debate", count: int = 3) -> dict:
    """
    Generate complete cross-platform content package from a single topic.

    Args:
        topic: Subject to create content about
        content_type: One of CONTENT_TYPES keys
        count: Number of content packages to generate

    Returns:
        Dict with packages for all 3 platforms, media prompts, and scheduling info.
    """
    posts = generate_posts(topic, content_type, count)

    packages = []
    for post in posts:
        text = post["text"]
        lines = text.split("\n")
        hook = lines[0] if lines else ""

        body_points = [
            f"第一，{topic}的核心不在技巧，在於認知框架",
            f"第二，90% 的人卡在{topic}的第一步就走偏了",
            "第三，最有效的方法往往違反直覺",
            "第四，持續做對的事比做很多事重要",
            f"第五，{topic}的終極秘密是——不斷迭代",
        ]
        cta = "你的看法呢？留言討論"

        threads_content = adapt_for_threads(topic, hook, body_points, cta)
        ig_content = adapt_for_instagram(topic, hook, body_points, cta)
        fb_content = adapt_for_facebook(topic, hook, body_points, cta)
        reel = generate_reel_script(topic, style="educational", duration=30)
        quote_card_html = generate_quote_card_html(hook, author="")

        packages.append({
            "topic": topic,
            "rank": post["rank"],
            "viral_score": post["scores"]["overall"],
            "grade": post["scores"]["grade"],
            "platforms": {
                "threads": threads_content,
                "instagram": ig_content,
                "facebook": fb_content,
            },
            "media": {
                "quote_card_html": quote_card_html,
                "image_prompts": {
                    "threads": generate_image_prompt(topic, "threads"),
                    "instagram": generate_image_prompt(topic, "instagram"),
                    "facebook": generate_image_prompt(topic, "facebook"),
                },
                "reel_script": reel,
            },
            "cross_post_json": {
                "threads": {"text": threads_content["text"]},
                "instagram": {"caption": ig_content["caption"], "type": ig_content["post_type"]},
                "facebook": {"message": fb_content["message"]},
            },
            "scheduling": {
                "threads_time": "21:00",
                "instagram_time": "12:00",
                "facebook_time": "09:00",
                "rationale": "基於 EdgeRank Time Decay + 各平台活躍高峰",
            },
        })

    return {
        "generated_at": datetime.now().isoformat(),
        "topic": topic,
        "content_type": content_type,
        "total_packages": len(packages),
        "packages": packages,
    }
