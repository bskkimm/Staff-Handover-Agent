# main.py
import runpy
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
OUT_MD = (BASE_DIR / "scheduling" / "output" / "combined_schedule.md").resolve()
KST = ZoneInfo("Asia/Seoul")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 환경변수 로드
load_dotenv(PROJECT_ROOT / ".env")

<<<<<<< HEAD
=======
SCHED_VIZ_DIR = (PROJECT_ROOT / "data" / "schedule" / "out_cal_bars").resolve()
>>>>>>> upstream/develop
SCHED_SCRIPT = (BASE_DIR / "scheduling" / "scheduling_main.py").resolve()


def run_scheduling_pipeline() -> None:
    """Execute the scheduling pipeline script in an isolated namespace."""
    sched_dir = SCHED_SCRIPT.parent
    if str(sched_dir) not in sys.path:
        sys.path.insert(0, str(sched_dir))
    runpy.run_path(str(SCHED_SCRIPT), run_name="__main__")


def _parse_schedule_dt(value: str, default_time: str) -> Optional[datetime]:
    """스케줄 문자열을 KST 기준 ISO 포맷으로 변환"""
    value = (value or "").replace("(KST)", "").strip()
    if not value:
        return None
    if len(value) == 10:
        value = f"{value} {default_time}"
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    return dt.replace(tzinfo=KST)


def load_schedule_events(md_path: Path) -> List[Dict[str, object]]:
    """마크다운 요약을 FullCalendar 이벤트 배열로 변환"""
    if not md_path.exists():
        return []
    from handover.scheduling.schedule_builder import parse_summary_blocks
    markdown = md_path.read_text(encoding="utf-8")
    items = parse_summary_blocks(markdown)
    events: List[Dict[str, object]] = []
    for item in items:
        start_dt = _parse_schedule_dt(item["start"], "00:00")
        end_dt = _parse_schedule_dt(item["deadline"], "18:00")
        if not start_dt:
            continue
        if not end_dt or end_dt < start_dt:
            end_dt = start_dt + timedelta(hours=1)
        if end_dt == start_dt:
            end_dt = start_dt + timedelta(hours=1)
        title = item["project"].strip()
        if item.get("owners"):
            title = f"{title} ({item['owners']})"
        events.append({
            "title": title,
            "start": start_dt.isoformat(timespec="minutes"),
            "end": end_dt.isoformat(timespec="minutes"),
            "extendedProps": {
                "source": item.get("source", ""),
            },
        })
    return events


# 초기 진입 시 타이틀·아이콘·레이아웃을 지정해 일관된 UX를 만든다.
st.set_page_config(page_title="BATON", page_icon="🏃‍♂️", layout="centered", initial_sidebar_state="collapsed")

# ================== Global Styles ==================
# Streamlit 기본 테마 대신 커스텀 CSS를 씌워 브랜딩한 UI를 적용한다.
st.markdown("""
<style>
/* 본문 폭 */
.main .block-container { max-width: 1100px; padding-top:.8rem; }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"]{
  background:#ffffff !important;
  box-shadow: 2px 0 8px rgba(128,128,128,0.05) !important;
  border:none !important;
}

[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] [data-testid="stVerticalBlock"],
[data-testid="stSidebar"] .streamlit-option-menu,
[data-testid="stSidebar"] .streamlit-option-menu > div,
[data-testid="stSidebar"] .nav,
[data-testid="stSidebar"] .nav-pills,
[data-testid="stSidebar"] .nav-item,
[data-testid="stSidebar"] .nav-link{
  background:#ffffff !important;
  box-shadow:none !important;
  border:none !important;
}

/* Sidebar 내부 제목 */
.sidebar-title {
  text-align:center; font-weight:700; font-size:26px; color:#1f2937;
  margin:10px 0 16px 0;
  padding-bottom:12px;
  position:relative;
}
.sidebar-title::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100px;
  height: 1px;
  background-color: #e5e7eb;
}

/* option_menu 기본 아이콘 색 */
.streamlit-option-menu .icon { color:#6b7280 !important; font-size:18px !important; }

/* 항목 사이 구분 바*/
.streamlit-option-menu .nav-item:not(:last-child) .nav-link{
  border-bottom:1px solid #e5e7eb !important;
  border-radius:8px !important;
}
.streamlit-option-menu .nav-item:last-child .nav-link{
  border-bottom:none !important;
}

/* 선택 항목: 배경 흰색, 텍스트/아이콘 빨강 */
.streamlit-option-menu .nav-link.active{
  background:#ffffff !important;
  color:#ef4444 !important;
  font-weight:600;
}
.streamlit-option-menu .nav-link.active .icon{
  color:#ef4444 !important;
}

/* 카드/텍스트 */
.card { border:1px solid #e5e7eb; background:#ffffff; border-radius:16px; padding:22px; box-shadow:0 1px 3px rgba(0,0,0,.06); }
.hint { color:#6b7280; font-size:14px; }

/* 메인 랜딩 */
.main-welcome { text-align:center; margin:10px auto 30px; max-width:600px; }
.main-title { font-size:42px; font-weight:800; color:#111827; margin-bottom:16px; line-height:1.2; }
.main-subtitle { font-size:18px; color:#6b7280; margin-bottom:40px; line-height:1.5; }
.feature-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(200px,1fr)); gap:24px; margin-top:20px; }
.feature-card { text-align:center; padding:32px 20px; border:1px solid #e5e7eb; border-radius:16px; background:#ffffff; transition:.2s; }
.feature-card:hover { border-color:#c7d2fe; box-shadow:0 4px 12px rgba(0,0,0,.08); transform:translateY(-2px); }
.feature-icon { font-size:32px; margin-bottom:16px; }
.feature-title { font-size:16px; font-weight:600; color:#111827; margin-bottom:8px; }
.feature-desc { font-size:14px; color:#6b7280; line-height:1.4; }
</style>
""", unsafe_allow_html=True)

# ================== Session ==================
if "nav" not in st.session_state:
    st.session_state.nav = "메인"

# ================== File Upload Status Check ==================
def check_uploaded_files():
    """DB에서 업로드된 파일이 있는지 확인"""
    try:
        from file_upload.database import file_db
        files = file_db.get_all_files()
        return len(files) > 0
    except Exception:
        return False

def get_uploaded_files_count():
    """업로드된 파일 개수 반환"""
    try:
        from file_upload.database import file_db
        files = file_db.get_all_files()
        return len(files)
    except Exception:
        return 0

# ================== Sidebar (option_menu) ==================
is_uploaded = check_uploaded_files()

# 파일 업로드 상태에 따라 메뉴 동적 구성
if is_uploaded:
    pages = ["메인", "파일 업로드", "인수인계 자료 추출", "Q&A", "스케줄 확인"]
    icons = ['house', 'cloud-upload', 'file-earmark-text', 'chat-dots', 'calendar3']
else:
    pages = ["메인", "파일 업로드"]
    icons = ['house', 'cloud-upload']

with st.sidebar:
    # 사이드바 헤더와 내비 구성을 원하는 스타일로 정렬한다.
    st.markdown('<div class="sidebar-title">BATON</div>', unsafe_allow_html=True)

    # 현재 선택된 페이지가 available pages에 없으면 메인으로 리셋
    if st.session_state.nav not in pages:
        st.session_state.nav = "메인"

    try:
        current_index = pages.index(st.session_state.nav)
    except ValueError:
        current_index = 0
        st.session_state.nav = "메인"

    choice = option_menu(
        None, pages, icons=icons, menu_icon=None, default_index=current_index,
        styles={
            # 옵션 메뉴 컨테이너/아이콘/링크 색상 등을 세밀하게 지정한다.
            "container": {"padding":"0px","background-color":"#ffffff","border":"none","box-shadow":"none"},
            "icon": {"color":"#6b7280","font-size":"18px"},
            "nav-link": {"font-size":"15px","text-align":"left","margin":"4px 0","padding":"12px 16px",
                         "border-radius":"8px","color":"#374151","background-color":"#ffffff","--hover-color":"#f8fafc"},
            "nav-link-selected": {"background-color":"#ffffff","color":"#ef4444","font-weight":"600"},
        }
    )

    if choice != st.session_state.nav:
        st.session_state.nav = choice
        st.rerun()

    # 파일이 업로드되지 않았을 때 안내 메시지 표시
    if not is_uploaded:
        st.markdown(
            '<div style="color:#6b7280;font-size:12px;text-align:center;margin:16px 8px 0;">'
            '⚠ 파일을 업로드하면 추가 메뉴를 사용할 수 있습니다.'
            '</div>', unsafe_allow_html=True
        )

# ================== Pages ==================
def page_main():
    # 랜딩 히어로 영역과 기능 소개 카드를 HTML/CSS로 직접 그린다.
    st.markdown("""
    <div class="main-welcome">
      <div class="main-title">BATON으로<br>완벽한 인수인계를 시작하세요</div>
      <div class="main-subtitle">파일을 업로드하면 AI가 자동으로 인수인계 자료를 정리하고,<br>궁금한 점은 언제든 질문할 수 있습니다.</div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if st.button("파일 업로드하고 시작하기", use_container_width=True, type="primary"):
            st.session_state.nav = "파일 업로드"
            st.rerun()
    st.markdown("""
    <div class="feature-grid">
      <div class="feature-card">
        <div class="feature-icon">📝</div>
        <div class="feature-title">자료 정리</div>
        <div class="feature-desc">업로드한 파일들을 분석해서<br>체계적인 레포트로 정리</div>
      </div>
      <div class="feature-card">
        <div class="feature-icon">💬</div>
        <div class="feature-title">AI Q&A</div>
        <div class="feature-desc">인수인계 담당자 페르소나로<br>궁금한 점을 언제든 질문</div>
      </div>
      <div class="feature-card">
        <div class="feature-icon">📅</div>
        <div class="feature-title">스케줄 시각화</div>
        <div class="feature-desc">중요한 일정과 마일스톤을<br>한눈에 보기 쉽게 정리</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def page_upload():
    """파일 업로드 페이지"""
    try:
        from file_upload.upload_page import run_upload
        run_upload()
    except Exception as e:
        st.error(f"파일 업로드 중 오류가 발생했습니다: {e}")

def page_report():
    st.markdown("#### 인수인계 자료 추출")
    st.caption("버튼을 누르면 현재 전처리된 데이터로 인수인계 요약 레포트를 생성하고 화면에 표시합니다.")

    from summary_report.report_service import generate_and_save_report

    if st.button("인수인계 자료 확인하기", use_container_width=True, type="primary"):
            with st.spinner("요약 레포트를 생성 중입니다..."):
                md, out_path = generate_and_save_report("test_report.md")
                if md:
                    st.markdown(md)
                else:
                    st.error("레포트 생성에 실패했습니다. 환경변수 및 네트워크를 확인하세요.")

def page_qa():
    try:
        from chatbot.chatbot_page import run_chat
        run_chat()  
    except ImportError as e:
        st.error(f"챗봇 모듈을 불러올 수 없습니다: {e}")
        st.info("chatbot.py 파일이 같은 폴더에 있는지 확인해주세요.")
    except Exception as e:
        st.error(f"챗봇 실행 중 오류가 발생했습니다: {e}")


def page_calendar():
    # streamlit-calendar 컴포넌트를 사용해 인터랙티브 달력을 노출한다.
    # st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 스케줄 확인")

    if "schedule_events" not in st.session_state:
        st.session_state.schedule_events = []

    if st.button("스케줄 추출하기", use_container_width=True, type="primary"):
        with st.spinner("스케줄을 추출 중입니다..."):
            try:
                run_scheduling_pipeline()
                events = load_schedule_events(OUT_MD)
                st.session_state.schedule_events = events
                if events:
                    st.success("스케줄 추출을 완료했습니다.")
                else:
                    st.warning("추출된 일정이 없습니다. 입력 데이터를 확인해주세요.")
            except Exception as exc:
                st.session_state.schedule_events = []
                st.error(f"스케줄 추출 중 오류가 발생했습니다: {exc}")

    events = st.session_state.get("schedule_events", [])
    if events:
        st.markdown("##### 인수인계 업무 달력")
        calendar(
            events=events,
            options={
                "initialView": "dayGridMonth",
                "height": "auto",
                "locale": "en",
                "buttonText": {
                    "today": "오늘",
                    "month": "월",
                    "week": "주",
                    "list": "목록",
                },
                "headerToolbar": {
                    "left": "prev,next today",
                    "center": "title",
                    "right": "dayGridMonth,timeGridWeek,listWeek",
                },
                "displayEventTime": False,
            },
            key="handover_calendar",
        )
    else:
        st.info("생성된 일정이 없습니다. 버튼을 눌러 스케줄을 추출하세요.")

    # st.markdown('</div>', unsafe_allow_html=True)

# ================== Router ==================
if st.session_state.nav == "메인":
    page_main()
elif st.session_state.nav == "파일 업로드":
    page_upload()
elif st.session_state.nav == "인수인계 자료 추출":
    page_report()
elif st.session_state.nav == "Q&A":
    page_qa()
elif st.session_state.nav == "스케줄 확인":
    page_calendar()
