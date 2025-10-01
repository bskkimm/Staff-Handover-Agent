from pathlib import Path
import streamlit as st
import html
from .rag_app import RAGChatbot
from .index_manager import ensure_index_ready



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
    # ----- Page title + styles -----
    st.markdown('<style>h4 { margin-top: -45px !important; font-weight: 600 !important; }</style>', unsafe_allow_html=True)
    st.markdown("#### 업무 Q&A 챗봇")
    st.caption("업로드된 인수인계 자료를 근거로 전임자의 페르소나로 답변합니다.")

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

    # ----- Ensure index is ready (trigger build on page entry) -----
    with st.spinner("자료를 정리하고 인덱스를 준비하는 중..."):
        ok, msg, rebuilt = ensure_index_ready()
    if not ok:
        st.error(msg)
        st.info("업로드된 파일을 확인하거나 .env 설정(Azure OpenAI 키/엔드포인트/버전 및 임베딩/채팅 배포명)을 점검해주세요.")
        return

    if rebuilt:
        try:
            st.cache_resource.clear()   # drop cached RAGChatbot so it reloads the fresh FAISS/meta
            st.toast("인덱스가 최신 상태로 갱신되었습니다.", icon="✅")
        except Exception:
            pass

    # ----- Get chatbot (cached) & initialize if needed -----
    chatbot = get_chatbot()
    if not chatbot.is_initialized():
        success, message = chatbot.initialize()
        if not success:
            st.error(message)
            st.info("💡 .env 파일의 Azure OpenAI 설정과 인덱스 경로를 확인해주세요.")
            return

    # ----- Session state -----
    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []

    # ----- UI container -----
    st.markdown('<div class="qa-container">', unsafe_allow_html=True)

    # Render past messages
    for msg in st.session_state.qa_history:
        _render_msg(msg["role"], msg["content"])

    # Reset button (centered) when there is history
    if st.session_state.qa_history:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("대화 초기화", type="secondary", use_container_width=True, key="reset_btn"):
                st.session_state.qa_history = []
                st.rerun()

    # ----- Chat input -----
    query = st.chat_input("전임자에게 질문해보세요")

    if query:
        # Add & render user message
        st.session_state.qa_history.append({"role": "user", "content": query})
        _render_msg("user", query)

        # Get answer
        with st.spinner("🤔답변을 준비하고 있습니다..."):
            result = chatbot.ask(query, k=6)

        if result.get("error"):
            response = result["error"]
        else:
            response = result.get("answer", "그 부분은 제가 가진 자료에서는 확인이 안 되네요")

        # Add & render assistant message
        st.session_state.qa_history.append({"role": "assistant", "content": response})
        _render_msg("assistant", response)

        # Sources (if any)
        if result.get("sources") and not result.get("error"):
            with st.expander("🔎 사용한 출처 보기"):
                for source in result["sources"]:
                    st.write(f"- {source['filename']} (chunk {source['chunk_index']}), 유사도: {source['score']:.3f}")

        # Re-render to place reset button immediately
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)