"""Real-time trend heatmap page."""
from __future__ import annotations


def render(agg, run_fn):
    """Render the real-time trends page. Imported by dashboard/app.py."""
    try:
        import streamlit as st
        import plotly.graph_objects as go
    except ImportError:
        return

    st.header("Real-time Trending Topics")
    col1, col2, col3 = st.columns(3)
    with col1:
        sources_input = st.text_input("Sources (blank=all)", key="rt_sources")
    with col2:
        geo = st.text_input("Geo (e.g. TW, US)", key="rt_geo")
    with col3:
        count = st.slider("Items per source", 5, 50, 20, key="rt_count")

    if st.button("Fetch Trends", type="primary", key="rt_fetch"):
        with st.spinner("Fetching..."):
            try:
                src_list = [s.strip() for s in sources_input.split(",") if s.strip()] or None
                data = run_fn(agg.trending(sources=src_list, geo=geo, count=count))
                merged = data.get("merged", [])[:50]
                if merged:
                    keywords = [i["keyword"] for i in merged]
                    scores = [i["score"] for i in merged]
                    fig = go.Figure(go.Bar(
                        x=scores[::-1], y=keywords[::-1],
                        orientation="h",
                        marker=dict(color=scores[::-1], colorscale="Viridis"),
                    ))
                    fig.update_layout(height=max(400, len(merged) * 20), margin=dict(l=200))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No data returned.")
            except Exception as e:
                st.error(f"Error: {e}")
