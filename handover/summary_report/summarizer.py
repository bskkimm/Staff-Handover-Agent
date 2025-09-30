from openai import AzureOpenAI
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# Azure OpenAI 클라이언트 설정
client = AzureOpenAI(
    api_key=os.getenv('AZURE_OPENAI_API_KEY'),
    api_version="2024-02-01",  # 최신 API 버전
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')  
)

def test_llm_markdown_output():
    """
    OpenAI GPT-4 API로 마크다운 형식 보고서 생성 테스트
    """
    
    # 실제 파일에서 데이터 읽기
    file_path = "../../data/preprocessed_data/No_1.txt"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            working_tasks = f.read()
        print(f"파일 로드 성공: {file_path}")
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return None
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        return None
    
    # GPT 에게 마크다운 보고서 생성 요청
    prompt = f"""
    다음 전임자의 업무 내용을 바탕으로 후임자에게 전달할 인수인계용 요약 보고서를 마크다운 형식으로 작성해주세요.
    
    **요구사항:**
    1. 제목은 # 으로 시작
    2. 제목의 하위 섹션별로 ## 사용
    3. 리스트는 - 또는 1. 사용
    4. 중요한 내용은 **굵게** 표시(볼드체)
    5. 코드나 날짜는 `백틱`으로 감싸기(인용문)
    6. 테이블 형식도 포함
    
    **이메일 내용:**
    {working_tasks}
    
    다음 구조로 작성해주세요:
    [프로젝트 개요]
    -- 프로젝트 명, 프로젝트 기간, 프로젝트 목표
    [진행 현황]
    -- 해결과제, 미해결과제
    [주요 일정]
    [잔여 업무 체크리스트]
    """
    
    try:
        # Azure OpenAI API 호출
        response = client.chat.completions.create(
            model="aicore-gpt4o",  
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 조직 업무 관리 전문가입니다. 전임자로서 후임자에게 인수인계를 하기 위한 명확하고 체계적인 마크다운 보고서를 작성합니다."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            max_tokens=1800,
            temperature=0.2
        )
        
        
        markdown_report = response.choices[0].message.content
        
        print("=" * 50)
        print("인수인계 요약 레포트 ")
        print("=" * 50)
        print(markdown_report)
        print("=" * 50)
        
        return markdown_report
        
    except Exception as e:
        print(f"API 호출 오류: {e}")
        return None

def save_markdown_to_file(markdown_content, filename="test_report.md"):
    """
    생성된 마크다운을 파일로 저장
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"마크다운 파일 저장 완료: {filename}")
    except Exception as e:
        print(f"파일 저장 오류: {e}")

if __name__ == "__main__":
    result = test_llm_markdown_output()
    
    if result:
        save_markdown_to_file(result, "test_report.md")
        print("\n테스트 완료! test_report.md 파일 확인")