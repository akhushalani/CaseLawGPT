"""Streamlit front end for CaseLawGPT."""
from __future__ import annotations

from typing import List

import streamlit as st

from config import DEFAULT_TOP_K, DB_PATH
from database import get_connection
from rag_pipeline import run_query


def load_courts() -> List[str]:
    conn = get_connection(DB_PATH)
    cur = conn.execute("SELECT DISTINCT court FROM cases WHERE court IS NOT NULL AND court != '' ORDER BY court;")
    courts = [row[0] for row in cur.fetchall()]
    conn.close()
    return courts


def render_citations(chunks):
    st.subheader("Citations")
    for idx, ch in enumerate(chunks, start=1):
        header = f"[{idx}] {ch.case_name or ch.citation or ch.case_id}"
        meta = f"{ch.citation or 'Unknown cite'} — {ch.court or 'Unknown court'} ({ch.decision_date or 'n.d.'})"
        with st.expander(f"{header} — {meta}", expanded=False):
            st.markdown(f"**Opinion:** {ch.opinion_type or 'unknown'} · Position {ch.position}")
            st.markdown(f"> {ch.text}")


def main():
    st.set_page_config(page_title="CaseLawGPT", layout="wide")
    st.title("CaseLawGPT")
    st.markdown("Ask legal questions over U.S. caselaw. Answers are grounded in retrieved opinions.")

    courts = load_courts()
    with st.sidebar:
        st.header("Retrieval Settings")
        top_k = st.slider("Top K results", min_value=1, max_value=20, value=DEFAULT_TOP_K)
        selected_courts = st.multiselect("Filter courts", options=courts)
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.text_input("Start date (YYYY-MM-DD)", value="", placeholder="1900-01-01")
        with col2:
            end_date = st.text_input("End date (YYYY-MM-DD)", value="", placeholder="2024-12-31")
        start_str = start_date.strip() or None
        end_str = end_date.strip() or None

    question = st.text_area("Legal question", height=120, placeholder="How have courts defined qualified immunity?")
    if st.button("Run CaseLawGPT") and question.strip():
        with st.spinner("Retrieving and generating answer..."):
            result = run_query(
                question,
                top_k=top_k,
                courts=selected_courts or None,
                start_date=start_str,
                end_date=end_str,
            )
        st.subheader("Answer")
        st.markdown(result["answer"])
        render_citations(result["chunks"])


if __name__ == "__main__":
    main()
