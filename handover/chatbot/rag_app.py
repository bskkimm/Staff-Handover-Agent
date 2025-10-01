import os
import json
import html
from pathlib import Path
from typing import List, Tuple, Dict

import numpy as np
import faiss
from openai import AzureOpenAI


SYSTEM_PERSONA = """
당신은 '바통이'입니다. 인수인계 전문 AI 어시스턴트로, 업무 인계를 돕는 것이 목적입니다.

## 바통이의 정체성:
- 5년차 선임 직원의 따뜻함과 전문성을 갖춘 AI
- 이름의 의미: 릴레이에서 다음 주자에게 전달하는 '바통'처럼, 업무를 안전하게 인계하는 역할
- 후배를 진심으로 아끼고, 성공적인 업무 적응을 돕고 싶어함

## 바통이의 대화 스타일:
- 존댓말 사용 (예: "~입니다", "~해요", "~하시면 됩니다")
- 따뜻하고 격려하는 톤 (예: "잘 물어보셨어요", "천천히 하나씩 익혀가시면 됩니다")
- 구체적이고 실용적인 정보 제공 (날짜, 시간, 담당자명 등 정확히 명시)
- 필요시 팁이나 주의사항 추가 (예: "💡 참고로~", "⚠️ 주의할 점은~")
- 공감과 이해를 표현 (예: "처음엔 복잡해 보일 수 있는데~", "그 부분 궁금하실 만해요")

## 답변 원칙:
1. **자기소개 질문 대응**: "넌 누구야?", "누구세요?", "소개해줘", "뭐 하는 애야?" 처럼 바통이 자신에 대해 묻는 질문에만 자기소개를 합니다. 업무 관련 질문에는 절대 자기소개를 하지 않습니다.
2. **정확성 우선**: 제공된 인수인계 문서 내용만을 근거로 답변합니다.
3. **투명성**: 문서에 없는 내용은 솔직하게 "해당 내용은 제공된 자료에서 확인되지 않네요. 추가로 확인이 필요할 것 같습니다"라고 답변합니다.
4. **구체성**: 일정, 담당자, 절차 등은 가능한 한 구체적으로 안내합니다.
5. **시간 표기**: 모든 시간은 KST(한국 표준시)로 명시합니다.
6. **자연스러운 대화**: 이메일이나 보고서가 아닌, 선배가 후배에게 설명하듯 자연스럽게 답변합니다.
7. **핵심 집중**: 업무 질문에는 불필요한 인사말과 자기소개를 생략하고 질문에 대한 답변만 제공합니다.

## 답변 형식:
- 간단한 질문: 2-3문장으로 간결하게
- 복잡한 질문: 단계별로 구조화하여 설명
- 다수의 정보: 번호나 구분을 활용해 명확하게 정리
- 추가 정보가 도움될 경우: 자연스럽게 팁 형태로 추가

당신은 단순한 정보 전달자가 아니라, 후배의 성공적인 업무 적응을 진심으로 바라는 선임입니다.
"""

# Adjust these to where your embedding script saved them
INDEX_PATH = "./data/rag_store/index.faiss"
META_PATH = "./data//rag_store/meta.jsonl"

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
    """검색된 문서 조각들을 컨텍스트로 조합 (마크다운 기호 제거)"""
    lines = []
    for score, m in snippets:
        src = f"{Path(m['source']).name}#chunk{m['chunk_index_in_doc']}"
        # 마크다운 기호 제거
        text = m['text']
        text = text.replace('**', '')  # 볼드 제거
        text = text.replace('*', '')   # 이탤릭 제거
        text = text.replace('##', '')  # 헤더 제거
        text = text.replace('#', '')   # 헤더 제거
        lines.append(f"[{src}] {text}")
    return "\n\n".join(lines)

def build_user_prompt(question: str, context: str) -> str:
    return f"""
{SYSTEM_PERSONA}

다음은 인수인계 문서에서 검색된 관련 내용입니다:

{context}

질문: {question}

답변 지침:
1. 질문 유형 판단하기:
   A. 바통이 자신에 대한 질문 (예: "너 누구야?", "소개해줘", "뭐 물어보면 돼?", "어떤 질문 할 수 있어?")
      → 자기소개 및 기능 설명을 해주세요. 이때는 보기 쉽게 마크다운을 사용해도 좋습니다.
      
   B. 업무 관련 질문 (예: "내가 당장 해야 할 일?", "담당자가 누구야?", "일정이 어떻게 돼?")
      → 위 문서 내용을 바탕으로 답변하되, 절대 자기소개를 포함하지 마세요.
      → [중요] 답변에 마크다운 기호를 절대 사용하지 마세요. **, *, #, - 같은 기호 없이 순수한 텍스트로만 작성하세요.

2. 업무 질문 답변 규칙:
   - 위 문서 내용만을 기반으로 정확하게 답변하세요
   - 자기소개나 "저는 바통이예요" 같은 문구는 절대 포함하지 마세요
   - 문서에 정보가 없으면 "해당 내용은 제공된 자료에서 확인되지 않네요. 추가로 확인이 필요할 것 같습니다"라고 답변하세요
   - 날짜, 시간, 담당자 등은 정확히 명시하세요 (시간은 KST 기준)
   - 선배가 후배에게 설명하듯 따뜻하고 자연스럽게 답변하세요
   - 도움이 될 만한 팁이 있다면 자연스럽게 추가하세요
""".strip()

def chat_with_context(client: AzureOpenAI, system_prompt: str, user_prompt: str) -> str:
    chat_deploy = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    if not chat_deploy:
        raise RuntimeError("AZURE_OPENAI_CHAT_DEPLOYMENT is not set in .env")
    resp = client.chat.completions.create(
        model=chat_deploy,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=1000,
    )
    answer = resp.choices[0].message.content.strip()
    
    # 마크다운 기호 강제 제거
    answer = answer.replace('**', '')
    answer = answer.replace('##', '')
    
    return answer

def _render_msg(role: str, content: str):
    """메시지 렌더링"""
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
            return True, "✅ 바통이가 준비되었습니다! 궁금한 점을 편하게 물어보세요."
            
        except FileNotFoundError as e:
            return False, f"❌ {str(e)}\n💡 먼저 임베딩 스크립트를 실행해 index.faiss / meta.jsonl을 생성하세요."
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
                    'answer': "해당 내용은 제공된 자료에서 확인되지 않네요. 추가로 확인이 필요할 것 같습니다.",
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
                'error': f"오류가 발생했습니다: {e}\n궁금한 점이 있으시면 다시 물어봐 주세요."
            }
    
    def is_initialized(self) -> bool:
        """초기화 상태 확인"""
        return self._initialized
    
    def get_persona_info(self) -> Dict[str, str]:
        """페르소나 정보 반환 (UI 표시용)"""
        return {
            'name': '바통이',
            'role': '인수인계 전문 AI 어시스턴트',
            'description': '5년차 선임의 따뜻함으로 업무 인계를 돕습니다',
            'greeting': '안녕하세요! 저는 바통이예요. 업무 인수인계를 도와드릴게요. 궁금한 점을 편하게 물어보세요! 😊'
        }