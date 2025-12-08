"""
Text preprocessing and chunking for CaseLawGPT.

Splits legal opinions into overlapping chunks suitable for retrieval.
"""
from __future__ import annotations

import re
import uuid
from typing import List, Tuple

from src.config import (
    CHUNK_TARGET_TOKENS,
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP,
    DB_PATH,
    VERBOSE,
)
from src.database import get_connection, insert_chunks


# Pattern to split on sentence boundaries
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def tokenize(text: str) -> List[str]:
    """Simple whitespace tokenization."""
    return text.split()


def chunk_text(text: str) -> List[str]:
    """
    Split text into overlapping chunks respecting sentence boundaries.
    
    Args:
        text: Full opinion text.
        
    Returns:
        List of text chunks.
    """
    sentences = SENTENCE_PATTERN.split(text)
    chunks: List[str] = []
    current_tokens: List[str] = []
    current_length = 0

    for sentence in sentences:
        tokens = tokenize(sentence)
        
        # Check if adding this sentence exceeds max tokens
        if current_length + len(tokens) > CHUNK_MAX_TOKENS and current_tokens:
            chunks.append(" ".join(current_tokens).strip())
            
            # Keep overlap tokens for context continuity
            overlap_tokens = " ".join(current_tokens).split()[-CHUNK_OVERLAP:]
            current_tokens = overlap_tokens + tokens
            current_length = len(current_tokens)
        else:
            current_tokens.extend(tokens)
            current_length += len(tokens)

        # Create chunk if we've reached target size
        if current_length >= CHUNK_TARGET_TOKENS:
            chunks.append(" ".join(current_tokens).strip())
            overlap_tokens = current_tokens[-CHUNK_OVERLAP:]
            current_tokens = overlap_tokens.copy()
            current_length = len(current_tokens)

    # Don't forget remaining tokens
    if current_tokens:
        chunks.append(" ".join(current_tokens).strip())
    
    return [chunk for chunk in chunks if chunk]


def process_opinions(db_path=DB_PATH) -> int:
    """
    Process all opinions and create chunks.
    
    Args:
        db_path: Path to SQLite database.
        
    Returns:
        Total number of chunks created.
    """
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
            rows_to_insert.append(
                (chunk_id, case_id, opinion_type, idx, chunk, token_count)
            )
        
        total_chunks += len(chunks)

        # Batch insert for performance
        if len(rows_to_insert) > 1000:
            insert_chunks(conn, rows_to_insert)
            rows_to_insert.clear()
            
            if VERBOSE:
                print(f"Inserted {total_chunks} chunks so far...")

    # Insert remaining rows
    if rows_to_insert:
        insert_chunks(conn, rows_to_insert)

    conn.close()
    print(f"Finished chunking: {total_chunks} chunks created.")
    
    return total_chunks


if __name__ == "__main__":
    process_opinions()