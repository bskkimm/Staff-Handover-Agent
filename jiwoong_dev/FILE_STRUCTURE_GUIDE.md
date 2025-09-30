# BATON 시스템 파일 구조 및 워크플로우 가이드

## 📁 전체 파일 트리 구조

```
jiwoong_dev/
├── handover/                          # 메인 애플리케이션 디렉토리
│   ├── main.py                        # 🚀 메인 Streamlit 앱 (진입점)
│   ├── utils.py                       # 🔧 유틸리티 함수들
│   ├── integrated_modules.py          # 🔗 통합 모듈 함수들
│   ├── .env                          # 🔐 환경변수 설정
│   │
│   ├── file_upload/                   # 📤 파일 업로드 시스템
│   │   ├── __init__.py               # 패키지 초기화
│   │   ├── database.py               # 🗄️ SQLite 데이터베이스 관리
│   │   ├── models.py                 # 📋 데이터 모델 정의
│   │   └── upload_page.py            # 📄 업로드 UI 페이지
│   │
│   ├── data_preprocess/               # 🔄 데이터 전처리 시스템
│   │   ├── email_preprocessor.py     # 📧 이메일 전처리
│   │   └── preprocessor_test.py      # 🧪 전처리 테스트 및 메인 로직
│   │
│   ├── summary_report/                # 📊 AI 요약 리포트
│   │   ├── summarizer.py             # 🤖 AI 요약 생성
│   │   └── summarizer_mail_test.py   # 🧪 요약 테스트
│   │
│   ├── scheduling/                    # 📅 스케줄 관리 시스템
│   │   ├── scheduling_main.py        # 🎯 스케줄 추출 메인 로직
│   │   ├── desk_calendar_bar_viz.py  # 📊 캘린더 시각화
│   │   └── output/                   # 📁 생성된 스케줄 파일들
│   │       ├── combined_schedule.md
│   │       ├── combined_schedule_timeline.png
│   │       └── combined_schedule.ics
│   │
│   ├── chatbot/                       # 💬 RAG 챗봇 시스템
│   │   ├── __init__.py               # 패키지 초기화
│   │   ├── rag_app.py                # 🤖 챗봇 메인 앱
│   │   ├── build_index.py            # 🔍 벡터 인덱스 구축
│   │   ├── ingest.py                 # 📥 문서 임베딩 처리
│   │   ├── rag_store.py              # 🗃️ 벡터 저장소 관리
│   │   └── rag_store/                # 📁 벡터 인덱스 파일들
│   │       ├── index.faiss
│   │       └── meta.jsonl
│   │
│   ├── common/                        # 🔧 공통 유틸리티
│   │   ├── chunker.py                # ✂️ 텍스트 청킹
│   │   ├── embed.py                  # 🧮 임베딩 처리
│   │   ├── ingest.py                 # 📥 데이터 수집
│   │   ├── retriever.py              # 🔍 검색 엔진
│   │   └── store.py                  # 🗄️ 저장소 관리
│   │
│   └── data/                          # 📁 데이터 저장소
│       ├── file_metadata.db          # 🗄️ SQLite 데이터베이스
│       └── uploads/                   # 📁 업로드된 파일들
│           ├── 20250925_113158_0245a76d.txt
│           ├── 20250925_113158_277b77a3.txt
│           └── ...
│
├── requirements.txt                   # 📦 Python 패키지 의존성
├── README.md                         # 📖 사용법 가이드
├── ARCHITECTURE.md                   # 🏗️ 시스템 아키텍처
├── quick_start.bat                   # 🚀 Windows 빠른 시작
├── quick_start.sh                    # 🐧 Linux/Mac 빠른 시작
└── run_baton.bat                     # 🎯 Windows 실행 스크립트
```

## 🔄 전체 워크플로우 및 파일 사용 흐름

### 1. 🚀 **애플리케이션 시작**
```
사용자 실행 → main.py → Streamlit 앱 시작
```

**주요 파일**: `main.py`
- **역할**: Streamlit 앱의 진입점
- **기능**: 
  - UI 구성 (사이드바, 페이지 라우팅)
  - 환경변수 로드 (`load_dotenv()`)
  - 세션 상태 관리

### 2. 📤 **파일 업로드 단계**
```
사용자 파일 선택 → upload_page.py → database.py → models.py → data/uploads/
```

**주요 파일들**:
- **`file_upload/upload_page.py`**: 업로드 UI 및 파일 처리
- **`file_upload/database.py`**: 파일 저장 및 메타데이터 관리
- **`file_upload/models.py`**: 데이터베이스 모델 정의
- **`data/uploads/`**: 실제 파일 저장 위치

**데이터 흐름**:
```python
# 1. 파일 업로드
upload_page.py → file_buffer, original_name

# 2. 데이터베이스 저장
database.py → save_file() → UploadedFile 객체 생성

# 3. 파일 시스템 저장
database.py → data/uploads/에 실제 파일 저장

# 4. 메타데이터 저장
models.py → SQLite DB에 파일 정보 저장
```

### 3. 🔄 **데이터 전처리 단계**
```
data/uploads/ → utils.py → preprocessor_test.py → 구조화된 데이터
```

**주요 파일들**:
- **`utils.py`**: 파일 데이터 읽기 및 유틸리티
- **`data_preprocess/preprocessor_test.py`**: 파일 타입 감지 및 파싱
- **`data_preprocess/email_preprocessor.py`**: 이메일 전처리 로직

**데이터 흐름**:
```python
# 1. 파일 데이터 읽기
utils.py → get_uploaded_files_data() → files_data (Dict[str, str])

# 2. 파일 타입 감지
preprocessor_test.py → detect_file_type() → FileType.EMAIL/MEETING/PERSONAL

# 3. 타입별 파싱
preprocessor_test.py → parse_email()/parse_meeting_minutes()/parse_personal_note()

# 4. 구조화된 데이터 반환
processed_data = {
    'emails': [Email 객체들],
    'meetings': [Meeting 객체들],
    'personal_notes': [PersonalNote 객체들]
}
```

### 4. 📊 **AI 요약 생성 단계**
```
구조화된 데이터 → integrated_modules.py → summarizer.py → Azure OpenAI → 마크다운 리포트
```

**주요 파일들**:
- **`integrated_modules.py`**: 요약 생성 통합 함수
- **`summary_report/summarizer.py`**: AI 요약 생성 로직

**데이터 흐름**:
```python
# 1. 데이터 변환
integrated_modules.py → run_summary_generation() → content_text

# 2. AI 요약 생성
summarizer.py → Azure OpenAI API → GPT-4 응답

# 3. 마크다운 리포트 반환
markdown_report = response.choices[0].message.content
```

### 5. 📅 **스케줄 추출 단계**
```
원본 파일 → integrated_modules.py → scheduling_main.py → 시각화 파일들
```

**주요 파일들**:
- **`integrated_modules.py`**: 스케줄 추출 통합 함수
- **`scheduling/scheduling_main.py`**: 스케줄 추출 메인 로직
- **`scheduling/desk_calendar_bar_viz.py`**: 캘린더 시각화

**데이터 흐름**:
```python
# 1. 임시 파일 생성
integrated_modules.py → create_temp_txt_files() → temp_dir

# 2. 스케줄 추출
scheduling_main.py → aggregate_all() → groups (프로젝트별 일정)

# 3. 다양한 형식 출력
scheduling_main.py → build_markdown() → .md 파일
scheduling_main.py → visualize_calendar() → .png 파일
scheduling_main.py → write_ics() → .ics 파일
desk_calendar_bar_viz.py → render_all_months_bars() → 월별 차트
```

### 6. 💬 **챗봇 시스템 단계**
```
문서 → chatbot/ → FAISS 인덱스 → RAG 검색 → GPT-4 답변
```

**주요 파일들**:
- **`chatbot/rag_app.py`**: 챗봇 메인 앱
- **`chatbot/build_index.py`**: 벡터 인덱스 구축
- **`chatbot/ingest.py`**: 문서 임베딩 처리
- **`chatbot/rag_store.py`**: 벡터 저장소 관리
- **`chatbot/rag_store/`**: FAISS 인덱스 파일들

**데이터 흐름**:
```python
# 1. 문서 임베딩
ingest.py → embed_text() → 벡터 생성

# 2. 인덱스 구축
build_index.py → FAISS 인덱스 생성 → index.faiss, meta.jsonl

# 3. 질의응답
rag_app.py → embed_text(질문) → FAISS 검색 → 관련 문서 → GPT-4 답변
```

## 🔧 **핵심 파일별 상세 역할**

### **🚀 main.py** (메인 컨트롤러)
```python
# 주요 기능
- Streamlit UI 구성
- 페이지 라우팅 (메인, 업로드, 추출, Q&A, 스케줄)
- 세션 상태 관리
- 환경변수 로드
```

### **🔧 utils.py** (유틸리티 함수들)
```python
# 주요 함수
- get_uploaded_files_data(): 파일 데이터 읽기
- check_azure_openai_config(): 환경변수 확인
- create_temp_txt_files(): 임시 파일 생성
- format_file_size(): 파일 크기 포맷팅
```

### **🔗 integrated_modules.py** (통합 모듈)
```python
# 주요 함수
- run_full_pipeline(): 전체 파이프라인 실행
- run_data_preprocessing(): 데이터 전처리
- run_summary_generation(): 요약 생성
- run_schedule_extraction(): 스케줄 추출
- run_chatbot_integration(): 챗봇 통합
```

### **🗄️ file_upload/database.py** (데이터베이스 관리)
```python
# 주요 클래스/함수
- FileDatabase: 파일 데이터베이스 관리
- save_file(): 파일 저장
- get_all_files(): 모든 파일 조회
- delete_file(): 파일 삭제
```

### **🧪 data_preprocess/preprocessor_test.py** (전처리 엔진)
```python
# 주요 함수
- detect_file_type(): 파일 타입 감지
- parse_email(): 이메일 파싱
- parse_meeting_minutes(): 회의록 파싱
- parse_personal_note(): 개인노트 파싱
- process_all_files(): 전체 파일 처리
```

### **🤖 summary_report/summarizer.py** (AI 요약)
```python
# 주요 함수
- test_llm_markdown_output(): AI 요약 생성
- Azure OpenAI API 호출
- 마크다운 형식 리포트 생성
```

### **📅 scheduling/scheduling_main.py** (스케줄 추출)
```python
# 주요 함수
- aggregate_all(): 스케줄 통합
- build_markdown(): 마크다운 생성
- visualize_calendar(): 시각화
- write_ics(): 캘린더 파일 생성
```

### **💬 chatbot/rag_app.py** (챗봇 앱)
```python
# 주요 함수
- run_chat(): 챗봇 실행
- embed_text(): 텍스트 임베딩
- retrieve_topk(): 벡터 검색
- chat_with_context(): 컨텍스트 기반 답변
```

## 📊 **데이터 저장 위치**

### **🗄️ SQLite 데이터베이스**
- **위치**: `data/file_metadata.db`
- **내용**: 파일 메타데이터 (이름, 크기, 해시, 경로 등)

### **📁 업로드된 파일들**
- **위치**: `data/uploads/`
- **형식**: `YYYYMMDD_HHMMSS_hash8.확장자`

### **📊 생성된 결과 파일들**
- **스케줄**: `scheduling/output/`
- **벡터 인덱스**: `chatbot/rag_store/`

## 🔄 **실행 순서 요약**

1. **`main.py`** → Streamlit 앱 시작
2. **`upload_page.py`** → 파일 업로드
3. **`database.py`** → 파일 저장
4. **`utils.py`** → 파일 데이터 읽기
5. **`preprocessor_test.py`** → 데이터 전처리
6. **`summarizer.py`** → AI 요약 생성
7. **`scheduling_main.py`** → 스케줄 추출
8. **`rag_app.py`** → 챗봇 준비
9. **결과 표시** → UI 업데이트

이렇게 BATON 시스템은 각 파일이 명확한 역할을 가지고 있으며, 데이터가 순차적으로 흘러가면서 최종적으로 완전한 인수인계 관리 시스템을 구성합니다! 🚀
