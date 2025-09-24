1. build_index.py
   ├─ingest.py
   ├─rag_store.py

- Reads all .txt files in a given folder and converts them into embeddings for similiarity search.

Read .txt → split into chunks → create embeds using AOI → normalizes embeds and builds a FAISS index

Saves:

'./rag_store/index.faiss' → FAISS inner-product index (cosine search)

'./rag_store/meta.jsonl' → one JSON line per chunk (metadata + text)

CLI usage:

python build_index.py --input_dir ./data \
  --out_index ./handover/chatbot/rag_store/index.faiss \
  --out_meta  ./handover/chatbot/rag_store/meta.jsonl \
  --max_tokens 800 --overlap 100 --batch_size 32


2. ingest.py

- Reusable client, chunking, embeddings utilities.

    get_client() → returns an Azure OpenAI client (reads .env)

    read_text(uploaded_file) → read .txt/.md content from an upload/file-like object

    chunk_text(text, max_tokens=800, overlap=100) → token-aware splitting

    embed_texts(client, model, texts) → L2-normalized embeddings as np.ndarray [n, d]


3. rag_store.py — Vector store + metadata helpers

- FAISS index + metadata I/O & search.

    load_store(index_path, meta_path) → (index, meta_rows)

    save_store(index, meta, index_path, meta_path) → persist both files

    create_empty_index(dim) → cosine-ready FAISS IP index

    add_vectors(index, vecs) → add already-normalized vectors

    search(index, meta, qvec, k=6) → top-k results as [{score, meta}, ...]

    normalize(a) → L2 normalization (used for queries)


4. rag_app.py

- A minimal RAG chat app built with Streamlit to test the build_index.py

1. loads a FAISS vector index + metadata you created offline,

2. embeds the user’s question with Azure OpenAI,

3. retrieves the most similar chunks,

4. prompts a chat model to answer only from those chunks (with a fixed “HR handover” persona, in Korean),

5. displays the answer plus the cited chunks.

