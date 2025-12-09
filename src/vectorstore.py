"""
Vector store for semantic search over case law chunks.

Uses sentence-transformers for embeddings and FAISS for similarity search.
"""
from __future__ import annotations

import sys
# Prevent TensorFlow import hanging on Apple Silicon
sys.modules["tensorflow"] = None  # noqa: E402

import os
from pathlib import Path
from typing import List, Tuple, Optional, Sequence

import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from src.config import (
    DB_PATH,
    VECTOR_INDEX_PATH,
    VECTOR_ID_MAP_PATH,
    EMBEDDING_MODEL_NAME,
    DEFAULT_TOP_K,
    VERBOSE,
)
from src.database import get_connection


# Module-level caches
_embedder: Optional[SentenceTransformer] = None
_index: Optional[faiss.Index] = None
_chunk_id_map: Optional[np.ndarray] = None


def _resolve_device() -> str:
    """Pick embedding device, favoring explicit env, then CUDA/MPS, else CPU."""
    device_env = os.getenv("EMBEDDING_DEVICE")
    if device_env:
        return device_env
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_embedder() -> SentenceTransformer:
    """Load and cache the embedding model."""
    global _embedder
    
    if _embedder is None:
        device = _resolve_device()
        try:
            _embedder = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)
        except NotImplementedError:
            # Some torch builds + meta tensors can fail; fall back to CPU.
            _embedder = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
        except Exception:
            # Last-resort fallback to CPU if anything unexpected happens.
            _embedder = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
    
    return _embedder


def _batch_iterable(items: Sequence, batch_size: int):
    """Yield batches from a sequence."""
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def build_index(db_path: Path = DB_PATH) -> None:
    """
    Build FAISS index from all chunks in database.
    
    Args:
        db_path: Path to SQLite database.
    """
    conn = get_connection(db_path)
    cur = conn.execute("SELECT chunk_id, text FROM chunks;")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        raise RuntimeError("No chunks found. Run preprocessing first.")

    chunk_ids, texts = zip(*rows)
    embedder = load_embedder()
    embeddings: List[np.ndarray] = []

    print(f"Encoding {len(texts)} chunks...")
    
    for batch in _batch_iterable(list(texts), 64):
        emb = embedder.encode(
            list(batch),
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        embeddings.append(emb)
        
        if VERBOSE and len(embeddings) % 50 == 0:
            print(f"Encoded {len(embeddings) * 64} chunks...")

    matrix = np.concatenate(embeddings, axis=0)
    dim = matrix.shape[1]
    
    # Inner product index (cosine similarity with normalized vectors)
    index = faiss.IndexFlatIP(dim)
    index.add(matrix.astype(np.float32))

    # Save index and ID mapping
    VECTOR_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(VECTOR_INDEX_PATH))
    np.save(VECTOR_ID_MAP_PATH, np.array(chunk_ids))
    
    print(f"Saved index with {len(chunk_ids)} vectors to {VECTOR_INDEX_PATH}")


def _load_index() -> Tuple[faiss.Index, np.ndarray]:
    """Load and cache the FAISS index and ID mapping."""
    global _index, _chunk_id_map
    
    if _index is None:
        if not VECTOR_INDEX_PATH.exists():
            raise FileNotFoundError(
                "Vector index not found. Run: python -m src.vectorstore --build"
            )
        _index = faiss.read_index(str(VECTOR_INDEX_PATH))
    
    if _chunk_id_map is None:
        _chunk_id_map = np.load(VECTOR_ID_MAP_PATH)
    
    return _index, _chunk_id_map


def search(query: str, top_k: int = DEFAULT_TOP_K) -> List[dict]:
    """
    Search for relevant chunks using semantic similarity.
    
    Args:
        query: Search query string.
        top_k: Number of results to return.
        
    Returns:
        List of result dictionaries with chunk data and scores.
    """
    index, id_map = _load_index()
    embedder = load_embedder()
    
    query_vec = embedder.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype(np.float32)

    scores, idxs = index.search(query_vec, top_k)
    found_ids = [id_map[i] for i in idxs[0] if i < len(id_map)]
    
    if not found_ids:
        return []

    # Fetch metadata from database
    conn = get_connection(DB_PATH)
    placeholder = ",".join("?" for _ in found_ids)
    
    cur = conn.execute(
        f"""
        SELECT 
            chunks.chunk_id, 
            chunks.case_id, 
            chunks.opinion_type, 
            chunks.position, 
            chunks.text,
            cases.citation, 
            cases.name, 
            cases.court, 
            cases.decision_date
        FROM chunks
        JOIN cases ON chunks.case_id = cases.case_id
        WHERE chunks.chunk_id IN ({placeholder});
        """,
        tuple(found_ids),
    )
    
    meta = {row[0]: row[1:] for row in cur.fetchall()}
    conn.close()

    # Build results with scores
    results = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx >= len(id_map):
            continue
            
        chunk_id = id_map[idx]
        if chunk_id not in meta:
            continue
            
        case_id, opinion_type, position, text, citation, name, court, decision_date = meta[chunk_id]
        
        results.append({
            "chunk_id": chunk_id,
            "case_id": case_id,
            "opinion_type": opinion_type,
            "position": position,
            "text": text,
            "citation": citation,
            "case_name": name,
            "court": court,
            "decision_date": decision_date,
            "score": float(score),
        })
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build or query vector index.")
    parser.add_argument("--build", action="store_true", help="Build index from chunks.")
    parser.add_argument("--query", type=str, help="Test query.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    args = parser.parse_args()

    if args.build:
        build_index()

    if args.query:
        import json
        hits = search(args.query, args.top_k)
        print(json.dumps(hits, indent=2))
