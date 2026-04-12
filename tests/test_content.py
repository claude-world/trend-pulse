"""Tests for content/ module — adapter, briefing (guides)."""

from trend_pulse.content.adapter import (
    PLATFORM_SPECS,
    get_platform_specs,
)
from trend_pulse.content.briefing import (
    get_content_brief,
    get_scoring_guide,
    get_review_checklist,
    get_reel_guide,
    _detect_language,
)


# ── Adapter ──


class TestAdapter:
    def test_platform_specs_has_3_platforms(self):
        # Originally 3 platforms; expanded to 8 in Phase 2
        assert {"threads", "instagram", "facebook"} <= set(PLATFORM_SPECS.keys())

    def test_platform_specs_bilingual(self):
        for name, spec in PLATFORM_SPECS.items():
            assert isinstance(spec["format"], dict), f"{name} format should be bilingual dict"
            assert "zh-TW" in spec["format"]
            assert "en" in spec["format"]

    def test_threads_has_official_fields(self):
        threads = PLATFORM_SPECS["threads"]
        assert "humor" in threads["strengths"]
        assert "media" in threads
        assert threads["media"]["video_max_minutes"] == 5
        assert threads["media"]["carousel_max"] == 20
        assert "posting_frequency" in threads
        assert "reply_strategy" in threads
        assert "non_recommendable" in threads
        assert len(threads["non_recommendable"]["en"]) >= 4
        assert len(threads["non_recommendable"]["zh-TW"]) >= 4
        assert "topic_tags" in threads
        assert "cross_promotion" in threads

    def test_threads_new_fields_localized(self):
        result = get_platform_specs("threads", "en")
        for field in ("posting_frequency", "reply_strategy", "topic_tags", "cross_promotion"):
            assert isinstance(result[field], str), f"{field} should be a localized string"
        assert isinstance(result["media"]["tip"], str), "media.tip should be a localized string"
        assert isinstance(result["non_recommendable"], list), "non_recommendable should resolve to list"
        result_zh = get_platform_specs("threads", "zh-TW")
        assert "週" in result_zh["posting_frequency"]
        assert isinstance(result_zh["non_recommendable"], list)
        assert any("標題黨" in item for item in result_zh["non_recommendable"])

    def test_get_platform_specs_single_en(self):
        result = get_platform_specs("threads", "en")
        assert result["platform"] == "threads"
        assert isinstance(result["format"], str)
        assert "Short text" in result["format"]

    def test_get_platform_specs_single_zh(self):
        result = get_platform_specs("threads", "zh-TW")
        assert result["platform"] == "threads"
        assert "短文字" in result["format"]

    def test_get_platform_specs_all(self):
        result = get_platform_specs("", "en")
        # Phase 2 expanded to 8 platforms; check core 3 + new ones present
        assert {"threads", "instagram", "facebook"} <= set(result.keys())
        for name, spec in result.items():
            assert isinstance(spec["format"], str)


# ── Briefing: Content Brief ──


class TestBriefing:
    def test_detect_language_chinese(self):
        assert _detect_language("AI工具") == "zh-TW"

    def test_detect_language_english(self):
        assert _detect_language("AI tools") == "en"

    def test_detect_language_japanese(self):
        assert _detect_language("AIツール") == "ja"

    def test_get_content_brief_basic(self):
        brief = get_content_brief("AI tools", "debate", "threads")
        assert brief["topic"] == "AI tools"
        assert brief["content_type"] == "debate"
        assert brief["language"] == "en"
        assert brief["char_limit"] == 500
        assert len(brief["hook_examples"]) > 0
        assert len(brief["cta_examples"]) > 0

    def test_get_content_brief_zh(self):
        brief = get_content_brief("AI工具", "debate", "threads")
        assert brief["language"] == "zh-TW"

    def test_get_content_brief_explicit_lang(self):
        brief = get_content_brief("AI", "debate", "threads", lang="en")
        assert brief["language"] == "en"

    def test_get_content_brief_has_patent_strategies(self):
        brief = get_content_brief("AI", "debate", "threads")
        assert len(brief["patent_strategies"]) == 5

    def test_get_content_brief_has_scoring_dimensions(self):
        brief = get_content_brief("AI", "debate", "threads")
        dims = brief["scoring_dimensions"]
        assert set(dims.keys()) == {
            "hook_power", "engagement_trigger", "conversation_durability",
            "velocity_potential", "format_score",
        }

    def test_get_content_brief_quality_gate(self):
        gate = get_content_brief("AI", "debate", "threads")["quality_gate"]
        assert gate["min_overall"] == 70
        assert gate["min_conversation"] == 55

    def test_get_content_brief_hook_examples_localized(self):
        brief_en = get_content_brief("AI", "debate", "threads", lang="en")
        brief_zh = get_content_brief("AI工具", "debate", "threads", lang="zh-TW")
        en_hooks = [h["example"] for h in brief_en["hook_examples"]]
        assert any("people" in h or "truth" in h or "wrong" in h for h in en_hooks)
        zh_hooks = [h["example"] for h in brief_zh["hook_examples"]]
        assert any("的" in h or "真相" in h or "人" in h for h in zh_hooks)


# ── Briefing: Scoring Guide ──


class TestScoringGuide:
    def test_scoring_guide_basic(self):
        guide = get_scoring_guide("en")
        assert "dimensions" in guide
        assert "grade_thresholds" in guide
        assert "quality_gate" in guide
        assert "instructions" in guide

    def test_scoring_guide_5_dimensions(self):
        dims = get_scoring_guide("en")["dimensions"]
        assert set(dims.keys()) == {
            "hook_power", "engagement_trigger", "conversation_durability",
            "velocity_potential", "format_score",
        }

    def test_scoring_guide_dimension_structure(self):
        dims = get_scoring_guide("en")["dimensions"]
        for name, dim in dims.items():
            assert "weight" in dim, f"{name} missing weight"
            assert "patent_basis" in dim, f"{name} missing patent_basis"
            assert "description" in dim, f"{name} missing description"
            assert "evaluate" in dim, f"{name} missing evaluate"
            assert "high_signals" in dim, f"{name} missing high_signals"
            assert "low_signals" in dim, f"{name} missing low_signals"
            assert len(dim["evaluate"]) >= 3

    def test_scoring_guide_weights_sum_to_1(self):
        dims = get_scoring_guide("en")["dimensions"]
        total = sum(d["weight"] for d in dims.values())
        assert abs(total - 1.0) < 0.001

    def test_scoring_guide_grade_thresholds(self):
        grades = get_scoring_guide("en")["grade_thresholds"]
        assert grades["S"]["min"] == 90
        assert grades["A"]["min"] == 80
        assert grades["B"]["min"] == 70
        assert grades["C"]["min"] == 55
        assert grades["D"]["min"] == 0

    def test_scoring_guide_zh(self):
        guide = get_scoring_guide("zh-TW")
        dims = guide["dimensions"]
        assert "注意力" in dims["hook_power"]["description"]
        assert "互動" in dims["engagement_trigger"]["description"]

    def test_scoring_guide_auto_lang(self):
        guide = get_scoring_guide("auto", topic="AI工具")
        assert "注意力" in guide["dimensions"]["hook_power"]["description"]

    def test_scoring_guide_auto_lang_english(self):
        guide = get_scoring_guide("auto", topic="AI tools")
        assert "attention" in guide["dimensions"]["hook_power"]["description"]


# ── Briefing: Review Checklist ──


class TestReviewChecklist:
    def test_review_checklist_basic(self):
        cl = get_review_checklist("threads", "en")
        assert cl["platform"] == "threads"
        assert cl["char_limit"] == 500
        assert "quality_gate" in cl
        assert "checklist" in cl
        assert "instructions" in cl

    def test_review_checklist_has_items(self):
        cl = get_review_checklist("threads", "en")
        assert len(cl["checklist"]) >= 9

    def test_review_checklist_item_structure(self):
        cl = get_review_checklist("threads", "en")
        for item in cl["checklist"]:
            assert "id" in item
            assert "category" in item
            assert "severity" in item
            assert "check" in item
            assert "pass_criteria" in item
            assert "auto_fixable" in item
            assert "fix_method" in item

    def test_review_checklist_has_critical_items(self):
        cl = get_review_checklist("threads", "en")
        critical = [i for i in cl["checklist"] if i["severity"] == "critical"]
        assert len(critical) >= 4

    def test_review_checklist_has_engagement_bait_check(self):
        cl = get_review_checklist("threads", "en")
        ids = [i["id"] for i in cl["checklist"]]
        assert "no_engagement_bait" in ids
        bait_item = next(i for i in cl["checklist"] if i["id"] == "no_engagement_bait")
        assert bait_item["severity"] == "critical"

    def test_review_checklist_has_media_enhancement(self):
        cl = get_review_checklist("threads", "en")
        ids = [i["id"] for i in cl["checklist"]]
        assert "media_enhancement" in ids

    def test_review_checklist_platform_limits(self):
        for platform, limit in [("threads", 500), ("instagram", 2200), ("facebook", 63206)]:
            cl = get_review_checklist(platform, "en")
            assert cl["char_limit"] == limit

    def test_review_checklist_zh(self):
        cl = get_review_checklist("threads", "zh-TW")
        assert "字" in cl["checklist"][0]["check"]

    def test_review_checklist_verdict_rules(self):
        cl = get_review_checklist("threads", "en")
        assert "pass" in cl["verdict_rules"]
        assert "fail" in cl["verdict_rules"]


# ── Briefing: Reel Guide ──


class TestReelGuide:
    def test_reel_guide_educational(self):
        guide = get_reel_guide("educational", 30, "en")
        assert guide["style"] == "educational"
        assert guide["target_duration"] == 30
        assert len(guide["scene_structure"]) >= 4
        assert "instructions" in guide
        assert "music_suggestion" in guide
        assert "editing_tips" in guide

    def test_reel_guide_storytelling(self):
        guide = get_reel_guide("storytelling", 30, "en")
        scene_types = [s["type"] for s in guide["scene_structure"]]
        assert "HOOK" in scene_types
        assert "CONFLICT" in scene_types
        assert "RESOLUTION" in scene_types

    def test_reel_guide_listicle(self):
        guide = get_reel_guide("listicle", 30, "en")
        scene_types = [s["type"] for s in guide["scene_structure"]]
        assert "HOOK" in scene_types
        assert "POINTS" in scene_types
        assert "CTA" in scene_types

    def test_reel_guide_scene_structure(self):
        guide = get_reel_guide("educational", 30, "en")
        for scene in guide["scene_structure"]:
            assert "type" in scene
            assert "time_pct" in scene
            assert "purpose" in scene
            assert "visual_guidance" in scene
            assert "tips" in scene
            assert "duration_seconds" in scene
            assert scene["duration_seconds"] >= 1

    def test_reel_guide_timing_sums_reasonable(self):
        guide = get_reel_guide("educational", 30, "en")
        total = sum(s["duration_seconds"] for s in guide["scene_structure"])
        assert 25 <= total <= 35

    def test_reel_guide_zh(self):
        guide = get_reel_guide("educational", 30, "zh-TW")
        assert any("秒" in t or "注意力" in t or "觀眾" in t
                    for s in guide["scene_structure"] for t in s["tips"])

    def test_reel_guide_different_durations(self):
        for dur in (15, 30, 60):
            guide = get_reel_guide("educational", dur, "en")
            assert guide["target_duration"] == dur

    def test_reel_guide_auto_lang(self):
        guide = get_reel_guide("educational", 30, "auto", topic="AI工具")
        assert any("秒" in t or "注意力" in t or "觀眾" in t
                    for s in guide["scene_structure"] for t in s["tips"])
