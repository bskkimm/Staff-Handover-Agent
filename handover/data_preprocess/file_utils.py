"""
파일 처리 관련 공통 유틸리티 함수들
"""
import os
import json
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime


def read_txt_file(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
    """
    단일 텍스트 파일을 읽어서 내용을 반환
    
    Args:
        file_path: 파일 경로
        encoding: 파일 인코딩 (기본값: utf-8)
    
    Returns:
        파일 내용 문자열 또는 None (오류 시)
    """
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            content = file.read()
            return content
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return None
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
        return None


def read_multiple_txt_files(directory_path: str, file_pattern: str = "*.txt") -> Dict[str, str]:
    """
    디렉토리에서 여러 텍스트 파일을 읽어서 딕셔너리로 반환
    
    Args:
        directory_path: 디렉토리 경로
        file_pattern: 파일 패턴 (기본값: "*.txt")
    
    Returns:
        Dict[str, str]: {파일명: 파일내용} 형태의 딕셔너리
    """
    files_content = {}
    path = Path(directory_path)
    
    if not path.exists():
        print(f"디렉토리가 존재하지 않습니다: {directory_path}")
        return files_content
    
    for file_path in path.glob(file_pattern):
        if file_path.is_file():
            content = read_txt_file(str(file_path))
            if content is not None:
                files_content[file_path.name] = content
                print(f"✓ 파일 로드 완료: {file_path.name}")
    
    print(f"총 {len(files_content)}개 파일 로드 완료")
    return files_content


def convert_to_json(data: dict, output_file: str = None) -> str:
    """
    데이터를 JSON 문자열로 변환
    
    Args:
        data: 변환할 데이터
        output_file: 출력 파일 경로 (선택사항)
    
    Returns:
        JSON 문자열
    """
    def custom_serializer(obj):
        # Email 객체처럼 dict로 변환 가능한 것은 __dict__ 사용
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        # datetime → ISO 포맷 문자열
        if isinstance(obj, datetime):
            return obj.isoformat()
        # 그 외는 문자열로
        return str(obj)
    
    json_str = json.dumps(data, ensure_ascii=False, indent=2, default=custom_serializer)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"JSON 파일 저장 완료: {output_file}")
    
    return json_str
