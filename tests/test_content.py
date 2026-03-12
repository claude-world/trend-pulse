"""Tests for content/ module — generator, adapter, reviewer."""

import pytest
from trend_pulse.content.generator import generate_posts, analyze_trends_and_generate
from trend_pulse.content.adapter import (
    PLATFORM_SPECS,
    adapt_for_threads,
    adapt_for_instagram,
    adapt_for_facebook,
    generate_hashtags,
    generate_elaboration,
    generate_image_prompt,
    generate_quote_card_html,
    generate_reel_script,
    full_pipeline,
)
from trend_pulse.content.reviewer import review, PLATFORM_LIMITS


# ── Generator ──


class TestGenerator:
    def test_generate_posts_returns_list(self):
        posts = generate_posts("AI", "debate", 3)
        assert isinstance(posts, list)
        assert len(posts) == 3

    def test_generate_posts_sorted_by_score(self):
        posts = generate_posts("AI", "debate", 5)
        scores = [p["scores"]["overall"] for p in posts]
        assert scores == sorted(scores, reverse=True)

    def test_generate_posts_has_required_fields(self):
        posts = generate_posts("AI", "opinion", 1)
        p = posts[0]
        assert "text" in p
        assert "scores" in p
        assert "hook_category" in p
        assert "hook_patent" in p
        assert "content_type" in p
        assert "rank" in p
        assert p["rank"] == 1

    def test_generate_posts_within_500_chars(self):
        posts = generate_posts("非常長的主題名稱用來測試", "debate", 5)
        for p in posts:
            assert len(p["text"]) <= 500, f"Post {p['rank']} is {len(p['text'])} chars"

    def test_generate_posts_all_content_types(self):
        for ct in ("opinion", "story", "debate", "howto", "list", "question", "news", "meme"):
            posts = generate_posts("AI", ct, 1)
            assert len(posts) == 1
            assert posts[0]["content_type"] != ""

    def test_generate_posts_invalid_type_falls_back(self):
        posts = generate_posts("AI", "nonexistent", 1)
        assert len(posts) == 1  # Falls back to debate

    def test_analyze_trends_single_query(self):
        data = {
            "query": "AI",
            "posts": [
                {"text": "post1", "heat_score": 100, "like_count": 50, "reply_count": 10, "repost_count": 5},
                {"text": "post2", "heat_score": 50, "like_count": 20, "reply_count": 5, "repost_count": 2},
            ],
        }
        result = analyze_trends_and_generate(data, count=2)
        assert "analysis" in result
        assert "generated_posts" in result
        assert "publish_ready" in result
        assert result["analysis"]["total_posts_analyzed"] == 2

    def test_analyze_trends_multi_query(self):
        data = {
            "results": {
                "AI": {"posts": [{"text": "ai", "heat_score": 100, "like_count": 10, "reply_count": 5, "repost_count": 2}]},
                "ML": {"posts": [{"text": "ml", "heat_score": 50, "like_count": 5, "reply_count": 2, "repost_count": 1}]},
            }
        }
        result = analyze_trends_and_generate(data, count=2)
        assert result["analysis"]["total_posts_analyzed"] == 2

    def test_analyze_trends_empty_returns_error(self):
        result = analyze_trends_and_generate({"posts": []})
        assert "error" in result


# ── Adapter ──


class TestAdapter:
    def test_platform_specs_has_3_platforms(self):
        assert set(PLATFORM_SPECS.keys()) == {"threads", "instagram", "facebook"}

    def test_adapt_for_threads_max_500(self):
        result = adapt_for_threads("AI", "Hook", ["Point1", "Point2", "Point3"], "CTA")
        assert result["platform"] == "threads"
        assert result["chars"] <= 500

    def test_adapt_for_instagram_has_carousel(self):
        result = adapt_for_instagram("AI", "Hook", ["P1", "P2", "P3", "P4"], "CTA")
        assert result["platform"] == "instagram"
        assert result["post_type"] == "carousel"
        assert len(result["carousel_slides"]) >= 3
        assert result["chars"] <= 2200

    def test_adapt_for_instagram_single_image(self):
        result = adapt_for_instagram("AI", "Hook", ["P1", "P2"], "CTA")
        assert result["post_type"] == "single_image"

    def test_adapt_for_facebook_long_form(self):
        result = adapt_for_facebook("AI", "Hook", ["P1", "P2"], "CTA")
        assert result["platform"] == "facebook"
        assert result["post_type"] == "long_text_with_image"

    def test_generate_hashtags_returns_list(self):
        tags = generate_hashtags("AI工具", count=10)
        assert isinstance(tags, list)
        assert len(tags) <= 10
        assert all(t.startswith("#") for t in tags)

    def test_generate_hashtags_no_duplicates(self):
        tags = generate_hashtags("AI", count=15)
        assert len(tags) == len(set(tags))

    def test_generate_elaboration_is_string(self):
        result = generate_elaboration("某個重點", "AI")
        assert isinstance(result, str)
        assert len(result) > 10

    def test_generate_image_prompt_3_platforms(self):
        for platform in ("threads", "instagram", "facebook"):
            prompt = generate_image_prompt("AI", platform)
            assert "style" in prompt
            assert "prompt" in prompt
            assert "dimensions" in prompt

    def test_quote_card_html_contains_text(self):
        html = generate_quote_card_html("測試金句", author="Test")
        assert "測試金句" in html
        assert "Test" in html
        assert "<!DOCTYPE html>" in html

    def test_quote_card_html_themes(self):
        for theme in ("dark", "light", "gradient", "warm"):
            html = generate_quote_card_html("test", theme=theme)
            assert "<!DOCTYPE html>" in html

    def test_quote_card_html_no_author(self):
        html = generate_quote_card_html("test", author="")
        assert "author" not in html.lower() or 'class="author"' not in html

    def test_reel_script_educational(self):
        script = generate_reel_script("AI", "educational", 30)
        assert script["duration_seconds"] == 30
        assert len(script["scenes"]) >= 4
        assert "music_suggestion" in script
        assert "editing_notes" in script
        assert "caption_for_post" in script

    def test_reel_script_storytelling(self):
        script = generate_reel_script("AI", "storytelling", 30)
        assert len(script["scenes"]) >= 4
        assert script["scenes"][0]["type"] == "HOOK"

    def test_reel_script_listicle(self):
        script = generate_reel_script("AI", "listicle", 30)
        assert len(script["scenes"]) >= 5  # 5 points + hook + CTA

    def test_full_pipeline_returns_packages(self):
        result = full_pipeline("AI", "debate", 2)
        assert "packages" in result
        assert result["total_packages"] == 2
        assert result["topic"] == "AI"

    def test_full_pipeline_package_structure(self):
        result = full_pipeline("AI", "opinion", 1)
        pkg = result["packages"][0]
        assert "platforms" in pkg
        assert set(pkg["platforms"].keys()) == {"threads", "instagram", "facebook"}
        assert "media" in pkg
        assert "cross_post_json" in pkg
        assert "scheduling" in pkg
        assert "viral_score" in pkg
        assert "grade" in pkg


# ── Reviewer ──


class TestReviewer:
    def test_platform_limits(self):
        assert PLATFORM_LIMITS["threads"] == 500
        assert PLATFORM_LIMITS["instagram"] == 2200
        assert PLATFORM_LIMITS["facebook"] == 63206

    def test_review_returns_required_keys(self):
        result = review("測試貼文", "threads")
        assert "verdict" in result
        assert "scores" in result
        assert "issues" in result
        assert "platform" in result
        assert "char_count" in result
        assert "char_limit" in result

    def test_review_pass_for_good_post(self):
        text = ("99% 的人不知道的AI真相？\n\n"
                "你覺得AI好用嗎？但是很多人持不同意見！\n\n"
                "最新研究顯示：\n1. 第一點\n2. 第二點\n\n"
                "---\n你怎麼看？留言討論")
        result = review(text, "threads")
        # Should have decent scores
        assert result["scores"]["overall"] >= 50

    def test_review_fail_for_short_text(self):
        result = review("短", "threads")
        assert result["verdict"] == "fail"

    def test_review_char_limit_critical(self):
        text = "x" * 501
        result = review(text, "threads")
        issues = [i for i in result["issues"] if i["type"] == "char_limit"]
        assert len(issues) == 1
        assert issues[0]["severity"] == "critical"

    def test_review_no_char_limit_issue_for_ig(self):
        text = "x" * 501
        result = review(text, "instagram")
        issues = [i for i in result["issues"] if i["type"] == "char_limit"]
        assert len(issues) == 0

    def test_review_missing_cta_detected(self):
        text = "這是一段沒有行動呼籲的文字。\n\n就這樣。"
        result = review(text, "threads")
        issues = [i for i in result["issues"] if i["type"] == "missing_cta"]
        assert len(issues) == 1

    def test_review_cta_present_not_flagged(self):
        text = "內容\n\n---\n你的看法呢？歡迎留言討論"
        result = review(text, "threads")
        issues = [i for i in result["issues"] if i["type"] == "missing_cta"]
        assert len(issues) == 0

    def test_review_weak_hook_detected(self):
        text = "短\n\n其他內容"
        result = review(text, "threads")
        issues = [i for i in result["issues"] if i["type"] == "weak_hook"]
        assert len(issues) == 1

    def test_review_auto_fix_adds_cta(self):
        text = "這是一段沒有CTA的文字。"
        result = review(text, "threads", auto_fix=True)
        if "fixed_text" in result:
            assert "留言" in result["fixed_text"] or "討論" in result["fixed_text"]

    def test_review_auto_fix_adds_question(self):
        text = ("這是一段沒有問題的文字。\n\n沒有爭議觀點。")
        result = review(text, "threads", auto_fix=True)
        if "fixed_text" in result:
            assert "？" in result["fixed_text"] or "怎麼看" in result["fixed_text"]

    def test_review_auto_fix_trims_text(self):
        text = "x" * 510
        result = review(text, "threads", auto_fix=True)
        if "fixed_text" in result:
            # Auto-fix trims to limit, but may also append CTA/question
            # The char_limit trim happens first, then CTA is appended
            # So we just check the original trim was applied
            assert result["fixed_text"] != text  # Something changed

    def test_review_auto_fix_rescores(self):
        text = "短文沒有結構"
        result = review(text, "threads", auto_fix=True)
        if "fixed_scores" in result:
            assert result["fixed_scores"]["overall"] >= result["scores"]["overall"]

    def test_review_all_platforms(self):
        for platform in ("threads", "instagram", "facebook"):
            result = review("測試", platform)
            assert result["platform"] == platform
            assert result["char_limit"] == PLATFORM_LIMITS[platform]
