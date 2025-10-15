# auth/login_page.py
"""
인계자/인수자 로그인 페이지
"""
import streamlit as st
from .database import auth_db


def render_login_page():
    """로그인 페이지 렌더링"""

    # 스타일 적용
    st.markdown("""
    <style>
    .login-container {
        max-width: 500px;
        margin: 60px auto;
        padding: 40px;
        background: #ffffff;
        border-radius: 16px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    .login-title {
        text-align: center;
        font-size: 75px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 12px;
    }
    .login-subtitle {
        text-align: center;
        font-size: 16px;
        color: #6b7280;
        margin-bottom: 40px;
    }
    .role-card {
        text-align: center;
        padding: 24px;
        border: 2px solid #e5e7eb;
        border-radius: 12px;
        background: #f9fafb;
        margin-bottom: 16px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .role-card:hover {
        border-color: #ef4444;
        background: #ffffff;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .role-icon {
        font-size: 40px;
        margin-bottom: 12px;
    }
    .role-title {
        font-size: 18px;
        font-weight: 600;
        color: #111827;
        margin-bottom: 8px;
    }
    .role-desc {
        font-size: 14px;
        color: #6b7280;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-title">BATON</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">BATON과 함께 AI로 업무 인수인계하기</div>', unsafe_allow_html=True)

    # 역할 선택이 안 되어 있으면 역할 선택 화면
    if "role_selection" not in st.session_state:
        st.session_state.role_selection = None

    if st.session_state.role_selection is None:
        render_role_selection()
    elif st.session_state.role_selection == "transferor":
        render_transferor_login()
    elif st.session_state.role_selection == "receiver":
        render_receiver_login()

    st.markdown('</div>', unsafe_allow_html=True)


def render_role_selection():
    """역할 선택 화면"""
    st.markdown("### 역할을 선택해주세요")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("인계자로 시작", use_container_width=True, type="primary", key="btn_transferor"):
            st.session_state.role_selection = "transferor"
            st.rerun()
        st.caption("업무를 인계할 파일을 업로드합니다")

    with col2:
        if st.button("인수자로 시작", use_container_width=True, type="secondary", key="btn_receiver"):
            st.session_state.role_selection = "receiver"
            st.rerun()
        st.caption("인계받은 자료를 확인합니다")


def render_transferor_login():
    """인계자 로그인 화면"""
    st.markdown("### 인계자 로그인")
    st.caption("업무를 인계할 인수자를 지정하고 파일을 업로드하세요")

    with st.form("transferor_login_form"):
        transferor_id = st.text_input("인계자 사번", placeholder="예: 11830")
        receiver_id = st.text_input("인수자 사번", placeholder="예: 11832")

        col1, col2 = st.columns([1, 1])
        with col1:
            submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")
        with col2:
            if st.form_submit_button("뒤로가기", use_container_width=True):
                st.session_state.role_selection = None
                st.rerun()

        if submitted:
            if not transferor_id or not receiver_id:
                st.error("모든 필드를 입력해주세요")
            elif transferor_id == receiver_id:
                st.error("인계자와 인수자는 다른 사번이어야 합니다")
            else:
                # 세션 생성
                try:
                    session = auth_db.create_session(transferor_id, receiver_id)

                    # 세션 상태 저장
                    st.session_state.logged_in = True
                    st.session_state.user_role = "transferor"
                    st.session_state.employee_id = transferor_id
                    st.session_state.session_id = session.session_id
                    st.session_state.receiver_id = receiver_id
                    st.session_state.nav = "파일 업로드"

                    st.success(f"인계 세션이 생성되었습니다! 인수자: {receiver_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"로그인 실패: {e}")


def render_receiver_login():
    """인수자 로그인 화면"""
    st.markdown("### 인수자 로그인")
    st.caption("사번을 입력하여 인계받은 자료를 확인하세요")

    with st.form("receiver_login_form"):
        receiver_id = st.text_input("인수자 사번", placeholder="예: 2024002")

        col1, col2 = st.columns([1, 1])
        with col1:
            submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")
        with col2:
            if st.form_submit_button("뒤로가기", use_container_width=True):
                st.session_state.role_selection = None
                st.rerun()

        if submitted:
            if not receiver_id:
                st.error("사번을 입력해주세요")
            else:
                # 인수자로 지정된 세션 조회
                sessions = auth_db.get_sessions_by_receiver(receiver_id)

                if not sessions:
                    st.error("해당 사번으로 지정된 인계 세션이 없습니다")
                else:
                    # 가장 최근 세션 선택 (향후 여러 세션 선택 UI 추가 가능)
                    session = sessions[0]

                    # 세션 상태 저장
                    st.session_state.logged_in = True
                    st.session_state.user_role = "receiver"
                    st.session_state.employee_id = receiver_id
                    st.session_state.session_id = session.session_id
                    st.session_state.transferor_id = session.transferor_id
                    st.session_state.nav = "메인"

                    st.success(f"로그인 성공! 인계자: {session.transferor_id}")
                    st.rerun()
