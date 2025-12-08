"""
Database utilities for CaseLawGPT.

Provides SQLite schema management and CRUD operations for cases,
opinions, and text chunks.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Tuple, Optional

from src.config import DB_PATH


def get_connection(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """
    Create a database connection with foreign key support.
    
    Args:
        db_path: Path to SQLite database. Defaults to config.DB_PATH.
        
    Returns:
        SQLite connection object.
    """
    db_path = db_path or DB_PATH
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """
    Initialize database schema.
    
    Creates tables for cases, opinions, and chunks if they don't exist.
    
    Args:
        conn: Active database connection.
    """
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
    """Check if a case already exists in the database."""
    cur = conn.execute(
        "SELECT 1 FROM cases WHERE case_id = ? LIMIT 1;", 
        (case_id,)
    )
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
    """Insert or update a case record."""
    conn.execute(
        """
        INSERT OR REPLACE INTO cases 
            (case_id, name, citation, court, jurisdiction, decision_date)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (case_id, name, citation, court, jurisdiction, decision_date),
    )


def insert_opinions(
    conn: sqlite3.Connection,
    case_id: str,
    opinions: Iterable[Tuple[str, str]],
) -> None:
    """
    Insert opinion records for a case.
    
    Args:
        conn: Database connection.
        case_id: Parent case identifier.
        opinions: Iterable of (opinion_type, text) tuples.
    """
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
    """
    Insert chunk records.
    
    Args:
        conn: Database connection.
        rows: Iterable of (chunk_id, case_id, opinion_type, position, text, token_count).
    """
    conn.executemany(
        """
        INSERT OR REPLACE INTO chunks
            (chunk_id, case_id, opinion_type, position, text, token_count)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        rows,
    )
    conn.commit()