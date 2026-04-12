"""Campaign management page — content generation and calendar."""
from __future__ import annotations


def render(agg, run_fn):
    """Render the campaign page."""
    try:
        import streamlit as st
    except ImportError:
        return

    st.header("Campaign Content Factory")

    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input("Topic", "AI agents", key="cp_topic")
        brand_voice = st.selectbox("Voice", ["casual", "professional", "provocative", "educational"], key="cp_voice")
    with col2:
        platforms = st.multiselect(
            "Platforms",
            ["threads", "x", "instagram", "linkedin", "tiktok", "youtube", "xiaohongshu", "facebook"],
            default=["threads"],
            key="cp_plats",
        )

    tab1, tab2 = st.tabs(["Generate Post", "Content Calendar"])

    with tab1:
        if st.button("Generate Content", type="primary", key="cp_gen"):
            with st.spinner("Running 6-agent workflow..."):
                try:
                    from ...core.agents.workflow import run_content_workflow
                    state = run_fn(run_content_workflow(
                        platforms=platforms or ["threads"],
                        brand_voice=brand_voice,
                        topic=topic,
                    ))
                    for plat, content in state.get("final_content", {}).items():
                        st.subheader(plat.capitalize())
                        st.text_area("", content, height=120, key=f"cp_out_{plat}")
                except Exception as e:
                    st.error(f"Error: {e}")

    with tab2:
        days = st.slider("Days", 3, 30, 7, key="cp_days")
        topics_input = st.text_input("Topics (comma-sep)", topic, key="cp_topics")
        if st.button("Build Calendar", key="cp_cal"):
            topic_list = [t.strip() for t in topics_input.split(",") if t.strip()]
            plat_list = platforms or ["threads"]
            from ... import core  # noqa
            _ANGLES = [
                "Hot take: {t} is changing everything",
                "3 things nobody tells you about {t}",
                "Why {t} matters more than you think",
                "The future of {t}: what to expect",
                "How {t} will affect you in 2026",
                "What experts get wrong about {t}",
                "The dark side of {t} everyone ignores",
            ]
            calendar = []
            for day in range(1, days + 1):
                t = topic_list[(day - 1) % len(topic_list)] if topic_list else "trending"
                p = plat_list[(day - 1) % len(plat_list)]
                angle = _ANGLES[(day - 1) % len(_ANGLES)].format(t=t)
                calendar.append({"Day": day, "Topic": t, "Platform": p, "Angle": angle})

            try:
                import pandas as pd
                st.dataframe(pd.DataFrame(calendar), use_container_width=True)
            except ImportError:
                # pandas not installed — fall back to plain table
                st.table(calendar)
