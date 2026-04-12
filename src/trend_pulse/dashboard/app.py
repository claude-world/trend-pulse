"""TrendPulse AI Dashboard — Streamlit entry point.

Run:
    streamlit run src/trend_pulse/dashboard/app.py

Requires:
    pip install 'trend-pulse[dashboard]'
    (streamlit, plotly, httpx already installed)
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

try:
    import streamlit as st
    import plotly.express as px
    import plotly.graph_objects as go
    _STREAMLIT_AVAILABLE = True
except ImportError:
    _STREAMLIT_AVAILABLE = False


def _run(coro):
    """Run async coroutine from sync Streamlit context.

    Streamlit runs its own event loop; we spin up a dedicated thread to
    avoid nesting asyncio.run() calls.
    """
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result(timeout=60)


@st.cache_resource
def _get_aggregator():
    """Cache TrendAggregator across reruns — avoids rebuilding plugin registry on every click."""
    from ..aggregator import TrendAggregator
    return TrendAggregator()


def main():
    if not _STREAMLIT_AVAILABLE:
        print("Install dashboard extras: pip install 'trend-pulse[dashboard]'")
        return

    st.set_page_config(
        page_title="TrendPulse AI",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ── Sidebar ──
    st.sidebar.title("TrendPulse AI")
    st.sidebar.caption("v2.0.0 · Global Trend Intelligence")

    page = st.sidebar.selectbox(
        "Navigation",
        ["Real-time Trends", "Trend Clusters", "Content Factory", "History"],
    )

    # ── Page routing ──
    if page == "Real-time Trends":
        _page_realtime()
    elif page == "Trend Clusters":
        _page_clusters()
    elif page == "Content Factory":
        _page_content_factory()
    elif page == "History":
        _page_history()


def _page_realtime():
    st.title("Real-time Trending Topics")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    col1, col2, col3 = st.columns(3)
    with col1:
        sources_input = st.text_input("Sources (comma-sep, blank=all)", "")
    with col2:
        geo = st.text_input("Geo (e.g. TW, US)", "")
    with col3:
        count = st.slider("Items per source", 5, 50, 20)

    if st.button("Fetch Trends", type="primary"):
        with st.spinner("Fetching trends..."):
            try:
                agg = _get_aggregator()
                src_list = [s.strip() for s in sources_input.split(",") if s.strip()] or None
                data = _run(agg.trending(sources=src_list, geo=geo, count=count))

                merged = data.get("merged", [])[:50]
                if merged:
                    st.subheader(f"Top {len(merged)} Trends (all sources merged)")
                    # Heatmap-style bar chart
                    keywords = [item["keyword"] for item in merged]
                    scores = [item["score"] for item in merged]
                    directions = [item.get("direction", "") for item in merged]

                    fig = go.Figure(go.Bar(
                        x=scores[::-1],
                        y=keywords[::-1],
                        orientation="h",
                        marker=dict(
                            color=scores[::-1],
                            colorscale="Viridis",
                        ),
                        text=[f"{d}" for d in directions[::-1]],
                        textposition="outside",
                    ))
                    fig.update_layout(height=max(400, len(merged) * 20), margin=dict(l=200))
                    st.plotly_chart(fig, use_container_width=True)

                    # Source breakdown
                    sources_data = data.get("sources", {})
                    if sources_data:
                        st.subheader("Source Breakdown")
                        source_counts = {src: len(v) for src, v in sources_data.items()}
                        fig2 = px.bar(
                            x=list(source_counts.keys()),
                            y=list(source_counts.values()),
                            labels={"x": "Source", "y": "Items"},
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.warning("No trends returned.")
            except Exception as e:
                st.error(f"Error: {e}")


def _page_clusters():
    st.title("Trend Knowledge Graph — Cross-Source Clusters")
    st.caption("Semantically grouped trends validated across multiple sources")

    col1, col2 = st.columns(2)
    with col1:
        threshold = st.slider("Similarity threshold", 0.05, 0.5, 0.25, 0.05)
    with col2:
        count = st.slider("Items per source", 5, 50, 20)

    if st.button("Build Clusters", type="primary"):
        with st.spinner("Clustering trends..."):
            try:
                from ..core.intelligence.clusters import cluster_trends
                from ..sources.base import TrendItem

                agg = _get_aggregator()
                raw = _run(agg.trending(count=count))
                items = []
                for src_result in raw.get("sources", {}).values():
                    for it in src_result:
                        items.append(TrendItem(
                            keyword=it.get("keyword", ""),
                            source=it.get("source", ""),
                            score=it.get("score", 0),
                        ))

                clusters = _run(cluster_trends(items, threshold=threshold))
                st.metric("Total Clusters", len(clusters))

                cross_count = sum(1 for c in clusters if c.cross_source)
                st.metric("Cross-Source Clusters", cross_count)

                for i, cluster in enumerate(clusters[:20], 1):
                    badge = "🌐 Cross-source" if cluster.cross_source else "📍 Single source"
                    with st.expander(
                        f"{i}. {cluster.topic} ({len(cluster.items)} items) — {badge}"
                    ):
                        st.write(f"**Score:** {cluster.score:.1f} | **Sources:** {', '.join(cluster.sources)}")
                        st.write(f"**Keywords:** {', '.join(cluster.keywords[:10])}")
            except Exception as e:
                st.error(f"Error: {e}")


def _page_content_factory():
    st.title("Agentic Content Factory")
    st.caption("6-agent pipeline: Researcher → Strategist → Copywriter → Optimizer → Compliance → Distributor")

    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input("Topic", "AI agents")
        brand_voice = st.selectbox("Brand Voice", ["casual", "professional", "provocative", "educational"])
    with col2:
        platforms_sel = st.multiselect(
            "Target Platforms",
            ["threads", "x", "instagram", "linkedin", "tiktok", "youtube", "xiaohongshu", "facebook"],
            default=["threads"],
        )

    if st.button("Generate Content", type="primary"):
        with st.spinner("Running 6-agent workflow..."):
            try:
                from ..core.agents.workflow import run_content_workflow
                state = _run(run_content_workflow(
                    platforms=platforms_sel or ["threads"],
                    brand_voice=brand_voice,
                    topic=topic,
                ))

                final = state.get("final_content", {})
                for plat, content in final.items():
                    st.subheader(f"{plat.capitalize()}")
                    st.text_area("", content, height=150, key=f"content_{plat}")
                    char_limits = {
                        "threads": 500, "x": 280, "instagram": 2200,
                        "linkedin": 3000, "tiktok": 2200, "youtube": 5000,
                        "xiaohongshu": 1000, "facebook": 63206,
                    }
                    limit = char_limits.get(plat, 500)
                    clen = len(content)
                    color = "green" if clen <= limit else "red"
                    st.markdown(f":{color}[{clen}/{limit} chars]")

                if state.get("errors"):
                    st.warning(f"Warnings: {', '.join(state['errors'])}")
            except Exception as e:
                st.error(f"Error: {e}")


def _page_history():
    st.title("Trend History & Lifecycle")

    keyword = st.text_input("Keyword to analyse", "python")
    days = st.slider("Days of history", 7, 90, 30)

    if st.button("Analyse", type="primary"):
        with st.spinner("Querying history..."):
            try:
                from ..core.intelligence.lifecycle import predict_lifecycle, lifecycle_emoji

                agg = _get_aggregator()
                hist = _run(agg.history(keyword=keyword, days=days))
                # history() returns newest-first; reverse to oldest-first for charts/lifecycle
                records = list(reversed(hist.get("records", [])))

                if records:
                    current_score = records[-1]["score"]
                    stage = predict_lifecycle(current_score, records)
                    emoji = lifecycle_emoji(stage)

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Current Score", f"{current_score:.1f}")
                    col2.metric("Lifecycle Stage", f"{emoji} {stage.value}")
                    col3.metric("Records Found", len(records))

                    scores = [r["score"] for r in records]
                    ts = [r.get("timestamp", i) for i, r in enumerate(records)]
                    fig = px.line(x=ts, y=scores, labels={"x": "Time", "y": "Score"},
                                  title=f"{keyword} — Score Over Time")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"No history found for '{keyword}'. Try taking a snapshot first.")
            except Exception as e:
                st.error(f"Error: {e}")


if __name__ == "__main__":
    main()
