"""
Viral post generator — creates scored posts optimized for Meta's ranking patents.

Generates posts using hook/body/CTA templates, scores them, and returns
ranked results ready for publishing.
"""

import random
from datetime import datetime

from ..patents.templates import (
    HOOK_TEMPLATES,
    BODY_TEMPLATES,
    CTA_TEMPLATES,
    CONTENT_TYPES,
    fill_template,
)
from ..patents.scorer import score_post


def generate_posts(topic: str, content_type: str = "debate", count: int = 5) -> list:
    """
    Generate scored viral posts for a given topic and content type.

    Args:
        topic: The subject to generate posts about
        content_type: One of CONTENT_TYPES keys (opinion/story/debate/howto/list/question/news/meme)
        count: Number of posts to generate

    Returns:
        List of post dicts sorted by score, each with text, scores, and metadata.
    """
    ctype = CONTENT_TYPES.get(content_type, CONTENT_TYPES["debate"])
    preferred_hooks = ctype["best_hooks"]

    posts = []
    used_hooks = set()

    for i in range(count):
        # Cycle through hook categories, preferring the type's best hooks
        if i < len(preferred_hooks):
            hook_cat = preferred_hooks[i]
        else:
            all_cats = list(HOOK_TEMPLATES.keys())
            hook_cat = all_cats[i % len(all_cats)]

        templates = HOOK_TEMPLATES[hook_cat]["templates"]

        # Pick a template we haven't used yet
        available = [t for t in templates if t not in used_hooks]
        if not available:
            available = templates
        template = random.choice(available)
        used_hooks.add(template)

        hook = fill_template(template, topic)
        body = fill_template(random.choice(BODY_TEMPLATES), topic)
        cta = random.choice(CTA_TEMPLATES)

        full_text = hook + body + cta

        # Ensure within 500 char limit
        if len(full_text) > 500:
            max_body = max(0, 500 - len(hook) - len(cta) - 3)
            body = body[:max_body] + "..."
            full_text = hook + body + cta

        scores = score_post(full_text)

        posts.append({
            "index": i,
            "hook_category": hook_cat,
            "hook_patent": HOOK_TEMPLATES[hook_cat]["patent"],
            "content_type": ctype["label"],
            "type_multiplier": ctype["multiplier"],
            "text": full_text,
            "text_length": len(full_text),
            "scores": scores,
        })

    # Sort by score descending
    posts.sort(key=lambda p: p["scores"]["overall"], reverse=True)

    # Re-index after sort
    for i, p in enumerate(posts):
        p["rank"] = i + 1

    return posts


def analyze_trends_and_generate(search_results: dict, count: int = 5) -> dict:
    """
    Analyze search results, identify hottest topics, and generate posts.

    Args:
        search_results: Output from Threads search or trend aggregation.
            Supports both single-query {"posts": [...]} and
            multi-query {"results": {"query": {"posts": [...]}}} formats.
        count: Number of posts to generate

    Returns:
        Dict with analysis summary, generated posts, and publish-ready subset.
    """
    # Handle both single-query and multi-query formats
    if "results" in search_results:
        all_posts = []
        for query, data in search_results["results"].items():
            posts = data.get("posts", [])
            for p in posts:
                p["source_query"] = query
            all_posts.extend(posts)
    else:
        all_posts = search_results.get("posts", [])
        for p in all_posts:
            p["source_query"] = search_results.get("query", "")

    if not all_posts:
        return {"error": "No posts found in search results"}

    # Sort by heat and extract topic patterns
    all_posts.sort(key=lambda p: p.get("heat_score", 0), reverse=True)
    top_posts = all_posts[:10]

    # Determine best content types based on engagement patterns
    total_replies = sum(p.get("reply_count", 0) for p in top_posts)
    total_reposts = sum(p.get("repost_count", 0) for p in top_posts)

    if total_replies > total_reposts * 2:
        best_type = "debate"
    elif total_reposts > total_replies:
        best_type = "howto"
    else:
        best_type = "opinion"

    # Generate posts for the top query/topic (deterministic: pick most common)
    from collections import Counter
    query_counts = Counter(p.get("source_query", "") for p in top_posts)
    topic = query_counts.most_common(1)[0][0] if query_counts else "trending"

    generated = generate_posts(topic, best_type, count)

    return {
        "analysis": {
            "total_posts_analyzed": len(all_posts),
            "top_heat_score": all_posts[0].get("heat_score", 0),
            "dominant_topic": topic,
            "recommended_type": best_type,
            "avg_engagement": {
                "likes": sum(p.get("like_count", 0) for p in top_posts) / max(len(top_posts), 1),
                "replies": sum(p.get("reply_count", 0) for p in top_posts) / max(len(top_posts), 1),
                "reposts": sum(p.get("repost_count", 0) for p in top_posts) / max(len(top_posts), 1),
            },
        },
        "generated_posts": generated,
        "publish_ready": [p for p in generated if p["scores"]["overall"] >= 70],
    }
