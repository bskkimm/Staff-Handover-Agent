import streamlit as st


def render():
    st.header("지식기반 Q&A 챗봇")
    try:
        from .rag_app import run_chat
        run_chat(use_sidebar=False)
    except Exception as e:
        st.error(f"챗봇 실행 중 오류: {e}")


