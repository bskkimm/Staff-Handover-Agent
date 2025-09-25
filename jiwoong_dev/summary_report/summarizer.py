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
    
    # 테스트용 HR 이메일 데이터
    sample_email = """
    From: 김민수 <kim.minsu@example.com>
    To: 박서연 <park.seoyeon@example.com>, 오현우 <oh.hyunwoo@example.com>
    Cc: 서유나 <seo.yuna@example.com>
    Date: Thu, 22 Aug 2024 15:25 +0900 (KST)
    Subject: Re: HR schedule
    
    마지막 정리 드립니다.
    - HRIS Replatform 포스터 최종 검토 예정 - 이번주 금 17:00 (KST)
    - Compensation Review 마이그레이션 리허설 일정 조정 중
    - 다음달 첫째주 수 11:00 월간 리뷰 준비
    
    프로젝트 일정:
    - HRIS Replatform: 2023-11-27 ~ 2024-02-27
    - Compensation Review: 2024-02-27 ~ 2024-06-27
    
    체크리스트:
    1. 채용 JD 취합 - 이번주 금 17:00 (KST)
    2. HRIS 필드 매핑 검토 - 다음주 수 오전
    3. 월말 리포트 초안 - 월말 18:00
    """
    
    # GPT 에게 마크다운 보고서 생성 요청
    prompt = f"""
    다음 HR 팀 이메일 내용을 바탕으로 인수인계용 요약 보고서를 마크다운 형식으로 작성해주세요.
    
    **요구사항:**
    1. 제목은 # 으로 시작
    2. 섹션별로 ## 사용
    3. 리스트는 - 또는 1. 사용
    4. 중요한 내용은 **굵게** 표시
    5. 코드나 날짜는 `백틱`으로 감싸기
    6. 테이블 형식도 포함
    
    **이메일 내용:**
    {sample_email}
    
    다음 구조로 작성해주세요:
    - 프로젝트 개요
    - 진행 현황
    - 주요 일정
    - 미해결 과제
    - 인수인계 체크리스트
    """
    
    try:
        # Azure OpenAI API 호출
        response = client.chat.completions.create(
            model="aicore-gpt4o",  
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 HR 업무 전문가입니다. 전임자로서 후임자에게 인수인계를 하기 위한 명확하고 체계적인 마크다운 보고서를 작성합니다."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            max_tokens=1500,
            temperature=0.2
        )
        
        
        markdown_report = response.choices[0].message.content
        
        print("=" * 50)
        print("마크다운 보고서 출력 테스트")
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