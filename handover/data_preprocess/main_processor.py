"""
메인 데이터 처리 모듈
모든 파서를 통합하여 파일들을 처리하는 메인 프로세서
"""
from typing import Dict, List
from .file_utils import read_multiple_txt_files, convert_to_json
from .type_detector import detect_file_type, FileType
from .email_parser import parse_email
from .meeting_parser import parse_meeting_minutes
from .personal_parser import parse_personal_note


def process_all_files(files_dict: Dict[str, str]) -> Dict[str, List]:
    """
    모든 파일을 타입별로 분류하고 파싱
    
    Args:
        files_dict: {파일명: 내용} 형태의 딕셔너리
    
    Returns:
        Dict[str, List]: 타입별로 분류된 파싱 결과
        {
            'emails': [이메일 객체들],
            'meetings': [회의록 딕셔너리들],
            'personal_notes': [개인기록 딕셔너리들]
        }
    """
    print(f"🔍 {len(files_dict)}개 파일 처리 시작")
    
    result = {
        'emails': [],
        'meetings': [],
        'personal_notes': []
    }
    
    for filename, content in files_dict.items():
        try:
            print(f"📄 파일 처리 중: {filename}")
            print(f"📏 내용 길이: {len(content)} 문자")
            
            # 1. 각 파일의 타입 감지
            file_type = detect_file_type(content)
            print(f"🏷️ 감지된 타입: {file_type}")
            
            # 2. 타입에 맞는 파서 실행
            if file_type == FileType.EMAIL:
                parsed = parse_email(content)
                result['emails'].extend(parsed)
                print(f"📧 이메일 {len(parsed)}개 파싱 완료")
                
            elif file_type == FileType.MEETING:
                parsed = parse_meeting_minutes(content)
                if parsed:
                    result['meetings'].append(parsed)
                    print(f"🤝 회의록 1개 파싱 완료")
                
            elif file_type == FileType.PERSONAL:
                parsed = parse_personal_note(content, filename)
                if parsed:
                    result['personal_notes'].append(parsed)
                    print(f"📝 개인노트 1개 파싱 완료")
            else:
                print(f"❓ 알 수 없는 타입: {file_type}")
                
        except Exception as e:
            print(f"❌ 파일 처리 오류 ({filename}): {e}")
            import traceback
            traceback.print_exc()
    
    print(f"✅ 처리 완료 - 이메일: {len(result['emails'])}, 회의록: {len(result['meetings'])}, 개인노트: {len(result['personal_notes'])}")
    return result


def process_directory(directory_path: str, file_pattern: str = "*.txt") -> Dict[str, List]:
    """
    디렉토리에서 파일들을 읽어서 처리
    
    Args:
        directory_path: 디렉토리 경로
        file_pattern: 파일 패턴 (기본값: "*.txt")
    
    Returns:
        Dict[str, List]: 타입별로 분류된 파싱 결과
    """
    # 파일들 읽기
    files_dict = read_multiple_txt_files(directory_path, file_pattern)
    
    if not files_dict:
        print("❌ 처리할 파일이 없습니다.")
        return {'emails': [], 'meetings': [], 'personal_notes': []}
    
    # 파일들 처리
    return process_all_files(files_dict)


def process_and_export_json(directory_path: str, output_file: str = None, file_pattern: str = "*.txt") -> str:
    """
    디렉토리의 파일들을 처리하고 JSON으로 변환
    
    Args:
        directory_path: 디렉토리 경로
        output_file: 출력 파일 경로 (선택사항)
        file_pattern: 파일 패턴 (기본값: "*.txt")
    
    Returns:
        str: JSON 문자열
    """
    # 파일들 처리
    result = process_directory(directory_path, file_pattern)
    
    # JSON으로 변환
    json_output = convert_to_json(result, output_file)
    
    return json_output
