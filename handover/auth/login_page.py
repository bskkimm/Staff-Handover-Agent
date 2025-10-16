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
    /* Streamlit 기본 padding 제거 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 1rem;
    }
    
    /* Streamlit 기본 요소 숨기기 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .main-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 0 20px;
    }
    .login-title {
        text-align: center;
        font-size: 64px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 8px;
        letter-spacing: -2px;
    }
    .login-subtitle {
        text-align: center;
        font-size: 14px;
        color: #6b7280;
        margin-bottom: 25px;
    }
    .section-title {
        text-align: center;
        font-size: 20px;
        font-weight: 600;
        color: #111827;
        margin-bottom: 30px;
    }
    /* 버튼 컨테이너 */
    .main-container > div {
        max-width: 400px;
        margin: 0 auto;
    }
    /* 버튼 스타일 */
    .stButton > button {
        width: 100%;
        height: 56px;
        background: #ffffff;
        color: #111827;
        border: 2px solid #e5e7eb;
        font-size: 16px;
        font-weight: 600;
        border-radius: 12px;
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .stButton > button:hover {
        background: #fef2f2;
        border-color: #ef4444;
        color: #ef4444;
        box-shadow: 0 4px 12px rgba(239,68,68,0.15);
        transform: translateY(-1px);
    }
    .stButton > button:active {
        transform: translateY(0px);
    }
    .login-form-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 28px;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    .form-title {
        font-size: 20px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 4px;
    }
    .form-subtitle {
        font-size: 13px;
        color: #6b7280;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-container">', unsafe_allow_html=True)
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
    st.markdown('<div class="section-title">역할을 선택해주세요</div>', unsafe_allow_html=True)

    # 중앙 정렬을 위한 컬럼 사용
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("인계자로 시작", key="btn_transferor", use_container_width=True):
            st.session_state.role_selection = "transferor"
            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("인수자로 시작", key="btn_receiver", use_container_width=True):
            st.session_state.role_selection = "receiver"
            st.rerun()


def render_transferor_login():
    """인계자 로그인 화면"""
    st.markdown('<div class="login-form-container">', unsafe_allow_html=True)
    st.markdown('<div class="form-title">📤 인계자 로그인</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-subtitle">업무를 인계할 인수자를 지정하고 파일을 업로드하세요</div>', unsafe_allow_html=True)

    with st.form("transferor_login_form"):
        transferor_id = st.text_input("인계자 사번", placeholder="예: 11830")
        receiver_id = st.text_input("인수자 사번", placeholder="예: 11832")

        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1], gap="small")
        with col1:
            submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")
        with col2:
            back = st.form_submit_button("뒤로가기", use_container_width=True)

        if back:
            st.session_state.role_selection = None
            st.rerun()

        if submitted:
            if not transferor_id or not receiver_id:
                st.error("사번을 입력해주세요")
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
                    st.session_state.transferor_id = transferor_id
                    st.session_state.receiver_id = receiver_id
                    st.session_state.nav = "파일 업로드"

                    st.success(f"인계 세션이 생성되었습니다! 인수자: {receiver_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"로그인 실패: {e}")

    st.markdown('</div>', unsafe_allow_html=True)


def render_receiver_login():
    """인수자 로그인 화면"""
    st.markdown('<div class="login-form-container">', unsafe_allow_html=True)
    st.markdown('<div class="form-title">📥 인수자 로그인</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-subtitle">사번을 입력하여 인계받은 자료를 확인하세요</div>', unsafe_allow_html=True)

    with st.form("receiver_login_form"):
        receiver_id = st.text_input("인수자 사번", placeholder="예: 11832")

        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1], gap="small")
        with col1:
            submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")
        with col2:
            back = st.form_submit_button("뒤로가기", use_container_width=True)

        if back:
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
                    st.session_state.receiver_id = receiver_id
                    st.session_state.nav = "메인"

                    st.success(f"로그인 성공! 인계자: {session.transferor_id}")
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)