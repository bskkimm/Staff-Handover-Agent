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

def check_preprocessing_status():
    """전처리된 데이터가 있는지 확인"""
    try:
        import os
        from pathlib import Path
        
        # Staff-Handover-Agent 실행 위치 기준으로 경로 설정
        current_dir = Path(__file__).parent.parent.parent  # handover/file_upload -> handover -> Staff-Handover-Agent
        preprocessed_dir = current_dir / "data" / "preprocessed_data"
        
        if preprocessed_dir.exists():
            json_files = list(preprocessed_dir.glob("*.txt"))
            return len(json_files) > 0
        return False
    except Exception:
        return False

def run_data_preprocessing():
    """업로드된 파일들을 전처리하여 구조화된 데이터로 변환"""
    try:
        from data_preprocess import process_with_auto_filename
        
        # 진행 상태 표시
        with st.spinner("📊 파일을 분석하고 구조화된 데이터로 변환 중..."):
            # 전처리 실행
            result = process_with_auto_filename()
            
            if result['success']:
                st.success(f"✅ 전처리 완료! {result['processed_files']}개 파일이 처리되었습니다.")
                st.info(f"📁 출력 파일: {result['output_file']}")
                
                # 처리된 파일 목록 표시
                if result.get('files_processed'):
                    st.markdown("**처리된 파일들:**")
                    for file_name in result['files_processed']:
                        st.markdown(f"- {file_name}")
                
                return True
            else:
                st.error(f"❌ 전처리 실패: {result['message']}")
                return False
                
    except ImportError as e:
        st.error(f"❌ 전처리 모듈을 불러올 수 없습니다: {e}")
        st.info("data_preprocess 패키지가 올바르게 설치되어 있는지 확인해주세요.")
        return False
    except Exception as e:
        st.error(f"❌ 전처리 중 오류가 발생했습니다: {e}")
        return False

def run_upload():
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
            handle_upload(files)
        else:
            st.warning("추가할 파일을 먼저 선택해 주세요.")

    st.divider()
    render_file_list()
    st.markdown('</div>', unsafe_allow_html=True)

def handle_upload(files):
    """파일 업로드 처리"""
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
            
            # 파일 저장 시도
            result = file_db.save_file(file_buffer, file.name)
            
            if result:
                added += 1
            else:
                duplicates += 1
                
        except Exception as e:
            errors.append(f"{file.name}: {str(e)}")
    
    # 결과 메시지 표시
    if added > 0:
        st.success(f"{added}개 파일을 성공적으로 업로드했어요.")
    if duplicates > 0:
        st.info(f"{duplicates}개 파일은 이미 업로드되어 있어서 건너뛰었어요.")
    if errors:
        for error in errors:
            st.error(error)
    
    # 파일이 추가되었으면 자동 전처리 실행 및 페이지 새로고침
    if added > 0:
        # 자동 전처리 실행
        run_data_preprocessing()
        st.rerun()

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

def render_file_list():
    """파일 목록 렌더링"""
    st.markdown("##### 업로드 목록")
    
    try:
        files = file_db.get_all_files()
        
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
        
        # 전처리 상태 확인 및 실행 버튼
        st.divider()
        st.markdown("##### 📊 데이터 전처리")
        
        # 전처리 상태 확인
        is_preprocessed = check_preprocessing_status()
        
        if is_preprocessed:
            st.success("✅ 전처리가 완료되었습니다. 인수인계 자료를 확인할 수 있습니다.")
        else:
            st.info("📝 업로드된 파일을 전처리하여 구조화된 데이터로 변환하세요.")
            
            if st.button("🔄 전처리 실행", use_container_width=True, type="secondary"):
                # 전처리 실행
                preprocessing_success = run_data_preprocessing()
                
                if preprocessing_success:
                    st.rerun()  # 페이지 새로고침하여 상태 업데이트
        
        # 다른 기능 활성화 안내
        st.info("왼쪽 메뉴의 기능들이 활성화되었습니다. 원하는 기능으로 이동하세요. ✅")
        
    except Exception as e:
        st.error(f"파일 목록을 불러오는 중 오류가 발생했습니다: {str(e)}")
