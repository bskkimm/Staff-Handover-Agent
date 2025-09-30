import streamlit as st
from .logic import build_report


def render():
    st.header("요약 레포트 생성")
    if st.button("레포트 생성", type="primary"):
        res = build_report()
        if not res.get("success"):
            st.error("레포트 생성 실패")
            return
        md_path = res.get("markdown")
        st.success("레포트 생성 완료")
        if md_path:
            st.markdown(open(md_path, "r", encoding="utf-8").read())
            st.download_button("Markdown 다운로드", data=open(md_path, "rb").read(), file_name="report.md")


