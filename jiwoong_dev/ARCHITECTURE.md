# BATON 시스템 아키텍처

## 🏗️ 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Streamlit)                    │
├─────────────────────────────────────────────────────────────────┤
│  main.py (UI Controller)                                       │
│  ├── Sidebar Navigation                                        │
│  ├── File Upload Interface                                     │
│  ├── Processing Pipeline UI                                    │
│  ├── Q&A Chat Interface                                        │
│  └── Schedule Visualization UI                                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND (Python)                        │
├─────────────────────────────────────────────────────────────────┤
│  integrated_modules.py (Business Logic)                        │
│  ├── run_data_preprocessing()                                  │
│  ├── run_summary_generation()                                  │
│  ├── run_schedule_extraction()                                 │
│  └── run_chatbot_integration()                                 │
│                                                                 │
│  utils.py (Utility Functions)                                  │
│  ├── get_uploaded_files_data()                                 │
│  ├── create_temp_txt_files()                                   │
│  └── check_azure_openai_config()                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA PROCESSING LAYER                       │
├─────────────────────────────────────────────────────────────────┤
│  data_preprocess/preprocessor_test.py                          │
│  ├── detect_file_type()                                        │
│  ├── parse_email()                                             │
│  ├── parse_meeting_minutes()                                   │
│  └── parse_personal_note()                                     │
│                                                                 │
│  file_upload/                                                  │
│  ├── database.py (SQLite)                                      │
│  ├── models.py (Data Models)                                   │
│  └── upload_page.py (Upload Logic)                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        LLM/AI LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│  Azure OpenAI API                                              │
│  ├── GPT-4 (Text Generation)                                   │
│  ├── Text-Embedding-3 (Vector Embeddings)                      │
│  └── API Response Handling                                     │
│                                                                 │
│  FAISS Vector Store                                            │
│  ├── index.faiss (Vector Index)                                │
│  └── meta.jsonl (Metadata)                                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        STORAGE LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  Local File System                                             │
│  ├── data/uploads/ (Uploaded Files)                            │
│  ├── scheduling/output/ (Generated Schedules)                  │
│  ├── chatbot/rag_store/ (Vector Store)                         │
│  └── data/file_metadata.db (SQLite Database)                   │
└─────────────────────────────────────────────────────────────────┘
```

## 🎨 프론트엔드 (Frontend) - Streamlit

### 주요 컴포넌트:
- **main.py**: 메인 UI 컨트롤러
- **사이드바 네비게이션**: 5개 메뉴 (메인, 파일업로드, 자료추출, Q&A, 스케줄확인)
- **동적 UI**: 파일 업로드 상태에 따라 메뉴 항목 변경

### 데이터 흐름:
```python
# 1. 사용자 인터랙션
st.button("🚀 전체 파이프라인 실행") 
    ↓
# 2. 백엔드 함수 호출
run_full_processing_pipeline()
    ↓
# 3. 결과를 session_state에 저장
st.session_state.processing_results = result
    ↓
# 4. UI 업데이트
display_processing_results(results)
```

## ⚙️ 백엔드 (Backend) - Python

### 1. Business Logic Layer (integrated_modules.py)

#### 데이터 전처리 파이프라인:
```python
def run_data_preprocessing(files_data):
    # 1. 파일 타입 감지 및 분류
    processed_data = process_all_files(files_data)
    
    # 2. 결과 구조화
    return {
        'emails': [...],      # 이메일 객체들
        'meetings': [...],    # 회의록 객체들  
        'personal_notes': [...] # 개인노트 객체들
    }
```

#### 요약 생성 파이프라인:
```python
def run_summary_generation(processed_data):
    # 1. 전처리된 데이터를 텍스트로 변환
    content_text = convert_to_text(processed_data)
    
    # 2. Azure OpenAI API 호출
    response = client.chat.completions.create(
        model="aicore-gpt4o",
        messages=[system_prompt, user_prompt]
    )
    
    # 3. 마크다운 리포트 반환
    return response.choices[0].message.content
```

#### 스케줄 추출 파이프라인:
```python
def run_schedule_extraction(files_data):
    # 1. 임시 txt 파일들 생성
    temp_dir = create_temp_txt_files(files_data)
    
    # 2. AI로 일정 추출
    groups = aggregate_all(files_with_text)
    
    # 3. 다양한 형식으로 출력
    save_markdown(md_content, out_md)
    visualize_calendar(md_content, out_png)
    write_ics(md_content, out_ics)
```

### 2. Utility Layer (utils.py)

#### 파일 관리:
```python
def get_uploaded_files_data():
    # SQLite에서 파일 메타데이터 조회
    files = file_db.get_all_files()
    
    # 실제 파일 내용 읽기
    for file_record in files:
        file_path = os.path.join("data/uploads", file_record.stored_filename)
        content = read_file_content(file_path)
        files_data[file_record.original_name] = content
    
    return files_data
```

## 🤖 LLM/AI 파트

### 1. Azure OpenAI API 통합

#### 텍스트 생성 (GPT-4):
```python
# 요약 리포트 생성
response = client.chat.completions.create(
    model="aicore-gpt4o",
    messages=[
        {"role": "system", "content": "HR 업무 전문가 페르소나"},
        {"role": "user", "content": f"다음 내용을 요약해주세요: {content_text}"}
    ],
    max_tokens=2000,
    temperature=0.2
)
```

#### 벡터 임베딩 (Text-Embedding-3):
```python
# 챗봇용 문서 임베딩
def embed_text(client, text):
    vec = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    ).data[0].embedding
    return np.array(vec, dtype="float32")
```

### 2. RAG (Retrieval-Augmented Generation) 시스템

#### 벡터 저장소 (FAISS):
```python
# 문서 임베딩 및 저장
index = faiss.IndexFlatIP(embedding_dim)
index.add(document_embeddings)

# 검색
scores, indices = index.search(query_embedding, k=6)
```

#### 챗봇 응답 생성:
```python
def chat_with_context(client, system_prompt, user_prompt):
    # 1. 사용자 질문 임베딩
    q_vec = embed_text(client, user_question)
    
    # 2. 관련 문서 검색
    hits = retrieve_topk(index, meta, q_vec, k=6)
    
    # 3. 컨텍스트 구성
    context = build_context(hits)
    
    # 4. GPT-4로 답변 생성
    response = client.chat.completions.create(
        model="aicore-gpt4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"컨텍스트: {context}\n질문: {user_question}"}
        ]
    )
```

## 💾 데이터 저장 및 흐름

### 1. 파일 업로드 → 저장
```
사용자 파일 업로드
    ↓
file_upload/upload_page.py
    ↓
SQLite DB (file_metadata.db) ← 메타데이터 저장
    ↓
data/uploads/ ← 실제 파일 저장
```

### 2. 전처리 → 구조화
```
원본 파일 (PDF, DOCX, TXT)
    ↓
data_preprocess/preprocessor_test.py
    ↓
구조화된 데이터 (Email, Meeting, PersonalNote 객체)
    ↓
메모리에서 처리 (session_state)
```

### 3. AI 처리 → 결과 저장
```
구조화된 데이터
    ↓
Azure OpenAI API 호출
    ↓
AI 응답 (텍스트, 임베딩)
    ↓
scheduling/output/ ← 스케줄 파일들
chatbot/rag_store/ ← 벡터 인덱스
```

### 4. 챗봇 질의응답
```
사용자 질문
    ↓
질문 임베딩 생성
    ↓
FAISS 벡터 검색
    ↓
관련 문서 검색
    ↓
GPT-4로 답변 생성
    ↓
사용자에게 응답
```

## 🔄 실시간 데이터 흐름

### 전체 파이프라인 실행 시:
```
1. 파일 업로드 확인
   ↓
2. 데이터 전처리 (이메일/회의록/개인노트 분류)
   ↓
3. AI 요약 생성 (GPT-4)
   ↓
4. 스케줄 추출 (GPT-4 + 시각화)
   ↓
5. 챗봇 인덱스 구축 (임베딩 + FAISS)
   ↓
6. 결과 저장 및 UI 업데이트
```

### 메모리 사용:
- **session_state**: 처리 결과 임시 저장
- **임시 파일**: 스케줄 처리용 txt 파일들
- **벡터 인덱스**: FAISS 인덱스 (메모리 + 디스크)

이렇게 BATON은 Streamlit 프론트엔드, Python 백엔드, Azure OpenAI LLM을 통합한 완전한 인수인계 관리 시스템입니다! 🚀
