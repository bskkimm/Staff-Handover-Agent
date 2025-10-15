# handover/chatbot/index_manager.py
from __future__ import annotations
import os, time
from pathlib import Path
from typing import Tuple

# Keep these consistent with rag_app.py
# 기본값 (레거시, session_id 없을 때)
INDEX_PATH = Path("./data/rag_store/index.faiss")
META_PATH  = Path("./data/rag_store/meta.jsonl")
INPUT_DIR  = Path("./data/preprocessed_data")

def _get_session_paths(session_id: str = None):
    """세션별 경로 반환"""
    if not session_id:
        return INDEX_PATH, META_PATH, INPUT_DIR

    session_index = Path(f"./data/sessions/{session_id}/rag_store/index.faiss")
    session_meta = Path(f"./data/sessions/{session_id}/rag_store/meta.jsonl")
    session_input = Path(f"./data/sessions/{session_id}/preprocessed_data")

    return session_index, session_meta, session_input

def _latest_mtime_under(root: Path) -> float:
    latest = 0.0
    if not root.exists():
        return 0.0
    for p in root.rglob("*"):
        if p.is_file():
            latest = max(latest, p.stat().st_mtime)
    return latest

def _target_mtime(index_path: Path, meta_path: Path) -> float:
    mts = []
    if index_path.exists(): mts.append(index_path.stat().st_mtime)
    if meta_path.exists():  mts.append(meta_path.stat().st_mtime)
    return min(mts) if mts else 0.0  # both should exist; use the older one

def needs_rebuild(session_id: str = None) -> bool:
    index_path, meta_path, input_dir = _get_session_paths(session_id)
    src_latest = _latest_mtime_under(input_dir)
    tgt_time   = _target_mtime(index_path, meta_path)
    # Rebuild if outputs missing, or sources newer than outputs
    return (not index_path.exists() or not meta_path.exists() or src_latest > tgt_time)

def build_now(session_id: str = None, embedding_model: str | None = None, max_tokens: int = 800, overlap: int = 100, embed_batch: int = 128) -> None:
    # Import lazily to avoid circulars
    from .build_index import build_index  # uses the function, not CLI
    index_path, meta_path, input_dir = _get_session_paths(session_id)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    build_index(
        input_dir=input_dir.resolve(),
        out_index=index_path.resolve(),
        out_meta=meta_path.resolve(),
        max_tokens=max_tokens,
        overlap=overlap,
        embedding_model=embedding_model or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
        embed_batch=embed_batch,
    )

def ensure_index_ready(session_id: str = None) -> Tuple[bool, str, bool]:
    """
    Returns: (ok, message, rebuilt)
    """
    try:
        if needs_rebuild(session_id):
            build_now(session_id)
            return True, "Index (re)built.", True
        return True, "Index up to date.", False
    except Exception as e:
        return False, f"Index build failed: {e}", False
