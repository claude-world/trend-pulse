"""Tests for patents/ module — templates, scorer, database."""

import pytest
from trend_pulse.patents.templates import (
    HOOK_TEMPLATES,
    HOOK_TEMPLATES_EN,
    BODY_TEMPLATES,
    BODY_TEMPLATES_EN,
    CTA_TEMPLATES,
    CTA_TEMPLATES_EN,
    CONTENT_TYPES,
    fill_template,
    fill_template_en,
    get_templates,
)
from trend_pulse.patents.scorer import score_post
from trend_pulse.patents.database import (
    PATENTS,
    get_patent,
    get_all_strategies,
    get_scoring_weights,
)


# ── Templates ──


class TestTemplates:
    def test_hook_templates_has_5_categories(self):
        assert len(HOOK_TEMPLATES) == 5
        expected = {"curiosity_gap", "controversy", "story", "data_driven", "engagement_trigger"}
        assert set(HOOK_TEMPLATES.keys()) == expected

    def test_hook_templates_en_has_5_categories(self):
        assert len(HOOK_TEMPLATES_EN) == 5
        assert set(HOOK_TEMPLATES_EN.keys()) == set(HOOK_TEMPLATES.keys())

    def test_each_hook_category_has_patent_and_templates(self):
        for cat, data in HOOK_TEMPLATES.items():
            assert "patent" in data, f"{cat} missing patent"
            assert "templates" in data, f"{cat} missing templates"
            assert len(data["templates"]) >= 5, f"{cat} has too few templates"

    def test_each_en_hook_category_has_patent_and_templates(self):
        for cat, data in HOOK_TEMPLATES_EN.items():
            assert "patent" in data, f"EN {cat} missing patent"
            assert "templates" in data, f"EN {cat} missing templates"
            assert len(data["templates"]) >= 5, f"EN {cat} has too few templates"

    def test_body_templates_not_empty(self):
        assert len(BODY_TEMPLATES) >= 5

    def test_body_templates_en_not_empty(self):
        assert len(BODY_TEMPLATES_EN) >= 5

    def test_cta_templates_not_empty(self):
        assert len(CTA_TEMPLATES) >= 5

    def test_cta_templates_en_not_empty(self):
        assert len(CTA_TEMPLATES_EN) >= 5

    def test_content_types_has_8_types(self):
        assert len(CONTENT_TYPES) == 8
        expected = {"opinion", "story", "debate", "howto", "list", "question", "news", "meme"}
        assert set(CONTENT_TYPES.keys()) == expected

    def test_each_content_type_has_required_fields(self):
        for ct, data in CONTENT_TYPES.items():
            assert "label" in data, f"{ct} missing label"
            assert "multiplier" in data, f"{ct} missing multiplier"
            assert "best_hooks" in data, f"{ct} missing best_hooks"
            assert data["multiplier"] >= 1.0

    def test_fill_template_replaces_topic(self):
        result = fill_template("{topic}是什麼", "AI")
        assert "AI是什麼" == result

    def test_fill_template_replaces_time(self):
        result = fill_template("研究了{time}", "AI")
        assert "{time}" not in result
        assert "研究了" in result

    def test_fill_template_replaces_count(self):
        result = fill_template("{count}個重點", "AI")
        assert "{count}" not in result
        # Count should be 3-9
        num = int(result.replace("個重點", ""))
        assert 3 <= num <= 9

    def test_fill_template_en_replaces_topic(self):
        result = fill_template_en("About {topic}", "AI")
        assert result == "About AI"

    def test_fill_template_en_replaces_time(self):
        result = fill_template_en("After {time} of work", "AI")
        assert "{time}" not in result

    def test_fill_template_en_replaces_count(self):
        result = fill_template_en("{count} key points", "AI")
        assert "{count}" not in result

    def test_fill_template_no_placeholders_left(self):
        for cat_data in HOOK_TEMPLATES.values():
            for tmpl in cat_data["templates"]:
                result = fill_template(tmpl, "測試主題")
                assert "{topic}" not in result
                assert "{time}" not in result
                assert "{count}" not in result

    def test_fill_template_en_no_placeholders_left(self):
        for cat_data in HOOK_TEMPLATES_EN.values():
            for tmpl in cat_data["templates"]:
                result = fill_template_en(tmpl, "test topic")
                assert "{topic}" not in result
                assert "{time}" not in result
                assert "{count}" not in result

    def test_get_templates_zh(self):
        hooks, body, cta = get_templates("zh-TW")
        assert hooks is HOOK_TEMPLATES
        assert body is BODY_TEMPLATES
        assert cta is CTA_TEMPLATES

    def test_get_templates_en(self):
        hooks, body, cta = get_templates("en")
        assert hooks is HOOK_TEMPLATES_EN
        assert body is BODY_TEMPLATES_EN
        assert cta is CTA_TEMPLATES_EN

    def test_get_templates_default_is_zh(self):
        hooks, _, _ = get_templates()
        assert hooks is HOOK_TEMPLATES


# ── Scorer ──


class TestScorer:
    def test_score_post_returns_required_keys(self):
        result = score_post("測試貼文")
        assert "overall" in result
        assert "grade" in result
        assert "dimensions" in result
        assert "text_length" in result
        assert "within_api_limit" in result
        assert "suggestions" in result

    def test_score_post_5_dimensions(self):
        dims = score_post("測試")["dimensions"]
        expected = {"hook_power", "engagement_trigger", "conversation_durability",
                    "velocity_potential", "format_score"}
        assert set(dims.keys()) == expected

    def test_score_range_0_to_100(self):
        result = score_post("一般貼文")
        assert 0 <= result["overall"] <= 100
        for dim, val in result["dimensions"].items():
            assert 0 <= val <= 98, f"{dim}={val} out of range"

    def test_grade_s_for_high_score(self):
        # Construct a post that should score very high
        text = ("99% 的人不知道的AI真相？\n\n"
                "你覺得AI是真的嗎？但是很多人不同意！\n\n"
                "最新數據顯示，緊急速報：\n\n"
                "1. 第一點\n2. 第二點\n3. 第三點\n\n"
                "---\n你怎麼看？留言討論，轉發給朋友")
        result = score_post(text)
        assert result["grade"] in ("S", "A")

    def test_grade_d_for_short_text(self):
        result = score_post("短")
        assert result["grade"] == "D"

    def test_within_api_limit_true_for_short(self):
        assert score_post("短文")["within_api_limit"] is True

    def test_within_api_limit_false_for_long(self):
        text = "x" * 501
        assert score_post(text)["within_api_limit"] is False

    def test_suggestions_for_weak_post(self):
        result = score_post("短")
        assert len(result["suggestions"]) > 0

    def test_hook_power_boosted_by_question(self):
        without_q = score_post("AI是很重要的技術")["dimensions"]["hook_power"]
        with_q = score_post("AI是很重要的技術？")["dimensions"]["hook_power"]
        assert with_q > without_q

    def test_engage_boosted_by_cta(self):
        without = score_post("AI很重要")["dimensions"]["engagement_trigger"]
        with_cta = score_post("AI很重要，你留言告訴我怎麼看")["dimensions"]["engagement_trigger"]
        assert with_cta > without

    def test_convo_boosted_by_controversy(self):
        without = score_post("AI很好用")["dimensions"]["conversation_durability"]
        with_c = score_post("但是AI的爭議很大，你覺得呢？")["dimensions"]["conversation_durability"]
        assert with_c > without

    def test_velocity_boosted_by_urgency(self):
        without = score_post("AI的發展趨勢")["dimensions"]["velocity_potential"]
        with_v = score_post("最新速報！AI今天重磅發布")["dimensions"]["velocity_potential"]
        assert with_v > without

    def test_format_boosted_by_structure(self):
        flat = score_post("這是一段沒有結構的文字")["dimensions"]["format_score"]
        structured = score_post("標題：重點\n\n1. 第一點\n\n2. 第二點\n\n3. 第三點")["dimensions"]["format_score"]
        assert structured > flat

    # ── English scoring tests ──

    def test_english_hook_power(self):
        """English hook keywords should boost hook_power."""
        without = score_post("AI is important technology")["dimensions"]["hook_power"]
        with_hook = score_post("The truth about AI nobody talks about?")["dimensions"]["hook_power"]
        assert with_hook > without

    def test_english_engagement(self):
        """English engagement keywords should boost engagement_trigger."""
        without = score_post("AI is a hot topic")["dimensions"]["engagement_trigger"]
        with_eng = score_post("What do you think about AI? Share your thoughts")["dimensions"]["engagement_trigger"]
        assert with_eng > without

    def test_english_conversation(self):
        """English controversy keywords should boost conversation_durability."""
        without = score_post("AI is useful")["dimensions"]["conversation_durability"]
        with_convo = score_post("But the controversial debate about AI opinion is heated. What do you think?")["dimensions"]["conversation_durability"]
        assert with_convo > without

    def test_english_velocity(self):
        """English urgency keywords should boost velocity_potential."""
        without = score_post("AI development trends are interesting")["dimensions"]["velocity_potential"]
        with_vel = score_post("Breaking today: exclusive first time AI launch!")["dimensions"]["velocity_potential"]
        assert with_vel > without

    def test_english_overall_decent_score(self):
        """A well-crafted English post should score > 50 (not < 40 as before)."""
        text = "The truth about AI nobody talks about. What do you think?"
        result = score_post(text)
        assert result["overall"] > 50


# ── Database ──


class TestDatabase:
    def test_patents_has_7_entries(self):
        assert len(PATENTS) == 7

    def test_patent_keys(self):
        expected = {"edgerank", "story_viewer_tuple", "interaction_flywheel",
                    "social_feed", "andromeda", "conversation_durability", "dear_algo"}
        assert set(PATENTS.keys()) == expected

    def test_each_patent_has_name_and_strategy(self):
        for key, p in PATENTS.items():
            assert "name" in p, f"{key} missing name"
            assert "strategy" in p, f"{key} missing strategy"

    def test_get_patent_returns_dict(self):
        p = get_patent("edgerank")
        assert p is not None
        assert p["name"] == "EdgeRank 三維排序公式"

    def test_get_patent_returns_none_for_unknown(self):
        assert get_patent("nonexistent") is None

    def test_get_all_strategies_returns_7(self):
        strategies = get_all_strategies()
        assert len(strategies) == 7
        assert all(isinstance(v, str) for v in strategies.values())

    def test_scoring_weights_sum_to_1(self):
        weights = get_scoring_weights()
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_scoring_weights_match_scorer(self):
        weights = get_scoring_weights()
        expected_dims = {"hook_power", "engagement_trigger", "conversation_durability",
                         "velocity_potential", "format_score"}
        assert set(weights.keys()) == expected_dims
