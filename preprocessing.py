"""Preprocess and chunk opinions for CaseLawGPT.

Usage:
    python preprocessing.py

Steps:
- Load opinions from SQLite.
- Split into paragraph-aware chunks ~500 tokens with small overlap.
- Persist chunk metadata into `chunks` table.
"""
from __future__ import annotations

import argparse
import re
import uuid
from typing import List, Tuple

from config import (
    CHUNK_TARGET_TOKENS,
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP,
    DB_PATH,
    VERBOSE,
)
from database import get_connection, insert_chunks


SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def tokenize(text: str) -> List[str]:
    return text.split()


def chunk_text(text: str) -> List[str]:
    """Chunk text into overlapping windows respecting sentences."""
    sentences = SENTENCE_RE.split(text)
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for sentence in sentences:
        tokens = tokenize(sentence)
        if current_len + len(tokens) > CHUNK_MAX_TOKENS and current:
            chunks.append(" ".join(current).strip())
            # overlap
            overlap_tokens = " ".join(current).split()[-CHUNK_OVERLAP:]
            current = overlap_tokens + tokens
            current_len = len(current)
        else:
            current.extend(tokens)
            current_len += len(tokens)

        if current_len >= CHUNK_TARGET_TOKENS:
            chunks.append(" ".join(current).strip())
            overlap_tokens = current[-CHUNK_OVERLAP:]
            current = overlap_tokens.copy()
            current_len = len(current)

    if current:
        chunks.append(" ".join(current).strip())
    return [c for c in chunks if c]


def process_opinions(db_path=DB_PATH) -> int:
    conn = get_connection(db_path)
    cur = conn.execute(
        """
        SELECT opinions.opinion_id, opinions.case_id, opinions.opinion_type, opinions.text
        FROM opinions
        JOIN cases ON opinions.case_id = cases.case_id;
        """
    )

    total_chunks = 0
    rows_to_insert: List[Tuple[str, str, str, int, str, int]] = []

    for opinion_id, case_id, opinion_type, text in cur.fetchall():
        chunks = chunk_text(text)
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{case_id}-{opinion_id}-{uuid.uuid4().hex[:8]}"
            token_count = len(tokenize(chunk))
            rows_to_insert.append((chunk_id, case_id, opinion_type, idx, chunk, token_count))
        total_chunks += len(chunks)

        if len(rows_to_insert) > 1000:
            insert_chunks(conn, rows_to_insert)
            rows_to_insert.clear()
            if VERBOSE:
                print(f"Inserted {total_chunks} chunks so far...")

    if rows_to_insert:
        insert_chunks(conn, rows_to_insert)

    conn.close()
    print(f"Finished chunking: {total_chunks} chunks created.")
    if total_chunks < 10_000:
        print("Warning: fewer than 10,000 chunks generated. Ingest more cases to satisfy requirement.")
    return total_chunks


def main():
    parser = argparse.ArgumentParser(description="Chunk opinions into retrieval units.")
    parser.add_argument("--db-path", default=DB_PATH, help="SQLite database path.")
    args = parser.parse_args()
    process_opinions(args.db_path)


if __name__ == "__main__":
    main()
