# BATON 시스템 - 정리된 파일 구조

## 🗑️ 삭제된 불필요한 파일들

### ✅ **삭제 완료된 파일들**:
1. **`data/`** (루트 디렉토리) - 중복된 데이터 디렉토리
2. **`handover/settings.py`** - 빈 설정 파일
3. **`handover/summary_report/summarizer_mail_test.py`** - 테스트 파일
4. **`handover/summary_report/test_report.md`** - 테스트 리포트
5. **`handover/scheduling/prototype_04A_viz_calendar.py`** - 프로토타입 파일
6. **`handover/scheduling/prototype_04A_viz_main_1.py`** - 프로토타입 파일
7. **`handover/chatbot/readme.txt`** - 불필요한 문서
8. **`handover/common/`** (전체 디렉토리) - 사용되지 않는 공통 모듈
9. **모든 `__pycache__/` 디렉토리들** - Python 캐시 파일들

## 📁 **정리된 최종 파일 구조**

```
jiwoong_dev/
├── handover/                          # 🚀 메인 애플리케이션
│   ├── main.py                        # Streamlit 앱 진입점
│   ├── utils.py                       # 유틸리티 함수들
│   ├── integrated_modules.py          # 통합 모듈 함수들
│   ├── .env                          # 환경변수 설정
│   │
│   ├── file_upload/                   # 📤 파일 업로드 시스템
│   │   ├── __init__.py
│   │   ├── database.py               # SQLite 데이터베이스 관리
│   │   ├── models.py                 # 데이터 모델 정의
│   │   └── upload_page.py            # 업로드 UI 페이지
│   │
│   ├── data_preprocess/               # 🔄 데이터 전처리
│   │   ├── email_preprocessor.py     # 이메일 전처리
│   │   └── preprocessor_test.py      # 전처리 메인 로직
│   │
│   ├── summary_report/                # 📊 AI 요약 리포트
│   │   └── summarizer.py             # AI 요약 생성
│   │
│   ├── scheduling/                    # 📅 스케줄 관리
│   │   ├── __init__.py
│   │   ├── scheduling_main.py        # 스케줄 추출 메인 로직
│   │   ├── desk_calendar_bar_viz.py  # 캘린더 시각화
│   │   └── output/                   # 생성된 스케줄 파일들
│   │       ├── combined_schedule.md
│   │       ├── combined_schedule_timeline.png
│   │       ├── combined_schedule.ics
│   │       └── out_cal_bars/         # 월별 캘린더 바
│   │
│   ├── chatbot/                       # 💬 RAG 챗봇 시스템
│   │   ├── __init__.py
│   │   ├── rag_app.py                # 챗봇 메인 앱
│   │   ├── build_index.py            # 벡터 인덱스 구축
│   │   ├── ingest.py                 # 문서 임베딩 처리
│   │   ├── rag_store.py              # 벡터 저장소 관리
│   │   └── rag_store/                # FAISS 벡터 인덱스
│   │       ├── index.faiss
│   │       └── meta.jsonl
│   │
│   └── data/                          # 📁 데이터 저장소
│       ├── file_metadata.db          # SQLite 데이터베이스
│       └── uploads/                   # 업로드된 파일들
│           └── [13개 txt 파일들]
│
├── requirements.txt                   # 📦 Python 패키지 의존성
├── README.md                         # 📖 사용법 가이드
├── ARCHITECTURE.md                   # 🏗️ 시스템 아키텍처
├── FILE_STRUCTURE_GUIDE.md           # 📋 파일 구조 가이드
├── quick_start.bat                   # 🚀 Windows 빠른 시작
├── quick_start.sh                    # 🐧 Linux/Mac 빠른 시작
├── run_baton.bat                     # 🎯 Windows 실행 스크립트
├── run_baton.sh                      # 🐧 Linux/Mac 실행 스크립트
└── venv/                             # 🐍 Python 가상환경
```

## 🎯 **핵심 파일들 (총 20개)**

### **메인 애플리케이션 (3개)**
- `main.py` - Streamlit 앱 진입점
- `utils.py` - 유틸리티 함수들
- `integrated_modules.py` - 통합 모듈

### **파일 업로드 (4개)**
- `file_upload/__init__.py`
- `file_upload/database.py`
- `file_upload/models.py`
- `file_upload/upload_page.py`

### **데이터 전처리 (2개)**
- `data_preprocess/email_preprocessor.py`
- `data_preprocess/preprocessor_test.py`

### **AI 요약 (1개)**
- `summary_report/summarizer.py`

### **스케줄 관리 (3개)**
- `scheduling/__init__.py`
- `scheduling/scheduling_main.py`
- `scheduling/desk_calendar_bar_viz.py`

### **챗봇 시스템 (5개)**
- `chatbot/__init__.py`
- `chatbot/rag_app.py`
- `chatbot/build_index.py`
- `chatbot/ingest.py`
- `chatbot/rag_store.py`

### **설정 및 문서 (2개)**
- `.env` - 환경변수
- `requirements.txt` - 패키지 의존성

## 🚀 **실행 방법**

### **Windows**:
```bash
# 방법 1: 배치 파일 사용
run_baton.bat

# 방법 2: 빠른 시작
quick_start.bat

# 방법 3: 수동 실행
cd handover
streamlit run main.py
```

### **Linux/Mac**:
```bash
# 방법 1: 스크립트 사용
./run_baton.sh

# 방법 2: 빠른 시작
./quick_start.sh

# 방법 3: 수동 실행
cd handover
streamlit run main.py
```

## ✅ **정리 효과**

1. **파일 수 감소**: 불필요한 파일들 제거로 구조 단순화
2. **성능 향상**: 캐시 파일 제거로 실행 속도 개선
3. **유지보수성**: 핵심 파일들만 남겨 관리 용이
4. **명확한 구조**: 각 모듈의 역할이 명확해짐

이제 BATON 시스템이 깔끔하게 정리되어 더욱 효율적으로 사용할 수 있습니다! 🎉
