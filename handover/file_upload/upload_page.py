# file_upload/upload_page.py
import streamlit as st
from file_upload.database import file_db
from pathlib import Path
import shutil

def human_size(bytes_size: int) -> str:
    """파일 크기를 사람이 읽기 쉬운 형태로 변환"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:3.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}PB"

def check_preprocessing_status(session_id: str = None):
    """전처리된 데이터가 있는지 확인"""
    try:
        import os
        from pathlib import Path

        # Staff-Handover-Agent 실행 위치 기준으로 경로 설정
        current_dir = Path(__file__).parent.parent.parent  # handover/file_upload -> handover -> Staff-Handover-Agent

        # 세션별 전처리 디렉토리
        if session_id:
            preprocessed_dir = current_dir / "data" / "preprocessed_data" / session_id
        else:
            preprocessed_dir = current_dir / "data" / "preprocessed_data"

        if preprocessed_dir.exists():
            json_files = list(preprocessed_dir.glob("*.txt"))
            return len(json_files) > 0
        return False
    except Exception:
        return False

def run_data_preprocessing(session_id: str = None):
    """업로드된 파일들을 전처리하여 구조화된 데이터로 변환"""
    try:
        from data_preprocess import process_with_auto_filename

        # 전처리 실행 (세션 ID 전달)
        result = process_with_auto_filename(session_id)

        if result['success']:
            return True
        else:
            return False

    except ImportError as e:
        return False
    except Exception as e:
        return False

def run_upload(session_id: str = None):
    # 페이지 제목 추가
    st.markdown('<style>h4 { margin-top: -45px !important; font-weight: 600 !important; }</style>', unsafe_allow_html=True)
    # 업로드 화면의 타이틀과 설명을 노출해 사용자 흐름을 잡는다.
    st.markdown("#### 파일 업로드")
    st.caption("지원 형식: PDF, TXT, DOCX, CSV — 여러 파일을 한 번에 올릴 수 있어요.")

    # 파일 업로더
    # 대용량 업로드 UX를 위해 멀티 업로드 위젯과 안내 문구를 설정한다.
    files = st.file_uploader(
        "여기에 파일을 드래그하거나 클릭해서 선택하세요.",
        type=["pdf", "txt", "docx", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    # 버튼들
    # 업로드/삭제 버튼을 나란히 배치해 조작 흐름을 단순화한다.
    col1, col2 = st.columns([1, 1])
    
    # 파일 선택 여부 확인을 위한 변수
    upload_clicked = False
    
    with col1:
        if st.button("업로드 추가", use_container_width=True, type="primary"):
            upload_clicked = True
    
    with col2:
        if st.button("전체 삭제", use_container_width=True):
            handle_delete_all()
    # 업로드 처리 및 메시지 표시 (컬럼 밖에서)
    if upload_clicked:
        if files:
            with st.spinner("파일 업로드 중..."):
                handle_upload(files)
        else:
            st.warning("추가할 파일을 먼저 선택해 주세요.")

    st.divider()
    render_file_list(session_id)
    st.markdown('</div>', unsafe_allow_html=True)

def handle_upload(files):
    """파일 업로드 처리"""
    import streamlit as st

    # 세션 ID 가져오기
    session_id = st.session_state.get("session_id")

    added = 0
    duplicates = 0
    errors = []

    for file in files:
        try:
            file_buffer = file.getvalue()

            # 파일 크기 검증 (10MB 제한)
            if len(file_buffer) > 10 * 1024 * 1024:
                errors.append(f"{file.name}: 파일 크기가 10MB를 초과합니다")
                continue

            # 파일 저장 시도 (session_id 포함)
            result = file_db.save_file(file_buffer, file.name, session_id)

            if result:
                added += 1
            else:
                duplicates += 1
                
        except Exception as e:
            errors.append(f"{file.name}: {str(e)}")
    
    # 파일이 추가되었으면 자동 전처리 실행
    if added > 0:
        # 자동 전처리 실행 (세션 ID 전달)
        preprocessing_success = run_data_preprocessing(session_id)

        if preprocessing_success:
            # 전처리 성공 시 조용히 처리 (사용자에게 메시지 표시하지 않음)
            pass
        else:
            st.error("파일 업로드는 완료되었지만 전처리 중 오류가 발생했습니다.")
        
        # 파일 업로드 후 페이지 새로고침하여 메뉴 상태 업데이트
        st.rerun()
    elif duplicates > 0:
        st.info(f"{duplicates}개 파일은 이미 업로드되어 있어서 건너뛰었어요.")
    
    if errors:
        for error in errors:
            st.error(error)

def handle_delete_all():
    """전체 파일 삭제 처리"""
    try:
        # 1) 업로드된 파일 + 메타레코드 삭제 (DB 기준)
        deleted_count = file_db.delete_all_files()

        # 2) 아티팩트 디렉토리/파일 정리 (업로드 폴더, 전처리 결과, RAG 스토어, 메타 DB)
        project_root = Path(__file__).parent.parent.parent  # .../Staff-Handover-Agent
        uploads_dir = project_root / "data" / "uploads"
        preprocessed_dir = project_root / "data" / "preprocessed_data"
        rag_store_dir = project_root / "data" / "rag_store"
        db_file = project_root / "data" / "file_metadata.db"

        # Helper: remove all contents of a directory (but keep the dir)
        def _empty_dir(path: Path):
            if path.exists() and path.is_dir():
                for child in path.iterdir():
                    if child.is_file() or child.is_symlink():
                        try:
                            child.unlink()
                        except Exception:
                            pass
                    elif child.is_dir():
                        try:
                            shutil.rmtree(child, ignore_errors=True)
                        except Exception:
                            pass
            else:
                path.mkdir(parents=True, exist_ok=True)

        # Empty uploads directory regardless of DB state
        _empty_dir(uploads_dir)

        # Remove entire preprocessed and rag store directories
        if preprocessed_dir.exists():
            shutil.rmtree(preprocessed_dir, ignore_errors=True)
        if rag_store_dir.exists():
            shutil.rmtree(rag_store_dir, ignore_errors=True)

        # Delete metadata DB file
        if db_file.exists():
            try:
                db_file.unlink()
            except Exception:
                pass

        # Feedback
        msg_parts = [f"업로드 {deleted_count}개 삭제"]
        if preprocessed_dir.exists():
            pass
        if rag_store_dir.exists():
            pass
        st.success("전체 삭제가 완료되었습니다. (업로드, 전처리 결과, 임베딩, 메타데이터)")
        st.rerun()
    except Exception as e:
        st.error(f"파일 삭제 중 오류가 발생했습니다: {str(e)}")

def render_file_list(session_id: str = None):
    """파일 목록 렌더링"""
    st.markdown("##### 업로드 목록")

    # 세션 ID가 파라미터로 전달되지 않으면 session_state에서 가져오기
    if not session_id:
        session_id = st.session_state.get("session_id")

    try:
        files = file_db.get_all_files(session_id)
        
        if not files:
            st.markdown('<p class="hint">아직 업로드된 파일이 없습니다.</p>', unsafe_allow_html=True)
            return
        
        # 파일 목록을 테이블 형태로 표시
        for file_record in files:
            col1, col2 = st.columns([9, 1])
            
            with col1:
                # 파일 정보 표시
                st.markdown(
                    f"**{file_record.original_name}** "
                    f"({file_record.file_type.upper()}) - "
                    f"{human_size(file_record.file_size)} - "
                    f"{file_record.upload_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            
            with col2:
                # 개별 파일 삭제 버튼
                if st.button(":material/delete:", key=f"delete_{file_record.id}", type="secondary", help="파일 삭제"):
                    try:
                        if file_db.delete_file(file_record.id):
                            st.success(f"'{file_record.original_name}' 파일을 삭제했어요.")
                            st.rerun()
                        else:
                            st.error("파일 삭제에 실패했습니다.")
                    except Exception as e:
                        st.error(f"파일 삭제 중 오류가 발생했습니다: {str(e)}")
        
        # 파일이 업로드되어 있으면 기능 활성화 안내
        st.divider()
        st.info("인수자를 위한 파일 업로드가 완료되었습니다. ✅")
        
    except Exception as e:
        # 오류 발생 시에도 기본 안내 메시지 표시
        st.info("왼쪽 메뉴의 기능들이 활성화되었습니다. 원하는 기능으로 이동하세요. ✅")
