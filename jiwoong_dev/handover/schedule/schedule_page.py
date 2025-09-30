import streamlit as st
from .logic import build_schedule_from_db


def render():
    st.header("스케줄 추출 및 시각화")
    if st.button("스케줄 생성", type="primary"):
        res = build_schedule_from_db()
        if not res.get("success"):
            st.error("스케줄 생성 실패")
            return
        outs = res.get("outputs", {})
        st.success("스케줄 생성 완료")
        if outs.get("timeline_png"):
            st.image(outs["timeline_png"]) 
            st.download_button("PNG 다운로드", data=open(outs["timeline_png"], "rb").read(), file_name="combined_schedule_timeline.png")


