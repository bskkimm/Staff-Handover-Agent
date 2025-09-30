import os
import json
import html
from pathlib import Path
from typing import List, Tuple, Dict

import numpy as np
import faiss
from openai import AzureOpenAI



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
INDEX_PATH = "./data/rag_store/index.faiss"
META_PATH = "./data/rag_store/meta.jsonl"

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

class RAGChatbot:
    """RAG 챗봇의 비즈니스 로직을 담당하는 클래스"""
    
    def __init__(self):
        self.client = None
        self.index = None
        self.meta = None
        self._initialized = False
    
    def initialize(self) -> Tuple[bool, str]:
        """RAG 시스템 초기화
        Returns:
            (success: bool, message: str)
        """
        try:
            # 환경변수 체크
            if not os.getenv("AZURE_OPENAI_API_KEY"):
                return False, "❌ AZURE_OPENAI_API_KEY가 설정되지 않았습니다. .env를 확인하세요."
            
            # Azure 클라이언트 생성
            self.client = get_azure_client()
            
            # RAG 스토어 로드
            self.index, self.meta = load_rag_store(INDEX_PATH, META_PATH)
            
            self._initialized = True
            return True, "✅ RAG 시스템이 성공적으로 초기화되었습니다."
            
        except FileNotFoundError as e:
            return False, f"❌ {str(e)}\n💡 먼저 임베딩 스크립트를 실행해 txt.faiss / txt.jsonl을 생성하세요."
        except Exception as e:
            return False, f"❌ 초기화 실패: {e}"
    
    def ask(self, query: str, k: int = 6) -> Dict[str, any]:
        """질문에 대한 답변 생성
        Args:
            query: 사용자 질문
            k: 검색할 문서 수
        Returns:
            {
                'answer': str,
                'sources': List[Dict],
                'error': str or None
            }
        """
        if not self._initialized:
            return {
                'answer': None,
                'sources': [],
                'error': 'RAG 시스템이 초기화되지 않았습니다.'
            }
        
        try:
            # 1) 쿼리 임베딩
            q_vec = embed_text(self.client, query)
            
            # 2) 관련 문서 검색
            hits = retrieve_topk(self.index, self.meta, q_vec, k=k)
            
            if not hits:
                return {
                    'answer': "그 부분은 제가 가진 자료에서는 확인이 안 되네요",
                    'sources': [],
                    'error': None
                }
            
            # 3) 컨텍스트 구성 및 답변 생성
            context = build_context(hits)
            user_prompt = build_user_prompt(query, context)
            answer = chat_with_context(self.client, SYSTEM_PERSONA, user_prompt)
            
            # 4) 소스 정보 정리
            sources = []
            for score, meta in hits:
                sources.append({
                    'filename': Path(meta['source']).name,
                    'chunk_index': meta['chunk_index_in_doc'],
                    'score': score
                })
            
            return {
                'answer': answer,
                'sources': sources,
                'error': None
            }
            
        except Exception as e:
            return {
                'answer': None,
                'sources': [],
                'error': f"오류가 발생했어요: {e}"
            }
    
    def is_initialized(self) -> bool:
        """초기화 상태 확인"""
        return self._initialized
