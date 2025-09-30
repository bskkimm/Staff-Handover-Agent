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
    # 페이지 제목 추가
    st.markdown('<style>h4 { margin-top: -45px !important; font-weight: 600 !important; }</style>', unsafe_allow_html=True)
    st.markdown("#### 업무 Q&A 챗봇")
    st.caption("업로드된 인수인계 자료를 근거로 전임자의 페르소나로 답변합니다.")
        
    # 채팅 UI 스타일 정의
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

    # RAG 챗봇 시스템 초기화
    chatbot = get_chatbot()
        
    if not chatbot.is_initialized():
        success, message = chatbot.initialize()
        if not success:
            st.error(message)
            st.info("💡 .env 파일에 Azure OpenAI 설정을 확인해주세요")
            return

    # 세션 상태 초기화
    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []

    # 컨테이너 시작
    st.markdown('<div class="qa-container">', unsafe_allow_html=True)

    # 기존 대화 내용을 화면에 표시
    for msg in st.session_state.qa_history:
        _render_msg(msg["role"], msg["content"])

    # 채팅 입력
    query = st.chat_input("전임자에게 질문해보세요")

    # 초기화 버튼 (중앙 정렬, 항상 표시)
    if st.session_state.qa_history:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("대화 초기화", type="secondary", use_container_width=True, key="reset_btn"):
                st.session_state.qa_history = []
                st.rerun()
        
    if query:
        # 사용자 메시지 추가 및 렌더링
        st.session_state.qa_history.append({"role": "user", "content": query})
        _render_msg("user", query)

        # AI 응답 생성 중임을 사용자에게 알리는 스피너
        with st.spinner("🤔답변을 준비하고 있습니다..."):
            result = chatbot.ask(query, k=6)
                        
            if result['error']:
                response = result['error']
            else:
                response = result['answer']
                        
            # AI 응답을 대화 기록에 저장하고 화면에 표시
            st.session_state.qa_history.append({"role": "assistant", "content": response})
            _render_msg("assistant", response)

        # 답변에 사용된 문서 출처 정보 표시
        if result.get('sources') and not result['error']:
            with st.expander("🔎 사용한 출처 보기"):
                for source in result['sources']:
                    st.write(f"- {source['filename']} (chunk {source['chunk_index']}), 유사도: {source['score']:.3f}")

        # 새 대화 후 즉시 초기화 버튼 표시
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)