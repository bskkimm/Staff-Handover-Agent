"""
Batch builder: read a folder of .txt/.md → chunk → embed (Azure) → normalize →
save FAISS + JSONL. Reuses shared funcs from ingest.py and rag_store.py.

Usage:
python build_index.py --input_dir ./data \
--out_index ./handover/chatbot/rag_store/index.faiss \
--out_meta  ./handover/chatbot/rag_store/meta.jsonl \
--max_tokens 800 --overlap 100 --batch_size 32

"""

import os
import json
import argparse
from pathlib import Path
from typing import List, Dict

import numpy as np
from dotenv import load_dotenv

import ingest               # <— shared chunk/embed/client
import rag_store            # <— shared FAISS + meta I/O


def list_text_files(root: Path) -> List[Path]:
    exts = {".txt", ".md"}
    return sorted([p for p in root.rglob("*") if p.suffix.lower() in exts])


def read_txt(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def main():
    parser = argparse.ArgumentParser(description="Build FAISS index from .txt/.md using Azure embeddings")
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--out_index", default="./rag_store/index.faiss")
    parser.add_argument("--out_meta", default="./rag_store/meta.jsonl")
    parser.add_argument("--max_tokens", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=100)
    parser.add_argument("--batch_size", type=int, default=32)
    args = parser.parse_args()

    load_dotenv()
    client = ingest.get_client()
    emb_model = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    if not emb_model:
        raise RuntimeError("AZURE_OPENAI_EMBEDDING_DEPLOYMENT missing in .env")

    files = list_text_files(Path(args.input_dir))
    if not files:
        print("[INFO] No .txt/.md found."); return

    print(f"[INFO] Found {len(files)} files")

    all_chunks: List[str] = []
    meta_rows: List[Dict] = []
    gid = 0

    for doc_id, p in enumerate(files):
        text = read_txt(p)
        chunks = ingest.chunk_text(text, max_tokens=args.max_tokens, overlap=args.overlap)
        for i, ch in enumerate(chunks):
            all_chunks.append(ch)
            meta_rows.append({
                "global_chunk_id": gid,
                "doc_id": doc_id,
                "source": str(p),
                "chunk_index_in_doc": i,
                "text": ch
            })
            gid += 1

    if not all_chunks:
        print("[INFO] No chunks produced."); return

    print(f"[INFO] Embedding {len(all_chunks)} chunks with {emb_model}...")
    vecs_list: List[np.ndarray] = []
    for i in range(0, len(all_chunks), args.batch_size):
        vecs_list.append(ingest.embed_texts(client, emb_model, all_chunks[i:i+args.batch_size]))
    vecs = np.vstack(vecs_list).astype("float32")   # already L2-normalized by ingest.embed_texts

    index = rag_store.create_empty_index(vecs.shape[1])
    rag_store.add_vectors(index, vecs)
    rag_store.save_store(index, meta_rows, args.out_index, args.out_meta)

    print(f"[OK] Saved index -> {args.out_index}")
    print(f"[OK] Saved meta  -> {args.out_meta}")
    print("[DONE]")


if __name__ == "__main__":
    main()
