"""
RAG pipeline for CaseLawGPT.

Orchestrates retrieval and generation to answer legal questions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from src.config import DEFAULT_TOP_K, MAX_CONTEXT_CHUNKS
from src.llm import generate_answer
from src.vectorstore import search


@dataclass
class RetrievedChunk:
    """Represents a retrieved case chunk with metadata."""
    
    chunk_id: str
    case_id: str
    citation: str
    case_name: str
    court: str
    decision_date: str
    opinion_type: str
    position: int
    text: str
    score: float


def filter_results(
    results: List[dict],
    courts: Optional[Sequence[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[dict]:
    """
    Filter search results by court and date range.
    
    Args:
        results: Raw search results.
        courts: List of court names to include (None = all).
        start_date: Minimum decision date (YYYY-MM-DD).
        end_date: Maximum decision date (YYYY-MM-DD).
        
    Returns:
        Filtered results list.
    """
    def within_date_range(decision_date: str) -> bool:
        if not decision_date:
            return True
        if start_date and decision_date < start_date:
            return False
        if end_date and decision_date > end_date:
            return False
        return True

    filtered = []
    
    for result in results:
        # Court filter
        if courts and result.get("court") not in courts:
            continue
        
        # Date filter
        if not within_date_range(result.get("decision_date") or ""):
            continue
        
        filtered.append(result)
    
    return filtered


def run_query(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    courts: Optional[Sequence[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """
    Execute a RAG query: retrieve relevant chunks and generate answer.
    
    Args:
        question: User's legal question.
        top_k: Number of chunks to retrieve and display.
        courts: Optional list of courts to filter by.
        start_date: Optional minimum date filter.
        end_date: Optional maximum date filter.
        
    Returns:
        Dictionary with 'answer' and 'chunks' keys.
    """
    # Retrieve more than needed to allow for filtering
    retrieved = search(question, top_k=max(top_k, MAX_CONTEXT_CHUNKS * 2))
    retrieved = filter_results(
        retrieved, 
        courts=courts, 
        start_date=start_date, 
        end_date=end_date
    )

    # Use consistent chunk count for LLM and display
    display_chunks = retrieved[:MAX_CONTEXT_CHUNKS]
    context_chunks = [r["text"] for r in display_chunks]
    
    # Generate answer
    answer = generate_answer(question, context_chunks)

    # Structure results for display
    structured = [
        RetrievedChunk(
            chunk_id=r["chunk_id"],
            case_id=r["case_id"],
            citation=r["citation"],
            case_name=r["case_name"],
            court=r["court"],
            decision_date=r["decision_date"],
            opinion_type=r["opinion_type"],
            position=r["position"],
            text=r["text"],
            score=r["score"],
        )
        for r in display_chunks
    ]

    return {
        "answer": answer,
        "chunks": structured,
    }