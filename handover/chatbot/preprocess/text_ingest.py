# handover/chatbot/preprocess/text_ingest.py
import json
from typing import List, Tuple, Dict, Any, Optional
from ..chunkers import json_chunker

_tok = None

def set_tokenizer(tok):
    global _tok
    _tok = tok
    json_chunker.set_tokenizer(tok)

def _sliding_window(text: str, max_tokens: int = 800, overlap: int = 100) -> List[str]:
    if not text.strip():
        return []
    ids = _tok.encode(text)
    chunks: List[str] = []
    start = 0
    step = max(1, max_tokens - max(0, overlap))
    while start < len(ids):
        end = min(start + max_tokens, len(ids))
        chunks.append(_tok.decode(ids[start:end]))
        if end == len(ids):
            break
        start += step
    return chunks

def chunk_text(
    text: str,
    max_tokens: int = 800,
    overlap: int = 100,
    source: Optional[str] = None,
) -> List[str]:
    """JSON → schema-aware chunks; plain text → sliding window."""
    try:
        data = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return _sliding_window(text, max_tokens, overlap)

    items = json_chunker.chunks_from_json_obj(
        data,
        source=source or "inline_json",
        max_tokens=max_tokens,
        overlap=overlap,
    )
    return [it["text"] for it in items]

def chunk_text_with_meta(
    text: str,
    max_tokens: int = 800,
    overlap: int = 100,
    source: Optional[str] = None,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Same as chunk_text, but also returns metadata rows for meta.jsonl."""
    try:
        data = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        pieces = _sliding_window(text, max_tokens, overlap)
        metas = [{
            "source": source or "inline",
            "type": "plain",
            "section": "content",
            "chunk_index_in_doc": i
        } for i in range(len(pieces))]
        return pieces, metas

    items = json_chunker.chunks_from_json_obj(
        data,
        source=source or "inline_json",
        max_tokens=max_tokens,
        overlap=overlap,
    )
    texts = [it["text"] for it in items]
    metas = [{k: v for k, v in it.items() if k != "text"} for it in items]
    return texts, metas
