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

def test_llm_markdown_output():
    """
    OpenAI GPT-4 API로 마크다운 형식 보고서 생성 테스트
    """
    
    # 실제 파일에서 데이터 읽기 (스크립트 기준 상대 경로를 결합)
    script_dir = Path(__file__).resolve().parent
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
    너는 대기업에서 실제로 쓰이는 **인수인계 보고서**를 작성하는 조직 업무 관리 전문가야.
    너에게 제공하는 하나의 JSON에는 이메일(threads), 회의록(meetings), 개인 메모(personal_notes), 기타 자료가 들어 있어.
    이 JSON을 참고하여, 후임자가 바로 업무 현황을 파악할 수 있는 **간결하고 체계적인 인수인계 보고서**를 마크다운 형식으로 작성해.

    # 지침 (반드시 준수)
    - 한국어로 작성
    - 마크다운 사용: 제목은 `#`, 하위 섹션은 `##`, 목록은 `-` 사용
    - **중요 키워드**는 굵게(**) 표시
    - 모든 **날짜·시간**은 백틱으로 감싸고(예: `2025-07-22 18:00`), **Asia/Seoul(UTC+9)** 기준으로 표기
    - "이전 메일" 참조가 있으면 **타임라인 상 앞선 항목으로 연결**하여 의사결정 흐름을 요약
    - 불명확하거나 JSON에 없는 내용은 **추정하지 말고** "미확인"으로 표시

    # 목표
    후임자가 30분 내 전체 맥락을 파악하고, 1주일 내 핵심 마일스톤을 완료할 수 있도록
    **프로젝트 개요 → 진행 현황 → 타임라인/일정 → 잔여 과제/리스크** 순으로 정리합니다.

    # 데이터(JSON)
    {working_tasks}

    # 처리 절차
    1) **프로젝트 식별**: 이메일/회의/메모 기타 자료의 제목과 본문에서 공통 키워드(예: 보상, 예산가이드, 1차시뮬레이션, 연간정책킥오프)를 추출해 프로젝트를 1개로 통합 서술.
    2) **기간 산정**: 가장 이른 날짜와 가장 늦은 날짜를 찾아 프로젝트 기간으로 표기.
    3) **의사결정 히스토리**: "첫 공지", "v0.x", "확정안" 등 버전 진화와 "이전 메일" 레퍼런스를 시간순으로 요약.
    4) **역할/이해관계자**: 발신자/수신자/CC/회의 참석자에서 **핵심 이해관계자**를 표로 정리(이름, 역할 추정: 발신=리드/오너, 수신=실무, CC=참조 등).
    5) **주요 산출물/상태**: "자료 초안 배포", "예산 가이드", "시뮬레이션" 등 산출물과 상태(배포/검토/확정/보정 필요)를 분류.
    6) **주요 일정**: 이메일/회의의 일정안을 병합, **마감 시각** 포함하여 테이블화.
    7) **잔여 업무/체크리스트**: 체크리스트·액션아이템을 중복 제거 후 **담당/기한/출처**로 테이블화.
    8) **리스크 & 의존성**: 이상치, 데이터 품질, 승인 라인, 접근 권한 등의 리스크를 심각도/대응으로 정리.
    9) **다음 7일 실행 계획**: JSON에서 가장 최신 상태를 기준으로 **D+7 실행계획**을 우선순위로 제시.

    # 출력 형식 (이 템플릿을 유지)

    # 인수인계 요약 레포트

    ## 기본 정보
    ### - 인계자 :
    ### - 인수자 :
    ### - 일자 :
    ### - 기타 관련 실무자 :

    ## 업무 현황
    ### 1. 담당 업무

    ### 2. 주요 업무계획 및 진행사항

    ### 3. 현안사항 및 문제점

    ### 4. 주요 미결사항

    ### 5. 기타 참고사항

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