# utils.py - 통합된 BATON 앱을 위한 유틸리티 함수들
import os
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def get_uploaded_files_data() -> Dict[str, str]:
    """업로드된 파일들의 내용을 읽어서 반환"""
    try:
        from file_upload.database import file_db
        files = file_db.get_all_files()
        
        st.info(f"📁 데이터베이스에서 {len(files)}개 파일을 찾았습니다.")
        
        files_data = {}
        for i, file_record in enumerate(files, 1):
            st.info(f"📄 [{i}/{len(files)}] 파일 처리 중: {file_record.original_name}")
            st.info(f"🔍 파일 정보 - ID: {file_record.id}, 타입: {file_record.file_type}, 크기: {file_record.file_size} bytes")
            
            # 파일 내용 읽기 - file_path 속성 사용 (절대 경로)
            file_path = file_record.file_path
            st.info(f"📂 파일 경로: {file_path}")
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        files_data[file_record.original_name] = content
                        st.success(f"✅ {file_record.original_name} 읽기 완료 ({len(content)} 문자)")
                except Exception as e:
                    st.error(f"❌ 파일 읽기 실패: {e}")
            else:
                st.warning(f"⚠️ 파일을 찾을 수 없습니다: {file_path}")
        
        st.success(f"📊 총 {len(files_data)}개 파일의 내용을 읽었습니다.")
        return files_data
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"파일 데이터 읽기 오류: {e}")
        st.error(f"상세 오류: {error_details}")
        return {}

def create_temp_txt_files(files_data: Dict[str, str]) -> str:
    """임시 디렉토리에 txt 파일들을 생성하고 경로 반환"""
    temp_dir = tempfile.mkdtemp()
    
    for filename, content in files_data.items():
        # 파일명에서 확장자 제거하고 .txt 추가
        base_name = Path(filename).stem
        txt_filename = f"{base_name}.txt"
        txt_path = os.path.join(temp_dir, txt_filename)
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return temp_dir

def cleanup_temp_dir(temp_dir: str):
    """임시 디렉토리 정리"""
    try:
        import shutil
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"임시 디렉토리 정리 오류: {e}")

def save_processing_results(results: Dict[str, Any], output_dir: str = "output"):
    """처리 결과를 파일로 저장"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON 결과 저장
    json_path = os.path.join(output_dir, f"processing_results_{timestamp}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    return json_path

def load_processing_results(json_path: str) -> Dict[str, Any]:
    """저장된 처리 결과 로드"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"결과 로드 오류: {e}")
        return {}

def check_azure_openai_config() -> bool:
    """Azure OpenAI 설정 확인"""
    # .env 파일 다시 로드
    load_dotenv(override=True)
    
    required_vars = [
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_API_VERSION'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.strip() == '' or value == 'your_api_key_here':
            missing_vars.append(var)
    
    if missing_vars:
        st.error(f"다음 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        st.info("💡 .env 파일을 확인하고 올바른 Azure OpenAI 설정을 입력해주세요.")
        return False
    
    return True

def get_file_type_icon(file_type: str) -> str:
    """파일 타입에 따른 아이콘 반환"""
    icons = {
        'email': '📧',
        'meeting': '🤝',
        'personal': '📝',
        'unknown': '📄'
    }
    return icons.get(file_type, '📄')

def format_file_size(size_bytes: int) -> str:
    """파일 크기를 사람이 읽기 쉬운 형태로 변환"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"
