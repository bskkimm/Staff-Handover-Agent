from openai import AzureOpenAI
import os
from dotenv import load_dotenv
from pathlib import Path

# 환경변수 로드
load_dotenv()

# Azure OpenAI 클라이언트 설정
client = AzureOpenAI(
    api_key=os.getenv('AZURE_OPENAI_API_KEY'),
    api_version="2024-02-01",  # 최신 API 버전
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')  
)

def test_llm_markdown_output(session_id: str = None):
    """
    OpenAI GPT-4 API로 마크다운 형식 보고서 생성 테스트
    """

    # 실제 파일에서 데이터 읽기
    script_dir = Path(__file__).resolve().parent

    # 세션별 경로
    if session_id:
        rel_to_script = Path("..") / ".." / "data" / "sessions" / session_id / "preprocessed_data" / "No_1.txt"
    else:
        rel_to_script = Path("..") / ".." / "data" / "preprocessed_data" / "No_1.txt"

    file_path = script_dir / rel_to_script
    
    try:
        with open(str(file_path), 'r', encoding='utf-8') as f:
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
    당신은 대기업 HR 프로젝트 실무의 인수인계를 담당하는 전문가입니다.
    아래 JSON(이메일 threads, 회의록, 개인 메모)을 통합 분석해 **마크다운**으로
    '업무 현황' 요약 레포트를 작성하세요.

    # 출력 형식 (반드시 이 제목·순서·형식을 유지)
    ## 업무 현황
    ### 1. 담당 업무
    - 본 프로젝트의 범위와 주요 책임을 한 문단으로 요약
    - 핵심 이해관계자(이름만, 이메일 비표시) 및 역할(리드/실무/참조) 정리(불명확하면 '미확인')

    ### 2. 주요 업무계획 및 진행사항
    - 최근 → 과거 순으로 5~10개 핵심 진행 업데이트를 불릿으로 요약
    - 각 항목 끝에 근거 출처를 `(근거: 이메일/회의/메모, \`YYYY-MM-DD HH:MM\`)` 형식으로 표기
    - 날짜·시간은 모두 **Asia/Seoul(UTC+9)** 기준으로 백틱(`)으로 감싸 표기

    ### 3. 현안사항 및 문제점
    - 데이터 품질/권한/승인/일정 등 이슈를 3~6개로 요약
    - 각 이슈마다 **영향**과 **즉시 대응안(1줄)** 포함

    ### 4. 주요 미결사항
    - 아직 미해결인 결정·검토·승인 사안을 3~8개로 정리
    - 각 항목에 **담당(미확인 가능)**, **목표 기한(있으면 날짜 백틱)**, **의존성** 기재

    ### 5. 기타 참고사항
    - 산출물(가이드/템플릿/시뮬 결과 등)과 버전·상태 간단 요약
    - 다음 7일 우선 실행 권고 3~5개(액션·완료기준·담당·\`기한\`)

    # 작성 규칙
    - 한국어, 간결·실무 중심 서술
    - **중요 키워드/마감**은 굵게(**) 표시
    - 표는 필요 시 1~2개까지 허용(예: 이해관계자/미결사항 요약), 과도한 표 사용 금지
    - JSON에 없는 정보는 추정하지 말고 '미확인'으로 표기
    - 중복 메일은 **제목(Subject)** 단위로 스레드화하여 한 줄로 병합

    # 입력 데이터(JSON)
    {working_tasks}
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
            max_tokens=2500,
            temperature=0.2
        )
        
        
        markdown_report = response.choices[0].message.content
        
        print("=" * 50)
        print("인수인계 요약 레포트")
        print("=" * 50)
        print(markdown_report)
        print("=" * 50)

        return markdown_report
        
    except Exception as e:
        print(f"API 호출 오류: {e}")
        return None

def save_markdown_to_file(markdown_content, filename="test_report.md"):
    """
    생성된 마크다운을 Staff-Handover-Agent/data/summary_report 디렉토리에 파일로 저장
    """
    try:
        # Staff-Handover-Agent/data/summary_report 디렉토리 사용
        script_dir = Path(__file__).resolve().parent
        staff_handover_agent_dir = script_dir.parent.parent
        data_dir = staff_handover_agent_dir / "data" / "summary_report"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = data_dir / filename
        with open(str(file_path), 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"인수인계 요약 레포트 저장 완료: {file_path}")
    except Exception as e:
        print(f"파일 저장 오류: {e}")

if __name__ == "__main__":
    result = test_llm_markdown_output()
    
    if result:
        save_markdown_to_file(result, "test_report.md")
        print("\n test_report.md 파일 확인")