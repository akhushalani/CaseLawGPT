"""End-to-end RAG pipeline for CaseLawGPT."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from config import DEFAULT_TOP_K, MAX_CONTEXT_CHUNKS
from llm_local import generate_answer
from vectorstore import search


@dataclass
class RetrievedChunk:
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
    def within_date(decision_date: str) -> bool:
        if not decision_date:
            return True
        if start_date and decision_date < start_date:
            return False
        if end_date and decision_date > end_date:
            return False
        return True

    filtered = []
    for r in results:
        if courts and r.get("court") not in courts:
            continue
        if not within_date(r.get("decision_date") or ""):
            continue
        filtered.append(r)
    return filtered


def run_query(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    courts: Optional[Sequence[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    retrieved = search(question, top_k=max(top_k, MAX_CONTEXT_CHUNKS * 2))
    retrieved = filter_results(retrieved, courts=courts, start_date=start_date, end_date=end_date)

    # Trim to context budget
    context_chunks = [r["text"] for r in retrieved[:MAX_CONTEXT_CHUNKS]]
    answer = generate_answer(question, context_chunks)

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
        for r in retrieved[:top_k]
    ]

    return {
        "answer": answer,
        "chunks": structured,
    }
