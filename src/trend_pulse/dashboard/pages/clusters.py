"""Trend Knowledge Graph cluster visualization page."""
from __future__ import annotations


def render(agg, run_fn):
    """Render the clusters page."""
    try:
        import streamlit as st
    except ImportError:
        return

    st.header("Trend Knowledge Graph — Cross-Source Clusters")

    col1, col2 = st.columns(2)
    with col1:
        threshold = st.slider("Similarity threshold", 0.05, 0.5, 0.25, 0.05, key="cl_thr")
    with col2:
        count = st.slider("Items per source", 5, 50, 20, key="cl_count")

    if st.button("Build Clusters", type="primary", key="cl_build"):
        with st.spinner("Clustering..."):
            try:
                from ...core.intelligence.clusters import cluster_trends
                from ...sources.base import TrendItem

                raw = run_fn(agg.trending(count=count))
                items = []
                for src_result in raw.get("sources", {}).values():
                    for it in src_result:
                        items.append(TrendItem(
                            keyword=it.get("keyword", ""),
                            source=it.get("source", ""),
                            score=it.get("score", 0),
                        ))

                clusters = run_fn(cluster_trends(items, threshold=threshold))
                col_a, col_b = st.columns(2)
                col_a.metric("Clusters", len(clusters))
                col_b.metric("Cross-Source", sum(1 for c in clusters if c.cross_source))

                for i, c in enumerate(clusters[:15], 1):
                    badge = "🌐" if c.cross_source else "📍"
                    with st.expander(f"{i}. {badge} {c.topic} ({len(c.items)} items)"):
                        st.write(f"Score: {c.score:.1f} | Sources: {', '.join(c.sources)}")
                        st.write(f"Keywords: {', '.join(c.keywords[:8])}")
            except Exception as e:
                st.error(f"Error: {e}")
