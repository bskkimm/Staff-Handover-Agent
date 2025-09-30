"""
모듈화된 전처리기 사용 예제
"""
from .main_processor import process_and_export_json


def main():
    """메인 실행 함수"""
    # 테스트 디렉토리 경로
    test_directory = "C:/Users/Administrator/SK_AX_Bootcamp/Staff-Handover-Agent/data/compensation/Test"
    
    # 파일들을 처리하고 JSON으로 변환
    json_output = process_and_export_json(test_directory)
    
    # 결과 출력
    print(json_output)


if __name__ == "__main__":
    main()
