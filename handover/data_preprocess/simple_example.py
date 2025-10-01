"""
간단한 사용 예제
업로드된 파일들을 처리하여 JSON으로 저장
"""
from data_preprocess import process_uploaded_files, process_with_auto_filename


def main():
    """메인 실행 함수"""
    print("🚀 업로드 파일 처리 시작")
    
    # 방법 1: 자동 파일명 생성 (No_1.txt, No_2.txt, ...)
    print("\n1️⃣ 자동 파일명으로 처리")
    result = process_with_auto_filename()
    
    print(f"처리 결과: {result}")
    
    if result['success']:
        print(f"✅ 성공: {result['output_file']}")
        print(f"처리된 파일: {result['files_processed']}")
    else:
        print(f"❌ 실패: {result['message']}")
    
    # 방법 2: 지정된 파일명으로 처리
    print("\n2️⃣ 지정된 파일명으로 처리")
    result2 = process_uploaded_files("No_1.txt")
    
    print(f"처리 결과: {result2}")


if __name__ == "__main__":
    main()
