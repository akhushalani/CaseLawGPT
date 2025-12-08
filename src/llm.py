"""
LLM integration for CaseLawGPT.

Provides answer generation using Ollama API.
"""
from __future__ import annotations

import sys
# Prevent TensorFlow import issues on Apple Silicon
sys.modules["tensorflow"] = None  # noqa: E402

from typing import List

import requests

from src.config import OLLAMA_MODEL, OLLAMA_URL, MAX_GENERATION_TOKENS


def build_prompt(question: str, context_chunks: List[str]) -> str:
    """
    Construct the prompt for the LLM.
    
    Args:
        question: User's legal question.
        context_chunks: Retrieved case text chunks.
        
    Returns:
        Formatted prompt string.
    """
    numbered_context = "\n\n".join(
        f"[{i + 1}] {chunk}" 
        for i, chunk in enumerate(context_chunks)
    )
    
    return f"""You are CaseLawGPT, a legal research assistant. Answer questions using ONLY the provided case excerpts.

RULES:
- Base your answer strictly on the provided context
- Cite cases by number (e.g., [1], [2]) when making claims
- If the context doesn't contain enough information, say so
- Be precise and legally accurate

CONTEXT FROM RETRIEVED CASES:
{numbered_context}

QUESTION: {question}

ANSWER:"""


def generate_answer(question: str, context_chunks: List[str]) -> str:
    """
    Generate an answer using the Ollama LLM.
    
    Args:
        question: User's legal question.
        context_chunks: Retrieved case text chunks for context.
        
    Returns:
        Generated answer string.
    """
    prompt = build_prompt(question, context_chunks)
    
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": MAX_GENERATION_TOKENS,
                },
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    
    except requests.exceptions.ConnectionError:
        return (
            "**Error: Cannot connect to Ollama.**\n\n"
            "Please ensure Ollama is running: `ollama serve`"
        )
    except requests.exceptions.Timeout:
        return "**Error: Request timed out.** Please try again."
    except Exception as e:
        return f"**Error:** {e}"