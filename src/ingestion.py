"""
Case ingestion module for CaseLawGPT.

Reads JSON case files and stores them in SQLite database.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Tuple

from src.config import RAW_DATA_DIR, DB_PATH, MIN_OPINION_LENGTH, VERBOSE
from src.database import get_connection, init_db, insert_case, insert_opinions, case_exists


# Regex patterns for text cleaning
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
MULTI_SPACE_PATTERN = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """
    Remove HTML tags and normalize whitespace.
    
    Args:
        text: Raw text potentially containing HTML.
        
    Returns:
        Cleaned text string.
    """
    without_html = HTML_TAG_PATTERN.sub(" ", text)
    normalized = MULTI_SPACE_PATTERN.sub(" ", without_html).strip()
    return normalized


def extract_opinions(case_data: dict) -> List[Tuple[str, str]]:
    """
    Extract and clean opinions from case JSON.
    
    Args:
        case_data: Parsed case JSON dictionary.
        
    Returns:
        List of (opinion_type, cleaned_text) tuples.
    """
    opinions = case_data.get("casebody", {}).get("opinions", []) or []
    cleaned: List[Tuple[str, str]] = []
    
    for opinion in opinions:
        text = opinion.get("text") or ""
        opinion_type = opinion.get("type") or "unknown"
        text = clean_text(text)
        
        if len(text) >= MIN_OPINION_LENGTH:
            cleaned.append((opinion_type, text))
    
    return cleaned


def get_citation(case_data: dict) -> str:
    """Extract primary citation from case data."""
    citations = case_data.get("citations") or []
    
    if isinstance(citations, list) and citations:
        return citations[0].get("cite", "")
    
    return case_data.get("citation", "")


def ingest_cases(
    raw_dir: Path = RAW_DATA_DIR,
    db_path: Path = DB_PATH,
) -> Tuple[int, int]:
    """
    Ingest all case files from directory into database.
    
    Args:
        raw_dir: Directory containing JSON case files.
        db_path: Path to SQLite database.
        
    Returns:
        Tuple of (cases_inserted, opinions_inserted).
    """
    conn = get_connection(db_path)
    init_db(conn)

    files = list(raw_dir.rglob("*.json"))
    
    if VERBOSE:
        print(f"Found {len(files)} case files in {raw_dir}")

    inserted_cases = 0
    inserted_opinions = 0

    for path in files:
        with path.open("r") as f:
            case_data = json.load(f)

        case_id = str(case_data.get("id") or path.stem)
        
        if case_exists(conn, case_id):
            continue

        name = case_data.get("name") or case_data.get("name_abbreviation") or ""
        citation = get_citation(case_data)
        
        court = (
            (case_data.get("court") or {}).get("name") 
            or case_data.get("court") 
            or ""
        )
        
        jurisdiction = (
            (case_data.get("jurisdiction") or {}).get("name")
            or case_data.get("jurisdiction")
            or ""
        )
        
        decision_date = case_data.get("decision_date") or ""
        opinions = extract_opinions(case_data)
        
        if not opinions:
            continue

        insert_case(conn, case_id, name, citation, court, jurisdiction, decision_date)
        insert_opinions(conn, case_id, opinions)
        conn.commit()

        inserted_cases += 1
        inserted_opinions += len(opinions)

        if VERBOSE and inserted_cases % 500 == 0:
            print(f"Ingested {inserted_cases} cases / {inserted_opinions} opinions...")

    conn.close()
    print(f"Finished ingestion: {inserted_cases} cases, {inserted_opinions} opinions.")
    
    return inserted_cases, inserted_opinions


if __name__ == "__main__":
    ingest_cases()