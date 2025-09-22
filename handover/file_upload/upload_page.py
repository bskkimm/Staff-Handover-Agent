# file_upload/upload_page.py
import streamlit as st
from file_upload.database import file_db

def human_size(bytes_size: int) -> str:
    """파일 크기를 사람이 읽기 쉬운 형태로 변환"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:3.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}PB"

def run_upload():
    """파일 업로드 페이지 실행"""
    st.markdown("#### 파일 업로드")
    st.caption("지원 형식: PDF, TXT, DOCX, CSV — 여러 파일을 한 번에 올릴 수 있어요.")

    # 파일 업로더
    files = st.file_uploader(
        "여기에 파일을 드래그하거나 클릭해서 선택하세요.",
        type=["pdf", "txt", "docx", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    # 버튼들
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
    
    # 파일이 추가되었으면 페이지 새로고침
    if added > 0:
        st.rerun()

def handle_delete_all():
    """전체 파일 삭제 처리"""
    try:
        deleted_count = file_db.delete_all_files()
        if deleted_count > 0:
            st.success(f"{deleted_count}개 파일을 모두 삭제했어요.")
            st.rerun()
        else:
            st.info("삭제할 파일이 없습니다.")
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
                # 개별 파일 삭제 버튼 (최소 너비)
                if st.button(":material/delete:", key=f"delete_{file_record.id}", type="secondary", help="파일 삭제"):
                    try:
                        if file_db.delete_file(file_record.id):
                            st.success(f"'{file_record.original_name}' 파일을 삭제했어요.")
                            st.rerun()
                        else:
                            st.error("파일 삭제에 실패했습니다.")
                    except Exception as e:
                        st.error(f"파일 삭제 중 오류가 발생했습니다: {str(e)}")
        
        # 다른 기능 활성화 안내
        st.info("왼쪽 메뉴의 기능들이 활성화되었습니다. 원하는 기능으로 이동하세요. ✅")
        
    except Exception as e:
        st.error(f"파일 목록을 불러오는 중 오류가 발생했습니다: {str(e)}")