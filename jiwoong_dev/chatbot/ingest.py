"""
Upload-time & batch shared utilities:
- get_client(): AzureOpenAI client from .env
- read_text(uploaded_file): read .txt/.md content (for UI uploads)
- chunk_text(text): token-aware splitting
- embed_texts(client, model, texts): batch embeddings (L2-normalized)
"""

import os
from pathlib import Path
from typing import List

import numpy as np
import tiktoken
from openai import AzureOpenAI


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


_tok = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, max_tokens: int = 800, overlap: int = 100) -> List[str]:
    if not text.strip():
        return []
    ids = _tok.encode(text)
    chunks: List[str] = []
    start = 0
    while start < len(ids):
        end = min(start + max_tokens, len(ids))
        chunks.append(_tok.decode(ids[start:end]))
        if end == len(ids):
            break
        start = max(0, end - overlap)
    return chunks


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
