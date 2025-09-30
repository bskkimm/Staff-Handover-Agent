import streamlit as st

from .logic import run_preprocess_from_db


def render():
    st.header("데이터 전처리")
    if st.button("전처리 실행", type="primary"):
        result = run_preprocess_from_db()
        summary = result.get("summary", {})
        st.success(
            f"완료 · 총 {summary.get('total_files', 0)}개 | 이메일 {summary.get('emails', 0)} | 회의록 {summary.get('meetings', 0)} | 개인노트 {summary.get('personal_notes', 0)}"
        )
        with st.expander("전처리 결과 상세"): 
            st.json(result.get("processed_data", {}))


