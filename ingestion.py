"""Ingest CAP JSON case files into SQLite for CaseLawGPT.

Usage:
    python ingestion.py --raw-dir data/raw_cases

This script:
- Reads each JSON file in data/raw_cases (recursively).
- Extracts metadata and opinion texts.
- Cleans opinion text (strip HTML/whitespace artifacts).
- Stores cases and opinions in SQLite.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable, List, Tuple

from config import RAW_DATA_DIR, DB_PATH, MIN_OPINION_LENGTH, VERBOSE
from database import get_connection, init_db, insert_case, insert_opinions, case_exists


HTML_TAG_RE = re.compile(r"<[^>]+>")
MULTI_SPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    without_html = HTML_TAG_RE.sub(" ", text)
    normalized = MULTI_SPACE_RE.sub(" ", without_html).strip()
    return normalized


def extract_opinions(case_json: dict) -> List[Tuple[str, str]]:
    opinions = case_json.get("casebody", {}).get("opinions", []) or []
    cleaned: List[Tuple[str, str]] = []
    for op in opinions:
        text = op.get("text") or ""
        opinion_type = op.get("type") or "unknown"
        text = clean_text(text)
        if len(text) < MIN_OPINION_LENGTH:
            continue
        cleaned.append((opinion_type, text))
    return cleaned


def get_citation(case_json: dict) -> str:
    # CAP sometimes provides a list of citations; fall back to a single field.
    cites = case_json.get("citations") or []
    if isinstance(cites, list) and cites:
        cite = cites[0].get("cite") or cites[0].get("cite") or ""
        return cite
    return case_json.get("citation") or ""


def ingest_cases(raw_dir: Path = RAW_DATA_DIR, db_path: Path = DB_PATH) -> None:
    conn = get_connection(db_path)
    init_db(conn)

    files = list(raw_dir.rglob("*.json"))
    if VERBOSE:
        print(f"Found {len(files)} case files in {raw_dir}")

    inserted_cases = 0
    inserted_opinions = 0

    for path in files:
        with path.open("r") as f:
            case_json = json.load(f)

        case_id = str(case_json.get("id") or path.stem)
        if case_exists(conn, case_id):
            continue

        name = case_json.get("name") or case_json.get("name_abbreviation") or ""
        citation = get_citation(case_json)
        court = (case_json.get("court") or {}).get("name") or case_json.get("court") or ""
        jurisdiction = (
            (case_json.get("jurisdiction") or {}).get("name") or case_json.get("jurisdiction") or ""
        )
        decision_date = case_json.get("decision_date") or ""

        opinions = extract_opinions(case_json)
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


def main():
    parser = argparse.ArgumentParser(description="Ingest CAP cases into SQLite.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DATA_DIR, help="Directory with raw case JSON files.")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="SQLite database path.")
    args = parser.parse_args()
    ingest_cases(args.raw_dir, args.db_path)


if __name__ == "__main__":
    main()
