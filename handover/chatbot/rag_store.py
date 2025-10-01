"""
FAISS + metadata helpers shared by batch builder and UI:
- load_store(index_path, meta_path) -> (index, meta_rows)
- save_store(index, meta, index_path, meta_path)
- create_empty_index(dim)
- add_vectors(index, vecs)
- search(index, meta, qvec, k)
- normalize(a)
"""

import json
from pathlib import Path
from typing import List, Dict

import numpy as np
import faiss


def normalize(a: np.ndarray) -> np.ndarray:
    return a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-12)


def load_store(index_path: str, meta_path: str):
    index = faiss.read_index(index_path)
    meta: List[Dict] = [
        json.loads(line) for line in Path(meta_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return index, meta


def save_store(index, meta: List[Dict], index_path: str, meta_path: str):
    Path(index_path).parent.mkdir(parents=True, exist_ok=True)
    Path(meta_path).parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, index_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        for row in meta:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def save(index_path: str, meta_path: str, vectors: np.ndarray, chunks: List[str], metas: List[Dict]):
    """
    Compatibility wrapper used by build_index.py:
      - builds a FAISS IP index for cosine on already L2-normalized vectors
      - merges each meta dict with its chunk 'text'
      - writes index.faiss + meta.jsonl
    """
    if vectors is None or vectors.size == 0:
        raise ValueError("No vectors to save.")
    if len(chunks) != len(metas) or vectors.shape[0] != len(chunks):
        raise ValueError(
            f"Length mismatch: vecs={vectors.shape[0]}, chunks={len(chunks)}, metas={len(metas)}"
        )

    # Build index
    dim = int(vectors.shape[1])
    index = create_empty_index(dim)
    # Assume vectors are already L2-normalized upstream.
    add_vectors(index, vectors.astype("float32"))

    # Combine meta with text
    meta_rows = []
    for m, t in zip(metas, chunks):
        row = dict(m)
        row["text"] = t
        meta_rows.append(row)

    save_store(index, meta_rows, index_path, meta_path)


def create_empty_index(dim: int):
    """Cosine similarity via inner product on L2-normalized vectors."""
    return faiss.IndexFlatIP(dim)


def add_vectors(index, vecs: np.ndarray):
    """Assumes vecs are already L2-normalized."""
    if vecs is None or vecs.size == 0:
        return
    index.add(vecs.astype("float32"))


def search(index, meta: List[Dict], qvec: np.ndarray, k: int = 6) -> List[Dict]:
    """
    qvec: shape [d] or [1,d]; returns [{'score': float, 'meta': Dict}]
    """
    if qvec.ndim == 1:
        q = qvec.reshape(1, -1)
    else:
        q = qvec
    q = normalize(q.astype("float32"))
    scores, idxs = index.search(q, k)
    out = []
    for s, i in zip(scores[0], idxs[0]):
        if int(i) >= 0:
            out.append({"score": float(s), "meta": meta[int(i)]})
    return out
