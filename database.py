"""Lightweight SQLite schema helpers for CaseLawGPT."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Tuple

from config import DB_PATH


def get_connection(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            name TEXT,
            citation TEXT,
            court TEXT,
            jurisdiction TEXT,
            decision_date TEXT
        );

        CREATE TABLE IF NOT EXISTS opinions (
            opinion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            opinion_type TEXT,
            text TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            opinion_type TEXT,
            position INTEGER,
            text TEXT NOT NULL,
            token_count INTEGER,
            FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def case_exists(conn: sqlite3.Connection, case_id: str) -> bool:
    cur = conn.execute("SELECT 1 FROM cases WHERE case_id = ? LIMIT 1;", (case_id,))
    return cur.fetchone() is not None


def insert_case(
    conn: sqlite3.Connection,
    case_id: str,
    name: str,
    citation: str,
    court: str,
    jurisdiction: str,
    decision_date: str,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO cases (case_id, name, citation, court, jurisdiction, decision_date)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (case_id, name, citation, court, jurisdiction, decision_date),
    )


def insert_opinions(
    conn: sqlite3.Connection,
    case_id: str,
    opinions: Iterable[Tuple[str, str]],
) -> None:
    conn.executemany(
        """
        INSERT INTO opinions (case_id, opinion_type, text)
        VALUES (?, ?, ?);
        """,
        ((case_id, otype, text) for otype, text in opinions),
    )


def insert_chunks(
    conn: sqlite3.Connection,
    rows: Iterable[Tuple[str, str, str, int, str, int]],
) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO chunks
        (chunk_id, case_id, opinion_type, position, text, token_count)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        rows,
    )
    conn.commit()
