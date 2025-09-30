"""
Upload-time & batch shared utilities:
- get_client(): AzureOpenAI client from .env
- read_text(uploaded_file): read .txt/.md content (for UI uploads)
- chunk_text(text): token-aware splitting (JSON-aware via preprocess.text_ingest)
- chunk_text_with_meta(text): same as chunk_text but also returns metadata rows
- embed_texts(client, model, texts): batch embeddings (L2-normalized)
"""
# at the top with other imports
from dotenv import load_dotenv
load_dotenv()  # loads .env from the current working directory

import os
from pathlib import Path
from typing import List, Dict, Tuple, Any

import numpy as np
import tiktoken
from openai import AzureOpenAI

# ------------------------------------------------------------------
# Wire up the JSON-aware dispatcher (requires preprocess/ & chunkers/)
# ------------------------------------------------------------------
# Inside preprocess/text_ingest.py, you import chunkers.json_chunker.
# Here, we set the tokenizer once and delegate calls to that module.

from .preprocess.text_ingest import (
    set_tokenizer as _set_tokenizer,
    chunk_text as _chunk_text_impl,
    chunk_text_with_meta as _chunk_text_with_meta_impl,
)

_tok = tiktoken.get_encoding("cl100k_base")
_set_tokenizer(_tok)

# ---- new: robust file reader for .txt/.md/.json
def read_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in [".txt", ".md", ".json"]:
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""

# ---- keep old signatures but add optional source (backward compatible)
def chunk_text(
    text: str,
    max_tokens: int = 800,
    overlap: int = 100,
    source: str | None = None,
) -> List[str]:
    """Delegates to preprocess.text_ingest; JSON → schema-aware, else sliding window."""
    return _chunk_text_impl(text, max_tokens, overlap, source=source)

def chunk_text_with_meta(
    text: str,
    max_tokens: int = 800,
    overlap: int = 100,
    source: str | None = None,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Like chunk_text, but also returns metadata dicts for meta.jsonl."""
    return _chunk_text_with_meta_impl(text, max_tokens, overlap, source=source)

# ------------------------------------------------------------------
# Azure OpenAI + file utilities
# ------------------------------------------------------------------
def get_client() -> AzureOpenAI:
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    if not all([api_key, endpoint, api_version]):
        raise RuntimeError("Missing Azure OpenAI env vars")
    return AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)

def read_text(uploaded_file) -> str:
    """
    Minimal extractor for .txt/.md uploads (e.g., Streamlit's UploadedFile).
    """
    name = getattr(uploaded_file, "name", "")
    suffix = Path(name).suffix.lower()
    if suffix not in [".txt", ".md"]:
        return ""
    b = uploaded_file.read()
    if isinstance(b, str):
        return b
    try:
        return b.decode("utf-8")
    except Exception:
        return b.decode("utf-8", errors="ignore")

# ------------------------------------------------------------------
# Embeddings
# ------------------------------------------------------------------
def _l2_normalize(a: np.ndarray) -> np.ndarray:
    return a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-12)

def embed_texts(client: AzureOpenAI, model: str, texts: List[str]) -> np.ndarray:
    """
    Returns L2-normalized embeddings, shape [n, d] float32.
    """
    if not texts:
        return np.empty((0, 0), dtype="float32")
    resp = client.embeddings.create(model=model, input=texts)
    vecs = [d.embedding for d in resp.data]
    arr = np.asarray(vecs, dtype="float32")
    return _l2_normalize(arr)
