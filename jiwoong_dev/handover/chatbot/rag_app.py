import os
import json
import html
from pathlib import Path
from typing import List, Tuple, Dict

import numpy as np
import faiss
import streamlit as st
from dotenv import load_dotenv
from openai import AzureOpenAI

# ----------------------------
# Env + Constants
# ----------------------------
load_dotenv()

SYSTEM_PERSONA = """
당신은 인사팀 대리 김민수입니다. 후임자에게 업무를 인수인계하는 상황에서 질문에 답변하고 있습니다.

## 김민수의 대화 특성:
- 차분하고 친근한 선임자의 말투
- 정중하지만 격식을 차리지 않는 자연스러운 대화
- 구체적이고 실용적인 정보 제공
- "~습니다" 보다는 "~해요", "~입니다" 정도의 자연스러운 존댓말
- 시간은 항상 KST로 명시
- 팀원들(오현우님, 김가은님, 서유나님)과의 협업 관계 언급

## 답변 규칙:
1. 제공된 HR 스케줄 문서 내용만 근거로 답변합니다.
2. 문서에 없는 내용은 '그 부분은 제가 가진 자료에서는 확인이 안 되네요'라고 자연스럽게 답변합니다.
3. 구체적인 일정이나 업무가 있다면 정확한 날짜와 시간을 KST로 명시해주세요.
4. 이메일 형식이 아닌 자연스러운 대화 형태로 답변하세요.
5. 인사말이나 마무리 인사는 생략하고 질문에 대한 답변에만 집중하세요.
"""

# Adjust these to where your embedding script saved them
INDEX_PATH = "./chatbot/rag_store/index.faiss"
META_PATH = "./chatbot/rag_store/meta.jsonl"

# ----------------------------
# Utils
# ----------------------------
def _norm(a: np.ndarray) -> np.ndarray:
    return a / (np.linalg.norm(a, axis=-1, keepdims=True) + 1e-12)

def get_azure_client() -> AzureOpenAI:
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_ver = os.getenv("AZURE_OPENAI_API_VERSION")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not api_key or not api_ver or not endpoint:
        raise RuntimeError(
            "Azure OpenAI env vars missing. "
            "Set AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_ENDPOINT in .env"
        )
    return AzureOpenAI(api_key=api_key, api_version=api_ver, azure_endpoint=endpoint)

def load_rag_store(index_path: str, meta_path: str):
    if not Path(index_path).exists():
        raise FileNotFoundError(f"FAISS index not found: {index_path}")
    if not Path(meta_path).exists():
        raise FileNotFoundError(f"Metadata JSONL not found: {meta_path}")
    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = [json.loads(line) for line in f]
    return index, meta

def embed_text(client: AzureOpenAI, text: str) -> np.ndarray:
    emb_deploy = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    if not emb_deploy:
        raise RuntimeError("AZURE_OPENAI_EMBEDDING_DEPLOYMENT is not set in .env")
    vec = client.embeddings.create(model=emb_deploy, input=text).data[0].embedding
    return np.array(vec, dtype="float32")

def retrieve_topk(index, meta, q_vec: np.ndarray, k: int = 6) -> List[Tuple[float, Dict]]:
    q = _norm(q_vec).reshape(1, -1)
    scores, idxs = index.search(q, k)
    results = []
    for s, i in zip(scores[0], idxs[0]):
        if int(i) >= 0:
            results.append((float(s), meta[int(i)]))
    return results

def build_context(snippets: List[Tuple[float, Dict]]) -> str:
    lines = []
    for score, m in snippets:
        src = f"{Path(m['source']).name}#chunk{m['chunk_index_in_doc']}"
        lines.append(f"[{src}] {m['text']}")
    return "\n\n".join(lines)

def build_index_from_files(files_data: Dict[str, str], index_path: str, meta_path: str):
    """업로드된 파일들로 FAISS 인덱스 구축"""
    import tempfile
    import shutil
    
    # 임시 디렉토리에 txt 파일들 생성
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 파일들을 임시 디렉토리에 저장
        for filename, content in files_data.items():
            base_name = Path(filename).stem
            txt_filename = f"{base_name}.txt"
            txt_path = os.path.join(temp_dir, txt_filename)
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # build_index.py를 사용하여 인덱스 구축
        import subprocess
        import sys
        
        # build_index.py 실행
        cmd = [
            sys.executable, "build_index.py",
            "--input_dir", temp_dir,
            "--out_index", os.path.join(temp_dir, "index.faiss"),
            "--out_meta", os.path.join(temp_dir, "meta.jsonl"),
            "--max_tokens", "800",
            "--overlap", "100",
            "--batch_size", "32"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        if result.returncode != 0:
            raise Exception(f"인덱스 구축 실패: {result.stderr}")
        
        # 생성된 인덱스 파일들을 목적지로 복사
        temp_index = os.path.join(temp_dir, "index.faiss")
        temp_meta = os.path.join(temp_dir, "meta.jsonl")
        
        if os.path.exists(temp_index) and os.path.exists(temp_meta):
            # 목적지 디렉토리 생성
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            
            # 파일 복사
            shutil.copy2(temp_index, index_path)
            shutil.copy2(temp_meta, meta_path)
        else:
            raise Exception("인덱스 파일 생성 실패")
            
    finally:
        # 임시 디렉토리 정리
        shutil.rmtree(temp_dir, ignore_errors=True)


def build_index_from_preprocessed_json(index_path: str, meta_path: str):
    """preprocessed.json을 단일 문서로 취급하여 임베딩 후 인덱스 구축"""
    from pathlib import Path
    import tempfile, shutil, json
    json_path = Path(__file__).resolve().parent.parent / "data" / "preprocessed" / "preprocessed.json"
    if not json_path.exists():
        raise FileNotFoundError("preprocessed.json not found. 먼저 전처리를 실행하세요.")

    temp_dir = tempfile.mkdtemp()
    try:
        txt_path = os.path.join(temp_dir, "preprocessed.txt")
        data = json.loads(json_path.read_text(encoding="utf-8"))
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2))

        import subprocess, sys
        cmd = [
            sys.executable, "build_index.py",
            "--input_dir", temp_dir,
            "--out_index", os.path.join(temp_dir, "index.faiss"),
            "--out_meta", os.path.join(temp_dir, "meta.jsonl"),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode != 0:
            raise Exception(f"인덱스 구축 실패: {result.stderr}")

        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        shutil.copy2(os.path.join(temp_dir, "index.faiss"), index_path)
        shutil.copy2(os.path.join(temp_dir, "meta.jsonl"), meta_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def build_user_prompt(question: str, context: str) -> str:
    return f"""
{SYSTEM_PERSONA}

다음은 인수인계 문서에서 검색된 관련 내용이에요(이것만 근거로 답변하세요):

{context}

질문: {question}

규칙:
- 제공된 문서 내용만 기반으로 답변해요.
- 문서에 없으면 '그 부분은 제가 가진 자료에서는 확인이 안 되네요'라고 말해요.
- 정확한 날짜/시간은 KST로 명시해요.
- 마지막에 [filename#chunkN] 형태로 출처를 간단히 적어줘요.
""".strip()

def chat_with_context(client: AzureOpenAI, system_prompt: str, user_prompt: str) -> str:
    chat_deploy = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  # e.g., gpt-4o-mini
    if not chat_deploy:
        raise RuntimeError("AZURE_OPENAI_CHAT_DEPLOYMENT is not set in .env")
    resp = client.chat.completions.create(
        model=chat_deploy,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=900,
    )
    return resp.choices[0].message.content.strip()

def _render_msg(role: str, content: str):
    safe = html.escape(content).replace("\n", "<br>")
    row_cls = "user" if role == "user" else "assistant"
    bub_cls = "user" if role == "user" else "assistant"
    st.markdown(
        f'<div class="msg-row {row_cls}"><div class="bubble {bub_cls}">{safe}</div></div>',
        unsafe_allow_html=True
    )

# ----------------------------
# Streamlit App
# ----------------------------
def run_chat(use_sidebar=True):
    if use_sidebar:
        st.set_page_config(page_title="Handover RAG (TXT)", layout="wide")
    st.markdown("""
    <style>
    .qa-container { max-width: 900px; margin:auto; }
    .msg-row { display:flex; margin:8px 0; }
    .msg-row.user { justify-content:flex-end; }
    .msg-row.assistant { justify-content:flex-start; }
    .bubble { padding:12px 16px; border-radius:16px; line-height:1.6;
              box-shadow:0 1px 3px rgba(0,0,0,0.05); word-wrap:break-word; 
              white-space:pre-wrap; font-size:16px; }
    .bubble.user { display:inline-block; max-width:70%; background:#dbeafe; 
                   border:1px solid #bfdbfe; text-align:left; border-bottom-right-radius:6px; }
    .bubble.assistant { flex:1; background:#f9fafb; border:1px solid #e5e7eb; text-align:left; }
    .persona-info { background:#f0f9ff; border:1px solid #bae6fd; border-radius:8px; 
                    padding:12px; margin:8px 0; font-size:14px; color:#0369a1; }
    </style>
    """, unsafe_allow_html=True)

    # Check keys early
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        st.error("❌ AZURE_OPENAI_API_KEY가 설정되지 않았습니다. .env를 확인하세요.")
        return

    # Load FAISS + metadata once
    try:
        index, meta = load_rag_store(INDEX_PATH, META_PATH)
    except FileNotFoundError as e:
        st.warning("🔍 FAISS 인덱스가 없습니다. 업로드된 파일들로 인덱스를 생성합니다...")
        
        # 인덱스 자동 생성
        try:
            from utils import get_uploaded_files_data
            files_data = get_uploaded_files_data()
            
            if not files_data:
                st.error("❌ 업로드된 파일이 없습니다. 먼저 파일을 업로드해주세요.")
                return
            
            # 임베딩 생성
            with st.spinner("🔄 문서 임베딩을 생성하고 인덱스를 구축 중..."):
                build_index_from_files(files_data, INDEX_PATH, META_PATH)
            
            # 다시 로드
            index, meta = load_rag_store(INDEX_PATH, META_PATH)
            st.success("✅ FAISS 인덱스가 성공적으로 생성되었습니다!")
            
        except Exception as build_error:
            st.error(f"❌ 인덱스 생성 실패: {build_error}")
            return

    # Client
    try:
        client = get_azure_client()
    except Exception as e:
        st.error(f"Azure OpenAI 클라이언트 생성 실패: {e}")
        return

    # UI header
    st.markdown('<div class="qa-container">', unsafe_allow_html=True)
    top_col1, top_col2 = st.columns([4, 2])
    with top_col1:
        st.markdown("### 업무 Q&A 챗봇 (RAG)")
        st.caption("로컬 임베딩 + FAISS 검색 기반 RAG (TXT 전용)")
    with top_col2:
        k = st.slider("Top-k 문맥 개수", 3, 12, 6)
        if st.button("대화 초기화", type="secondary", use_container_width=True):
            st.session_state.pop("qa_history", None)
            st.rerun()

    # Session state
    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []

    # Render history
    for msg in st.session_state.qa_history:
        _render_msg(msg["role"], msg["content"])

    # Input
    query = st.chat_input("전임자에게 질문해보세요")
    if query:
        st.session_state.qa_history.append({"role": "user", "content": query})
        _render_msg("user", query)

        with st.spinner("🤔 문서에서 관련 내용을 찾고 있어요..."):
            try:
                # 1) Embed query
                q_vec = embed_text(client, query)
                # 2) Retrieve
                hits = retrieve_topk(index, meta, q_vec, k=k)
                if not hits:
                    response = "그 부분은 제가 가진 자료에서는 확인이 안 되네요"
                else:
                    # 3) Build context + prompt
                    context = build_context(hits)
                    user_prompt = build_user_prompt(query, context)
                    # 4) Chat
                    response = chat_with_context(client, SYSTEM_PERSONA, user_prompt)
            except Exception as e:
                response = f"오류가 발생했어요: {e}"

        st.session_state.qa_history.append({"role": "assistant", "content": response})
        _render_msg("assistant", response)

        # Optional: show sources
        if 'hits' in locals() and hits:
            with st.expander("🔎 사용한 출처 보기"):
                for s, m in hits:
                    st.write(f"- {Path(m['source']).name} (chunk {m['chunk_index_in_doc']}), score={s:.3f}")

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    run_chat()
