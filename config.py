"""
Configuration for CaseLawGPT.

Run pipeline:
- Step 1: Ingest raw CAP JSON files with `python ingestion.py`.
- Step 2: Preprocess and chunk with `python preprocessing.py`.
- Step 3: Build embeddings/vector index with `python vectorstore.py`.
- Step 4: Launch UI with `streamlit run app.py`.
"""
from __future__ import annotations

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw_cases"
DB_PATH = DATA_DIR / "caselaw.db"
VECTOR_DIR = DATA_DIR / "vectorstore"
VECTOR_INDEX_PATH = VECTOR_DIR / "faiss.index"
VECTOR_ID_MAP_PATH = VECTOR_DIR / "chunk_ids.npy"

# Models (assume already downloaded locally)
EMBEDDING_MODEL_NAME = os.getenv(
    "CASELAW_EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
LOCAL_LLM_MODEL_PATH = os.getenv(
    "LOCAL_LLM_MODEL_PATH",
    str(BASE_DIR / "models" / "llama-3-8b-instruct"),
)

# Chunking
CHUNK_TARGET_TOKENS = 500
CHUNK_MAX_TOKENS = 800
CHUNK_OVERLAP = 80
MIN_OPINION_LENGTH = 500  # characters

# Retrieval / generation
DEFAULT_TOP_K = 5
MAX_CONTEXT_CHUNKS = 8
MAX_INPUT_TOKENS = 4096
MAX_GENERATION_TOKENS = 512

# Logging
VERBOSE = True


def ensure_directories() -> None:
    """Ensure required directories exist."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


ensure_directories()
