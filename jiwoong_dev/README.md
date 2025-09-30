# BATON - 통합 인수인계 관리 시스템

BATON은 AI 기반의 종합적인 인수인계 관리 시스템입니다. 업로드된 문서들을 자동으로 분석하고, 요약 리포트를 생성하며, 스케줄을 추출하고 시각화하며, Q&A 챗봇을 제공합니다.

## 🚀 주요 기능

### 1. 파일 업로드 및 관리
- **지원 형식**: PDF, TXT, DOCX, CSV
- **파일 관리**: 개별/전체 삭제, 중복 검사, 크기 제한 (10MB)
- **데이터베이스**: SQLite 기반 파일 메타데이터 저장

### 2. 데이터 전처리
- **자동 분류**: 이메일, 회의록, 개인노트 자동 감지
- **구조화**: 각 문서 타입에 맞는 파싱 및 구조화
- **태그 추출**: 프로젝트명, 키워드 자동 추출

### 3. AI 요약 리포트
- **Azure OpenAI**: GPT-4 기반 요약 생성
- **마크다운 형식**: 체계적인 구조의 요약 보고서
- **인수인계 최적화**: 후임자를 위한 맞춤형 내용

### 4. 스케줄 추출 및 시각화
- **자동 추출**: 문서에서 프로젝트 일정 자동 추출
- **다양한 출력**: Markdown, PNG 타임라인, ICS 캘린더
- **시각화**: 월별 캘린더 바 차트 생성

### 5. RAG 기반 Q&A 챗봇
- **AI 페르소나**: "인사팀 대리 김민수"로 설정
- **벡터 검색**: FAISS 기반 문서 검색
- **자연스러운 대화**: 친근한 말투의 질문-답변

## 📋 설치 및 설정

### 1. 환경 설정
```bash
# .env 파일 생성 (handover 디렉토리에)
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_CHAT_DEPLOYMENT=aicore-gpt4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=your_embedding_deployment_name
```

### 2. 필요한 패키지 설치
```bash
pip install streamlit streamlit-option-menu openai python-dotenv faiss-cpu matplotlib numpy pandas
```

### 3. 애플리케이션 실행
```bash
cd handover
streamlit run main.py
```

## 🎯 사용법

### 1. 파일 업로드
1. **파일 업로드** 메뉴에서 인수인계 관련 문서들을 업로드
2. 지원 형식: PDF, TXT, DOCX, CSV
3. 여러 파일을 한 번에 업로드 가능

### 2. 인수인계 자료 추출
1. **인수인계 자료 추출** 메뉴로 이동
2. **🚀 전체 파이프라인 실행** 버튼 클릭
3. 또는 개별 기능 실행:
   - **📝 데이터 전처리**: 파일 분석 및 분류
   - **📊 요약 리포트 생성**: AI 기반 요약 생성
   - **📅 스케줄 추출**: 일정 추출 및 시각화

### 3. Q&A 챗봇
1. **Q&A** 메뉴로 이동
2. 전임자에게 궁금한 점을 질문
3. 업로드된 문서 기반으로 답변 제공

### 4. 스케줄 확인
1. **스케줄 확인** 메뉴로 이동
2. 생성된 스케줄 파일들 확인
3. 타임라인 이미지, 마크다운, ICS 파일 다운로드

## 📁 프로젝트 구조

```
jiwoong_dev/handover/
├── main.py                    # 메인 애플리케이션
├── utils.py                   # 유틸리티 함수들
├── integrated_modules.py      # 통합 모듈 함수들
├── file_upload/              # 파일 업로드 모듈
│   ├── database.py           # SQLite 데이터베이스
│   ├── models.py             # 데이터 모델
│   └── upload_page.py        # 업로드 UI
├── data_preprocess/          # 데이터 전처리
│   ├── email_preprocessor.py # 이메일 전처리
│   └── preprocessor_test.py  # 전처리 테스트
├── summary_report/           # 요약 리포트
│   └── summarizer.py         # AI 요약 생성
├── scheduling/               # 스케줄 관리
│   ├── scheduling_main.py    # 스케줄 추출
│   └── desk_calendar_bar_viz.py # 시각화
├── chatbot/                  # RAG 챗봇
│   ├── rag_app.py           # 챗봇 앱
│   ├── build_index.py       # 인덱스 구축
│   └── rag_store/           # 벡터 저장소
└── data/                     # 데이터 저장소
    └── uploads/             # 업로드된 파일들
```

## 🔧 주요 기술 스택

- **Frontend**: Streamlit
- **AI/ML**: Azure OpenAI (GPT-4, 임베딩)
- **벡터 검색**: FAISS
- **데이터베이스**: SQLite
- **시각화**: Matplotlib
- **문서 처리**: 다양한 형식 지원

## 📝 사용 예시

### 1. 전체 파이프라인 실행
```python
# main.py에서 자동으로 실행되는 과정:
# 1. 파일 업로드 → 2. 데이터 전처리 → 3. 요약 생성 → 4. 스케줄 추출 → 5. 챗봇 준비
```

### 2. 개별 기능 실행
```python
# 데이터 전처리만 실행
from integrated_modules import run_data_preprocessing
result = run_data_preprocessing(files_data)

# 요약 리포트만 생성
from integrated_modules import run_summary_generation
result = run_summary_generation(processed_data)
```

## 🚨 주의사항

1. **Azure OpenAI 설정**: .env 파일에 올바른 API 키와 엔드포인트 설정 필요
2. **파일 크기 제한**: 개별 파일당 10MB 제한
3. **지원 형식**: PDF, TXT, DOCX, CSV만 지원
4. **인터넷 연결**: Azure OpenAI API 호출을 위해 필요

## 🆘 문제 해결

### 1. Azure OpenAI 연결 오류
- .env 파일의 API 키와 엔드포인트 확인
- 네트워크 연결 상태 확인

### 2. 파일 업로드 오류
- 파일 크기 확인 (10MB 이하)
- 지원 형식 확인 (PDF, TXT, DOCX, CSV)

### 3. 처리 결과가 없는 경우
- 파일 내용이 비어있지 않은지 확인
- Azure OpenAI API 할당량 확인

## 📞 지원

문제가 발생하거나 개선 사항이 있으면 개발팀에 문의해주세요.
