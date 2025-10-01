#!/usr/bin/env python3
"""
build_index.py

Batch builder: read a folder of .txt/.md/.json → chunk → embed (Azure) → L2-normalize →
save FAISS + meta JSONL via rag_store.py.

This version is JSON-aware:
- If a file is .json and matches your normalized schema (emails/meetings/personal_notes),
  chunking will be schema-aware (headers per item + section-aware splitting).
- Other text files fall back to sliding-window chunking.

Usage:
    python build_index.py \
      --input_dir ./data/preprocessed \
      --out_index ./handover/chatbot/rag_store/index.faiss \
      --out_meta  ./handover/chatbot/rag_store/meta.jsonl \
      --max_tokens 800 \
      --overlap 100 \
      --embedding_model text-embedding-3-large \
      --embed_batch 128
"""


from __future__ import annotations

# at the top with other imports
from dotenv import load_dotenv
load_dotenv()  # loads .env from the current working directory

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np

# Local modules
# Project layout assumption:
# handover/chatbot/
#   ├─ build_index.py   ← (this file)
#   ├─ ingest.py
#   ├─ rag_store.py
#   └─ preprocess/, chunkers/, ...
#
# If you run from repo root, PYTHONPATH should include the package root so that
# "import ingest" / "import rag_store" resolves. If not, we adjust sys.path.
_CURR = Path(__file__).resolve()
_PKG_ROOT = _CURR.parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from . import ingest               # shared tokenizer/JSON-aware chunking + embeddings
from . import rag_store            # FAISS/meta save helpers


# ----------------------------
# Helpers
# ----------------------------
def list_source_files(root: Path) -> List[Path]:
    """
    Recursively list source files under `root` with supported extensions.
    Supports .txt, .md, .json
    """
    exts = {".txt", ".md", ".json"}
    return sorted([p for p in root.rglob("*") if p.suffix.lower() in exts and p.is_file()])


def read_file(p: Path) -> str:
    """
    Delegate to ingest.read_file if available; otherwise simple read.
    """
    try:
        return ingest.read_file(p)  # supports .txt/.md/.json
    except Exception:
        return p.read_text(encoding="utf-8", errors="ignore")


def chunk_one_file(
    path: Path,
    max_tokens: int,
    overlap: int,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Reads file text and returns (chunks, metas).
    The 'source' field in meta will be the absolute path of the file.
    """
    raw = read_file(path)
    if not raw or not str(raw).strip():
        return [], []

    chunks, metas = ingest.chunk_text_with_meta(
        raw,
        max_tokens=max_tokens,
        overlap=overlap,
        source=str(path.resolve()),
    )
    return chunks, metas


def batched(iterable: List[Any], n: int) -> List[List[Any]]:
    """
    Yield successive n-sized batches from `iterable`.
    """
    if n <= 0:
        n = 64
    for i in range(0, len(iterable), n):
        yield iterable[i : i + n]


def _ensure_2d(arr: np.ndarray) -> np.ndarray:
    """
    Ensure embeddings array is [N, D] float32.
    """
    if arr is None:
        return np.empty((0, 0), dtype="float32")
    a = np.asarray(arr)
    if a.ndim == 1:
        a = a.reshape(1, -1)
    if a.dtype != np.float32:
        a = a.astype("float32")
    return a


def _maybe_tuple_from_embed(ret) -> np.ndarray:
    """
    Some earlier snippets returned (array) or (array, ...). Normalize to array.
    """
    if isinstance(ret, tuple):
        return _ensure_2d(ret[0])
    return _ensure_2d(ret)


# ----------------------------
# Main building routine
# ----------------------------
def build_index(
    input_dir: Path,
    out_index: Path,
    out_meta: Path,
    max_tokens: int,
    overlap: int,
    embedding_model: str,
    embed_batch: int,
) -> None:
    files = list_source_files(input_dir)
    if not files:
        print(f"[build_index] No source files found under: {input_dir}")
        return

    print(f"[build_index] Found {len(files)} source files")
    print(f"[build_index] Token params: max_tokens={max_tokens}, overlap={overlap}")

    all_chunks: List[str] = []
    all_meta: List[Dict[str, Any]] = []

    # 1) Chunk all files
    for idx, p in enumerate(files, 1):
        try:
            chunks, metas = chunk_one_file(p, max_tokens=max_tokens, overlap=overlap)
        except Exception as e:
            print(f"[build_index] ERROR chunking {p}: {e}")
            continue

        all_chunks.extend(chunks)
        all_meta.extend(metas)
        print(f"[{idx}/{len(files)}] {p.name}: +{len(chunks)} chunks (total: {len(all_chunks)})")

    if not all_chunks:
        print("[build_index] No chunks produced. Nothing to embed/save.")
        return

    # 2) Embed (batched)
    print(f"[build_index] Embedding {len(all_chunks)} chunks (batch={embed_batch}) with model='{embedding_model}'")
    client = ingest.get_client()

    embed_vecs: List[np.ndarray] = []
    for bi, batch in enumerate(batched(all_chunks, embed_batch), 1):
        try:
            vec = ingest.embed_texts(client, embedding_model, batch)
            vec = _maybe_tuple_from_embed(vec)
        except Exception as e:
            print(f"[build_index] ERROR embedding batch {bi}: {e}")
            raise

        embed_vecs.append(vec)
        print(f"  - batch {bi}: {len(batch)} embedded")

    vectors = _ensure_2d(np.vstack(embed_vecs))
    if vectors.shape[0] != len(all_chunks):
        raise RuntimeError(
            f"[build_index] Embedding count mismatch: vectors={vectors.shape[0]} vs chunks={len(all_chunks)}"
        )

    print(f"[build_index] Final embeddings shape: {vectors.shape}")

    # 3) Persist via rag_store
    out_index.parent.mkdir(parents=True, exist_ok=True)
    out_meta.parent.mkdir(parents=True, exist_ok=True)

    print(f"[build_index] Saving index -> {out_index}")
    print(f"[build_index] Saving meta  -> {out_meta}")

    # Expect rag_store.save(index_path, meta_path, vectors, chunks, metas)
    rag_store.save(
        index_path=str(out_index),
        meta_path=str(out_meta),
        vectors=vectors,
        chunks=all_chunks,
        metas=all_meta,
    )

    # Optional: quick sanity stats
    try:
        type_counts = {}
        for m in all_meta:
            t = m.get("type", "plain")
            type_counts[t] = type_counts.get(t, 0) + 1
        print("[build_index] Chunk type counts:", json.dumps(type_counts, ensure_ascii=False))
    except Exception:
        pass

    print("[build_index] DONE ✅")


# ----------------------------
# CLI
# ----------------------------
def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FAISS/JSONL from txt/md/json (schema-aware for normalized JSON).")
    parser.add_argument("--input_dir", required=True, help="Directory containing source files (.txt/.md/.json)")
    parser.add_argument("--out_index", required=True, help="Path to write FAISS index (e.g., ./rag_store/index.faiss)")
    parser.add_argument("--out_meta", required=True, help="Path to write meta JSONL (e.g., ./rag_store/meta.jsonl)")
    parser.add_argument("--max_tokens", type=int, default=800, help="Max tokens per chunk (header+body)")
    parser.add_argument("--overlap", type=int, default=100, help="Token overlap between adjacent chunks")
    parser.add_argument(
        "--embedding_model",
        default=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
        help="Azure embeddings model name (can also come from env AZURE_OPENAI_EMBEDDING_DEPLOYMENT)",
    )
    parser.add_argument(
        "--embed_batch",
        type=int,
        default=128,
        help="Batch size for embedding requests",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    ns = parse_args(argv or sys.argv[1:])
    input_dir = Path(ns.input_dir).resolve()
    out_index = Path(ns.out_index).resolve()
    out_meta = Path(ns.out_meta).resolve()

    build_index(
        input_dir=input_dir,
        out_index=out_index,
        out_meta=out_meta,
        max_tokens=ns.max_tokens,
        overlap=ns.overlap,
        embedding_model=ns.embedding_model,
        embed_batch=ns.embed_batch,
    )


if __name__ == "__main__":
    main()
