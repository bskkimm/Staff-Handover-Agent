"""
업로드된 파일 처리기
업로드 디렉토리의 파일들을 처리하여 JSON으로 저장
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional

from .main_processor import process_and_export_json


def process_uploaded_files(output_filename: str = "No_1.json") -> Dict:
    """
    업로드된 파일들을 처리하여 JSON으로 저장
    
    Args:
        output_filename: 출력 파일명 (기본값: "No_1.json")
    
    Returns:
        Dict: 처리 결과
    """
    # Staff-Handover-Agent 실행 위치 기준으로 경로 설정
    # __file__: Staff-Handover-Agent/handover/data_preprocess/upload_processor.py
    # 실행 위치: Staff-Handover-Agent
    current_dir = Path(__file__).parent.parent.parent  # handover/data_preprocess -> handover -> Staff-Handover-Agent
    uploads_dir = current_dir / "data" / "uploads"
    output_dir = current_dir / "data" / "preprocessed_data"
    
    # 디렉토리 생성 (존재하지 않는 경우)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 업로드 디렉토리: {uploads_dir}")
    print(f"📁 출력 디렉토리: {output_dir}")
    print(f"📁 업로드 디렉토리 존재 여부: {uploads_dir.exists()}")
    print(f"📁 업로드 디렉토리 절대 경로: {uploads_dir.absolute()}")
    
    # 업로드된 txt 파일들 확인
    txt_files = list(uploads_dir.glob("*.txt"))
    print(f"📄 발견된 txt 파일 수: {len(txt_files)}")
    for file_path in txt_files:
        print(f"  - {file_path.name}")
    
    if not txt_files:
        print("❌ 처리할 txt 파일이 없습니다.")
        return {
            'success': False,
            'message': '처리할 txt 파일이 없습니다.',
            'processed_files': 0,
            'output_file': None
        }
    
    print(f"📄 발견된 파일: {len(txt_files)}개")
    for file_path in txt_files:
        print(f"  - {file_path.name}")
    
    try:
        # 파일들 처리
        print("🔄 파일 처리 시작...")
        json_output = process_and_export_json(str(uploads_dir))
        
        # 출력 파일 경로
        output_path = output_dir / output_filename
        
        # JSON 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_output)
        
        print(f"✅ 처리 완료: {output_path}")
        
        return {
            'success': True,
            'message': f'파일 처리가 완료되었습니다. ({output_filename})',
            'processed_files': len(txt_files),
            'output_file': str(output_path),
            'files_processed': [f.name for f in txt_files]
        }
        
    except Exception as e:
        print(f"❌ 파일 처리 중 오류 발생: {e}")
        return {
            'success': False,
            'message': f'파일 처리 중 오류가 발생했습니다: {str(e)}',
            'processed_files': 0,
            'output_file': None
        }


def get_next_file_number() -> int:
    """다음 파일 번호를 가져옵니다 (No_1.json, No_2.json, ...)"""
    # Staff-Handover-Agent 실행 위치 기준으로 경로 설정
    current_dir = Path(__file__).parent.parent.parent  # handover/data_preprocess -> handover -> Staff-Handover-Agent
    output_dir = current_dir / "data" / "preprocessed_data"
    
    existing_files = list(output_dir.glob("No_*.json"))
    if not existing_files:
        return 1
    
    # 파일명에서 번호 추출
    numbers = []
    for file_path in existing_files:
        try:
            # "No_1.json" -> "1"
            number_str = file_path.stem.split("_")[1]
            numbers.append(int(number_str))
        except (IndexError, ValueError):
            continue
    
    return max(numbers) + 1 if numbers else 1


def process_with_auto_filename() -> Dict:
    """자동으로 파일 번호를 생성하여 처리"""
    file_number = get_next_file_number()
    output_filename = f"No_{file_number}.json"
    return process_uploaded_files(output_filename)


if __name__ == "__main__":
    # 테스트 실행
    print("🚀 업로드 파일 처리 테스트")
    
    # 자동 파일명으로 처리
    result = process_with_auto_filename()
    
    print("\n📊 처리 결과:")
    print(f"성공: {result['success']}")
    print(f"메시지: {result['message']}")
    print(f"처리된 파일 수: {result['processed_files']}")
    print(f"출력 파일: {result['output_file']}")
    
    if result['success']:
        print(f"처리된 파일들: {result['files_processed']}")
