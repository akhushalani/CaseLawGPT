"""
Configuration settings for CaseLawGPT.

This module centralizes all configuration parameters including paths,
model settings, and processing parameters.
"""
from __future__ import annotations

import os
from pathlib import Path


# =============================================================================
# Path Configuration
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw_cases"
DB_PATH = DATA_DIR / "caselaw.db"
VECTOR_DIR = DATA_DIR / "vectorstore"
VECTOR_INDEX_PATH = VECTOR_DIR / "faiss.index"
VECTOR_ID_MAP_PATH = VECTOR_DIR / "chunk_ids.npy"


# =============================================================================
# Model Configuration
# =============================================================================

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/all-MiniLM-L6-v2",
)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


# =============================================================================
# Chunking Configuration
# =============================================================================

CHUNK_TARGET_TOKENS = 500
CHUNK_MAX_TOKENS = 800
CHUNK_OVERLAP = 80
MIN_OPINION_LENGTH = 500  # characters


# =============================================================================
# Retrieval & Generation Configuration
# =============================================================================

DEFAULT_TOP_K = 5
MAX_CONTEXT_CHUNKS = 8
MAX_INPUT_TOKENS = 4096
MAX_GENERATION_TOKENS = 512


# =============================================================================
# Runtime Settings
# =============================================================================

VERBOSE = True


# =============================================================================
# Initialization
# =============================================================================

def ensure_directories() -> None:
    """Create required directories if they don't exist."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


ensure_directories()