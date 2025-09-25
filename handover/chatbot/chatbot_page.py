import streamlit as st
import html
from .rag_app import RAGChatbot

def _render_msg(role: str, content: str):
    """메시지 렌더링"""
    safe = html.escape(content).replace("\n", "<br>")
    row_cls = "user" if role == "user" else "assistant"
    bub_cls = "user" if role == "user" else "assistant"
    st.markdown(
        f'<div class="msg-row {row_cls}"><div class="bubble {bub_cls}">{safe}</div></div>',
        unsafe_allow_html=True
    )

@st.cache_resource
def get_chatbot():
    """RAG 챗봇 인스턴스 생성 (캐시됨)"""
    return RAGChatbot()

def run_chat():
    # CSS 스타일
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
    </style>
    """, unsafe_allow_html=True)

    # RAG 챗봇 초기화
    chatbot = get_chatbot()
    
    if not chatbot.is_initialized():
        success, message = chatbot.initialize()
        if not success:
            st.error(message)
            return

    # UI 헤더
    st.markdown('<div class="qa-container">', unsafe_allow_html=True)
    
    # 상단 컨트롤
    top_col1, top_col2 = st.columns([4, 2])
    with top_col1:
        st.markdown("### 업무 Q&A 챗봇 (RAG)")
        st.caption("로컬 임베딩 + FAISS 검색 기반 RAG")
    
    with top_col2:
        k = st.slider("Top-k 문맥 개수", 3, 12, 6)
        if st.button("대화 초기화", type="secondary", use_container_width=True):
            st.session_state.pop("qa_history", None)
            st.rerun()

    # 대화 기록 초기화
    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []

    # 대화 기록 렌더링
    for msg in st.session_state.qa_history:
        _render_msg(msg["role"], msg["content"])

    # 사용자 입력
    query = st.chat_input("전임자에게 질문해보세요")
    
    if query:
        # 사용자 메시지 추가 및 렌더링
        st.session_state.qa_history.append({"role": "user", "content": query})
        _render_msg("user", query)

        # AI 답변 생성
        with st.spinner("🤔 문서에서 관련 내용을 찾고 있어요..."):
            result = chatbot.ask(query, k=k)
            
            if result['error']:
                response = result['error']
            else:
                response = result['answer']

        # AI 답변 추가 및 렌더링
        st.session_state.qa_history.append({"role": "assistant", "content": response})
        _render_msg("assistant", response)

        # 출처 표시
        if result.get('sources'):
            with st.expander("🔎 사용한 출처 보기"):
                for source in result['sources']:
                    st.write(f"- {source['filename']} (chunk {source['chunk_index']}), score={source['score']:.3f}")

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    run_chat()