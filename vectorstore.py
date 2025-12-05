"""Vector index utilities using sentence-transformers + FAISS."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Sequence, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config import (
    DB_PATH,
    VECTOR_INDEX_PATH,
    VECTOR_ID_MAP_PATH,
    EMBEDDING_MODEL_NAME,
    DEFAULT_TOP_K,
    VERBOSE,
)
from database import get_connection

_embedder: SentenceTransformer | None = None
_index: faiss.Index | None = None
_chunk_id_map: np.ndarray | None = None


def load_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedder


def _batch_iterable(items: Sequence, batch_size: int):
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def build_index(db_path: Path = DB_PATH) -> None:
    """Compute embeddings for all chunks and persist FAISS index."""
    conn = get_connection(db_path)
    cur = conn.execute("SELECT chunk_id, text FROM chunks;")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        raise RuntimeError("No chunks found; run preprocessing first.")

    chunk_ids, texts = zip(*rows)
    embedder = load_embedder()
    embeddings: List[np.ndarray] = []

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
    index = faiss.IndexFlatIP(dim)
    index.add(matrix.astype(np.float32))

    VECTOR_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(VECTOR_INDEX_PATH))
    np.save(VECTOR_ID_MAP_PATH, np.array(chunk_ids))
    print(f"Saved index with {len(chunk_ids)} vectors to {VECTOR_INDEX_PATH}")


def _load_index() -> Tuple[faiss.Index, np.ndarray]:
    global _index, _chunk_id_map
    if _index is None:
        if not VECTOR_INDEX_PATH.exists():
            raise FileNotFoundError("Vector index not built. Run vectorstore.py --build")
        _index = faiss.read_index(str(VECTOR_INDEX_PATH))
    if _chunk_id_map is None:
        _chunk_id_map = np.load(VECTOR_ID_MAP_PATH)
    return _index, _chunk_id_map


def search(query: str, top_k: int = DEFAULT_TOP_K) -> List[dict]:
    """Return top-k chunks with metadata."""
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

    conn = get_connection(DB_PATH)
    placeholder = ",".join("?" for _ in found_ids)
    cur = conn.execute(
        f"""
        SELECT chunks.chunk_id, chunks.case_id, chunks.opinion_type, chunks.position, chunks.text,
               cases.citation, cases.name, cases.court, cases.decision_date
        FROM chunks
        JOIN cases ON chunks.case_id = cases.case_id
        WHERE chunks.chunk_id IN ({placeholder});
        """,
        tuple(found_ids),
    )
    meta = {row[0]: row[1:] for row in cur.fetchall()}
    conn.close()

    results = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx >= len(id_map):
            continue
        cid = id_map[idx]
        if cid not in meta:
            continue
        case_id, opinion_type, position, text, citation, name, court, decision_date = meta[cid]
        results.append(
            {
                "chunk_id": cid,
                "case_id": case_id,
                "opinion_type": opinion_type,
                "position": position,
                "text": text,
                "citation": citation,
                "case_name": name,
                "court": court,
                "decision_date": decision_date,
                "score": float(score),
            }
        )
    return results


def main():
    parser = argparse.ArgumentParser(description="Build or query FAISS index.")
    parser.add_argument("--build", action="store_true", help="Build index from chunks table.")
    parser.add_argument("--query", type=str, help="Optional query to test retrieval.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Top K results.")
    args = parser.parse_args()

    if args.build:
        build_index()

    if args.query:
        hits = search(args.query, args.top_k)
        print(json.dumps(hits, indent=2))


if __name__ == "__main__":
    main()
