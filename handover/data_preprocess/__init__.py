"""
데이터 전처리 패키지

이 패키지는 이메일, 회의록, 개인기록 등의 텍스트 파일을 파싱하고 구조화된 데이터로 변환하는 기능을 제공합니다.

주요 모듈:
- file_utils: 파일 읽기/쓰기 유틸리티
- type_detector: 파일 타입 감지
- email_parser: 이메일 파싱
- meeting_parser: 회의록 파싱
- personal_parser: 개인기록 파싱
- main_processor: 통합 처리기
"""

from .main_processor import process_all_files, process_directory, process_and_export_json
from .file_utils import read_txt_file, read_multiple_txt_files, convert_to_json
from .type_detector import detect_file_type, FileType
from .email_parser import parse_email, Email
from .meeting_parser import parse_meeting_minutes, MeetingMinutes
from .personal_parser import parse_personal_note, PersonalNote
from .upload_processor import process_uploaded_files, process_with_auto_filename, get_next_file_number

__all__ = [
    'process_all_files',
    'process_directory', 
    'process_and_export_json',
    'read_txt_file',
    'read_multiple_txt_files',
    'convert_to_json',
    'detect_file_type',
    'FileType',
    'parse_email',
    'Email',
    'parse_meeting_minutes',
    'MeetingMinutes',
    'parse_personal_note',
    'PersonalNote',
    # 업로드 파일 처리
    'process_uploaded_files',
    'process_with_auto_filename',
    'get_next_file_number'
]
