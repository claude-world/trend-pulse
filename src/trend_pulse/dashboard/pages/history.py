"""History analysis page — lifecycle + score over time."""
from __future__ import annotations


def render(agg, run_fn):
    """Render the history page."""
    try:
        import streamlit as st
        import plotly.express as px
    except ImportError:
        return

    st.header("Trend History & Lifecycle Analysis")

    col1, col2, col3 = st.columns(3)
    with col1:
        keyword = st.text_input("Keyword", "python", key="hi_kw")
    with col2:
        days = st.slider("Days", 7, 90, 30, key="hi_days")
    with col3:
        source = st.text_input("Source filter (blank=all)", "", key="hi_src")

    if st.button("Analyse", type="primary", key="hi_go"):
        with st.spinner("Querying..."):
            try:
                from ...core.intelligence.lifecycle import predict_lifecycle, lifecycle_emoji

                hist = run_fn(agg.history(keyword=keyword, days=days, source=source))
                # history() returns newest-first; reverse to oldest-first for lifecycle/charts
                records = list(reversed(hist.get("records", [])))

                if not records:
                    st.info(f"No history for '{keyword}'. Take a snapshot first.")
                    return

                scores = [r["score"] for r in records]
                ts = list(range(len(records)))
                current = scores[-1]  # most recent score (oldest-first list → last = newest)
                stage = predict_lifecycle(current, records)
                emoji = lifecycle_emoji(stage)

                m1, m2, m3 = st.columns(3)
                m1.metric("Current Score", f"{current:.1f}")
                m2.metric("Lifecycle", f"{emoji} {stage.value}")
                m3.metric("Records", len(records))

                fig = px.line(x=ts, y=scores,
                              labels={"x": "Record #", "y": "Score"},
                              title=f"'{keyword}' — Score Trajectory")
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Raw records"):
                    st.json(records[-10:])

            except Exception as e:
                st.error(f"Error: {e}")
