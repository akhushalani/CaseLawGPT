"""Local LLM wrapper using Hugging Face Transformers."""
from __future__ import annotations

import os
from typing import List

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig

from config import LOCAL_LLM_MODEL_PATH, MAX_INPUT_TOKENS, MAX_GENERATION_TOKENS

_model = None
_tokenizer = None


def load_model():
    global _model, _tokenizer
    if _model is None or _tokenizer is None:
        model_path = LOCAL_LLM_MODEL_PATH
        _tokenizer = AutoTokenizer.from_pretrained(model_path)
        _model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )
    return _model, _tokenizer


def build_prompt(question: str, context_chunks: List[str]) -> str:
    numbered_context = "\n\n".join(f"[{i+1}] {chunk}" for i, chunk in enumerate(context_chunks))
    prompt = f"""You are CaseLawGPT, an assistant that answers legal questions strictly using provided judicial opinions.
Use only the context below. Do not speculate or add outside knowledge. If the answer is not supported, say you cannot answer confidently.
Include brief in-text citations referencing the case names/citations shown in the context.

Context:
{numbered_context}

Question: {question}

Answer with clear reasoning and citations."""
    return prompt


def generate_answer(question: str, context_chunks: List[str]) -> str:
    model, tokenizer = load_model()
    prompt = build_prompt(question, context_chunks)
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_INPUT_TOKENS,
    )
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    gen_config = GenerationConfig(
        max_new_tokens=MAX_GENERATION_TOKENS,
        temperature=0.2,
        top_p=0.9,
        do_sample=False,
        eos_token_id=tokenizer.eos_token_id,
    )

    with torch.no_grad():
        output_ids = model.generate(**inputs, generation_config=gen_config)
    decoded = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    # Remove prompt from decoded output if the model returns it.
    answer = decoded[len(prompt) :].strip() if decoded.startswith(prompt) else decoded.strip()
    return answer
