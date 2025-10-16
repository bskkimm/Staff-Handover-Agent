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
    /* Streamlit 기본 요소 숨기기 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 8rem;
        padding-bottom: 1rem;
    }
    
    /* 좌우 레이아웃용 구분선 */
    .divider-line {
        position: fixed;
        left: 48%;
        top: 30%;
        bottom: 40%;
        width: 2px;
        background: #e5e7eb;
        transform: translateX(-50%);
    }
    
    /* 왼쪽 섹션 스타일 */
    .left-content {
        text-align: center;
        padding-right: 55px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 300px;
        position: relative;
        top: 15px;
    }
    .login-title {
        font-size: 96px;
        font-weight: 700;
        color: #ef4444;
        margin-bottom: 8px;
        margin-top: 0;
        letter-spacing: -2px;
        line-height: 1;
    }
    .login-subtitle {
        font-size: 16px;
        color: #6b7280;
        margin-top: 0;
    }
    
    /* 오른쪽 섹션 스타일 */
    .right-content {
        padding-left: 85px;
    }
    
    /* 로그인 폼 래퍼 */
    .login-form-wrapper {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 400px;
        padding-top: 40px;
    }
    
    /* 오른쪽 컬럼 전체를 위로 올리기 */
    [data-testid="column"]:nth-child(2) {
        margin-top: -80px;
    }
    .section-title {
        text-align: center;
        font-size: 16px;
        font-weight: 600;
        color: #111827;
        margin-bottom: 30px;
        margin-top: 0;
    }
    
    /* 오른쪽 버튼 그룹 중앙 정렬 */
    .right-button-group {
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-height: 300px;
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
    
    /* 로그인 폼 컨테이너 - 너비 조정 */
    .login-form-container {
        max-width: 540px;
        margin: 0 auto;
        padding: 32px;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    .form-title {
        font-size: 22px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 6px;
    }
    .form-subtitle {
        font-size: 14px;
        color: #6b7280;
        margin-bottom: 24px;
    }
    
    /* 입력 필드 너비 조정 */
    .stTextInput > div > div > input {
        font-size: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

    # 역할 선택 상태 확인
    if "role_selection" not in st.session_state:
        st.session_state.role_selection = None

    if st.session_state.role_selection is None:
        render_role_selection()
    elif st.session_state.role_selection == "transferor":
        render_transferor_login()
    elif st.session_state.role_selection == "receiver":
        render_receiver_login()


def render_role_selection():
    """역할 선택 화면 - 좌우 분할 레이아웃"""
    
    # 구분선 추가
    st.markdown('<div class="divider-line"></div>', unsafe_allow_html=True)
    
    # 좌우 컬럼 생성
    col_left, col_right = st.columns([1, 1], gap="large")
    
    with col_left:
        st.markdown("""
        <div class="left-content">
            <div>
                <div class="login-title">BATON</div>
                <div class="login-subtitle">BATON과 함께 AI로 업무 인수인계하기</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_right:
        # 수직 여백 추가로 중앙 배치 효과
        st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)
        
        st.markdown('<div class="section-title">역할을 선택해주세요</div>', unsafe_allow_html=True)
        
        if st.button("인계자 로그인", key="btn_transferor", use_container_width=True):
            st.session_state.role_selection = "transferor"
            st.rerun()
        
        st.markdown("<div style='margin: 16px 0;'></div>", unsafe_allow_html=True)
        
        if st.button("인수자 로그인", key="btn_receiver", use_container_width=True):
            st.session_state.role_selection = "receiver"
            st.rerun()


def render_transferor_login():
    """인계자 로그인 화면"""
    # 구분선 추가
    st.markdown('<div class="divider-line"></div>', unsafe_allow_html=True)
    
    # 좌우 컬럼 생성
    col_left, col_right = st.columns([1, 1], gap="large")
    
    with col_left:
        st.markdown("""
        <div class="left-content">
            <div>
                <div class="login-title">BATON</div>
                <div class="login-subtitle">BATON과 함께 AI로 업무 인수인계하기</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_right:
        st.markdown('<div style="margin-top: -40px;">', unsafe_allow_html=True)
        
        st.markdown('<div class="form-title" style="text-align: center;">인계자 로그인</div>', unsafe_allow_html=True)
        st.markdown('<div class="form-subtitle" style="text-align: center;">업무를 인계할 인수자를 지정하고 파일을 업로드하세요</div>', unsafe_allow_html=True)

        with st.form("transferor_login_form"):
            transferor_id = st.text_input("인계자 사번", placeholder="예: 11830")
            receiver_id = st.text_input("인수자 사번", placeholder="예: 11832")

            st.markdown("<br>", unsafe_allow_html=True)
            
            col_a, col_b = st.columns([1, 1], gap="small")
            with col_a:
                submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")
            with col_b:
                back = st.form_submit_button("뒤로가기", use_container_width=True)

            if back:
                st.session_state.role_selection = None
                st.rerun()

            if submitted:
                if not transferor_id or not receiver_id:
                    st.error("모든 필드를 입력해주세요")
                elif transferor_id == receiver_id:
                    st.error("인계자와 인수자는 다른 사번이어야 합니다")
                else:
                    try:
                        session = auth_db.create_session(transferor_id, receiver_id)

                        st.session_state.logged_in = True
                        st.session_state.user_role = "transferor"
                        st.session_state.employee_id = transferor_id
                        st.session_state.session_id = session.session_id
                        st.session_state.receiver_id = receiver_id
                        st.session_state.nav = "파일 업로드"

                        st.rerun()
                    except Exception as e:
                        st.error(f"로그인 실패: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)


def render_receiver_login():
    """인수자 로그인 화면"""
    # 구분선 추가
    st.markdown('<div class="divider-line"></div>', unsafe_allow_html=True)
    
    # 좌우 컬럼 생성
    col_left, col_right = st.columns([1, 1], gap="large")
    
    with col_left:
        st.markdown("""
        <div class="left-content">
            <div>
                <div class="login-title">BATON</div>
                <div class="login-subtitle">BATON과 함께 AI로 업무 인수인계하기</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_right:
        st.markdown('<div style="margin-top: -40px;">', unsafe_allow_html=True)
        
        st.markdown('<div class="form-title" style="text-align: center;">인수자 로그인</div>', unsafe_allow_html=True)
        st.markdown('<div class="form-subtitle" style="text-align: center;">사번을 입력하여 인계받은 자료를 확인하세요</div>', unsafe_allow_html=True)

        with st.form("receiver_login_form"):
            receiver_id = st.text_input("인수자 사번", placeholder="예: 11832")

            st.markdown("<br>", unsafe_allow_html=True)
            
            col_a, col_b = st.columns([1, 1], gap="small")
            with col_a:
                submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")
            with col_b:
                back = st.form_submit_button("뒤로가기", use_container_width=True)

            if back:
                st.session_state.role_selection = None
                st.rerun()

            if submitted:
                if not receiver_id:
                    st.error("사번을 입력해주세요")
                else:
                    sessions = auth_db.get_sessions_by_receiver(receiver_id)

                    if not sessions:
                        st.error("해당 사번으로 지정된 인계 세션이 없습니다")
                    else:
                        session = sessions[0]

                        st.session_state.logged_in = True
                        st.session_state.user_role = "receiver"
                        st.session_state.employee_id = receiver_id
                        st.session_state.session_id = session.session_id
                        st.session_state.transferor_id = session.transferor_id
                        st.session_state.nav = "메인"

                        st.success(f"로그인 성공!\n\n인계자: {session.transferor_id}")
                        st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)