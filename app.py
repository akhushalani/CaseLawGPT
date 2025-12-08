"""
Streamlit web interface for CaseLawGPT.

Provides a user-friendly interface for querying legal cases.
"""
from __future__ import annotations

from typing import List

import streamlit as st

from src.config import DEFAULT_TOP_K, DB_PATH, VECTOR_INDEX_PATH
from src.database import get_connection
from src.pipeline import run_query


def load_courts() -> List[str]:
    """Load unique court names from database."""
    try:
        conn = get_connection(DB_PATH)
        cur = conn.execute(
            """
            SELECT DISTINCT court 
            FROM cases 
            WHERE court IS NOT NULL AND court != '' 
            ORDER BY court;
            """
        )
        courts = [row[0] for row in cur.fetchall()]
        conn.close()
        return courts
    except Exception:
        return []


def render_citations(chunks) -> None:
    """Render citation cards for retrieved chunks."""
    st.subheader("Citations")
    
    for idx, chunk in enumerate(chunks, start=1):
        header = f"[{idx}] {chunk.case_name or chunk.citation or chunk.case_id}"
        meta = (
            f"{chunk.citation or 'Unknown cite'} - "
            f"{chunk.court or 'Unknown court'} "
            f"({chunk.decision_date or 'n.d.'})"
        )
        
        with st.expander(f"{header} | {meta}", expanded=False):
            st.markdown(
                f"**Opinion type:** {chunk.opinion_type or 'unknown'} | "
                f"**Chunk:** {chunk.position}"
            )
            st.markdown(f"**Relevance score:** {chunk.score:.3f}")
            st.markdown("---")
            
            # Truncate long text
            display_text = (
                chunk.text[:1500] + "..." 
                if len(chunk.text) > 1500 
                else chunk.text
            )
            st.markdown(f"> {display_text}")


def check_system_ready() -> tuple[bool, List[str]]:
    """Verify that all pipeline components are initialized."""
    issues = []
    
    if not DB_PATH.exists():
        issues.append("Database not found. Run the ingestion pipeline first.")
    else:
        try:
            conn = get_connection(DB_PATH)
            chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            conn.close()
            
            if chunks == 0:
                issues.append("No chunks in database. Run preprocessing.")
        except Exception as e:
            issues.append(f"Database error: {e}")
    
    if not VECTOR_INDEX_PATH.exists():
        issues.append("Vector index not found. Run vectorstore build.")
    
    return len(issues) == 0, issues


def get_stats() -> dict:
    """Get database statistics for display."""
    try:
        conn = get_connection(DB_PATH)
        stats = {
            "cases": conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
            "opinions": conn.execute("SELECT COUNT(*) FROM opinions").fetchone()[0],
            "chunks": conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0],
        }
        conn.close()
        return stats
    except Exception:
        return {"cases": 0, "opinions": 0, "chunks": 0}


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="CaseLawGPT",
        layout="wide",
        page_icon="⚖️",
    )
    
    st.title("⚖️ CaseLawGPT")
    st.markdown(
        "Ask legal questions grounded in U.S. caselaw. "
        "Answers cite retrieved judicial opinions."
    )
    
    # System readiness check
    ready, issues = check_system_ready()
    if not ready:
        st.error("System not ready!")
        for issue in issues:
            st.warning(issue)
        st.stop()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Settings")
        
        stats = get_stats()
        col1, col2 = st.columns(2)
        col1.metric("Cases", stats["cases"])
        col2.metric("Chunks", stats["chunks"])
        
        st.divider()
        
        top_k = st.slider("Results to retrieve", 1, 20, DEFAULT_TOP_K)
        
        courts = load_courts()
        selected_courts = st.multiselect("Filter by court", options=courts)
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.text_input("From date", placeholder="1960-01-01")
        with col2:
            end_date = st.text_input("To date", placeholder="2024-12-31")
        
        st.divider()
        st.caption("Powered by FAISS + Ollama")
    
    # Main query interface
    question = st.text_area(
        "Your legal question",
        height=100,
        placeholder="e.g., How have courts interpreted qualified immunity?",
    )
    
    col1, col2, _ = st.columns([1, 1, 4])
    
    with col1:
        search_btn = st.button("🔍 Search", type="primary", use_container_width=True)
    
    with col2:
        if st.button("🎲 Example", use_container_width=True):
            st.session_state["example"] = True
            st.rerun()
    
    # Handle example button
    if st.session_state.get("example"):
        question = "What are the requirements for a valid Fourth Amendment search?"
        st.session_state["example"] = False
    
    # Execute query
    if search_btn and question.strip():
        with st.spinner("Searching cases and generating answer..."):
            try:
                result = run_query(
                    question,
                    top_k=top_k,
                    courts=selected_courts or None,
                    start_date=start_date.strip() or None,
                    end_date=end_date.strip() or None,
                )
                
                st.subheader("Answer")
                st.markdown(result["answer"])
                
                if result["chunks"]:
                    render_citations(result["chunks"])
                else:
                    st.warning("No relevant cases found for your query.")
                    
            except Exception as e:
                st.error(f"Error: {e}")
                with st.expander("Details"):
                    st.exception(e)


if __name__ == "__main__":
    main()