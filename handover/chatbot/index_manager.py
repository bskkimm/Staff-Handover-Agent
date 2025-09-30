# handover/chatbot/index_manager.py
from __future__ import annotations
import os, time
from pathlib import Path
from typing import Tuple

# Keep these consistent with rag_app.py
INDEX_PATH = Path("./data/rag_store/index.faiss")
META_PATH  = Path("./data/rag_store/meta.jsonl")
INPUT_DIR  = Path("./data/preprocessed")

def _latest_mtime_under(root: Path) -> float:
    latest = 0.0
    if not root.exists():
        return 0.0
    for p in root.rglob("*"):
        if p.is_file():
            latest = max(latest, p.stat().st_mtime)
    return latest

def _target_mtime() -> float:
    mts = []
    if INDEX_PATH.exists(): mts.append(INDEX_PATH.stat().st_mtime)
    if META_PATH.exists():  mts.append(META_PATH.stat().st_mtime)
    return min(mts) if mts else 0.0  # both should exist; use the older one

def needs_rebuild() -> bool:
    src_latest = _latest_mtime_under(INPUT_DIR)
    tgt_time   = _target_mtime()
    # Rebuild if outputs missing, or sources newer than outputs
    return (not INDEX_PATH.exists() or not META_PATH.exists() or src_latest > tgt_time)

def build_now(embedding_model: str | None = None, max_tokens: int = 800, overlap: int = 100, embed_batch: int = 128) -> None:
    # Import lazily to avoid circulars
    from .build_index import build_index  # uses the function, not CLI
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    build_index(
        input_dir=INPUT_DIR.resolve(),
        out_index=INDEX_PATH.resolve(),
        out_meta=META_PATH.resolve(),
        max_tokens=max_tokens,
        overlap=overlap,
        embedding_model=embedding_model or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
        embed_batch=embed_batch,
    )

def ensure_index_ready() -> Tuple[bool, str, bool]:
    """
    Returns: (ok, message, rebuilt)
    """
    try:
        if needs_rebuild():
            build_now()
            return True, "Index (re)built.", True
        return True, "Index up to date.", False
    except Exception as e:
        return False, f"Index build failed: {e}", False
