# 데이터 전처리 모듈

이 패키지는 이메일, 회의록, 개인기록 등의 텍스트 파일을 파싱하고 구조화된 데이터로 변환하는 기능을 제공합니다.

## 모듈 구조

```
data_preprocess/
├── __init__.py              # 패키지 초기화
├── file_utils.py            # 파일 처리 유틸리티
├── type_detector.py         # 파일 타입 감지
├── email_parser.py          # 이메일 파싱
├── meeting_parser.py        # 회의록 파싱
├── personal_parser.py       # 개인기록 파싱
├── main_processor.py        # 통합 처리기
├── preprocessor_test.py     # 사용 예제
└── README.md               # 이 파일
```

## 사용 방법

### 1. 업로드 파일 처리 (권장)

```python
from data_preprocess import process_with_auto_filename, process_uploaded_files

# 자동 파일명으로 처리 (No_1.txt, No_2.txt, ...)
result = process_with_auto_filename()
if result['success']:
    print(f"처리 완료: {result['output_file']}")

# 또는 지정된 파일명으로 처리
result = process_uploaded_files("No_1.txt")
```

### 2. 기본 사용법

```python
from data_preprocess import process_and_export_json

# 디렉토리의 모든 txt 파일을 처리하고 JSON으로 변환
json_output = process_and_export_json("path/to/directory")
print(json_output)
```

### 3. 단계별 사용법

```python
from data_preprocess import (
    read_multiple_txt_files,
    process_all_files,
    convert_to_json
)

# 1. 파일들 읽기
files_dict = read_multiple_txt_files("path/to/directory", "*.txt")

# 2. 파일들 처리
result = process_all_files(files_dict)

# 3. JSON으로 변환
json_output = convert_to_json(result)
```

### 4. 개별 모듈 사용법

```python
from data_preprocess import (
    detect_file_type,
    parse_email,
    parse_meeting_minutes,
    parse_personal_note,
    FileType
)

# 파일 타입 감지
file_type = detect_file_type(content)

# 타입별 파싱
if file_type == FileType.EMAIL:
    emails = parse_email(content)
elif file_type == FileType.MEETING:
    meeting = parse_meeting_minutes(content)
elif file_type == FileType.PERSONAL:
    personal = parse_personal_note(content, filename)
```

## 지원하는 파일 타입

### 1. 이메일 (Email)
- From:, To:, Subject:, Date: 헤더가 있는 파일
- Reply 메일과 Original 메일 분리 처리
- 발신자, 수신자, 제목, 내용 추출

### 2. 회의록 (Meeting)
- 제목, 일시, 장소, 참석자 정보
- 배경, 안건, 논의, 결정사항, 액션아이템 추출

### 3. 개인기록 (Personal)
- 작성자, 프로젝트, 관련 메일 정보
- 목표, 참고자료, 진행상태, 메모, 다음 액션 추출

## 출력 형식

처리된 데이터는 다음과 같은 구조로 반환됩니다:

```json
{
  "emails": [
    {
      "날짜": "2024-07-18 17:00",
      "제목": "보상 킥오프 회의 안건",
      "발신자": "김민수",
      "수신자": "박서연, 오현우",
      "참조": "",
      "내용": "회의 내용..."
    }
  ],
  "meetings": [
    {
      "타입": "meeting",
      "제목": "보상 킥오프 회의",
      "일시": "2024-07-19 11:00",
      "장소": "회의실 A",
      "작성자": "김민수",
      "참석자": "김민수, 박서연, 오현우",
      "배경": "2024-07-18 '보상_킥오프' 메일 후속",
      "안건": ["시장 데이터 소싱 계획", "레벨/밴드 규칙 재확인"],
      "논의": "데이터 벤더 2곳 비교, 07-25까지 계약 선택",
      "결정사항": ["시장 데이터 컷 기준 08-05"],
      "액션아이템": [
        {
          "작업": "벤더 비교표 제출",
          "기한": "2024-07-22",
          "담당자": "김민수"
        }
      ]
    }
  ],
  "personal_notes": [
    {
      "타입": "personal",
      "제목": "시장 데이터 벤더 비교표 작성 노트",
      "작성자": "김민수",
      "날짜": "2024-07-19",
      "프로젝트": "보상",
      "관련메일": ["2024-07-18 보상_킥오프"],
      "목표": ["벤더 비교표 제출 및 07-25 계약 선택 지원"],
      "참고자료": ["Vendor A, Vendor B 제안서"],
      "진행상태": {
        "TODO": ["로컬 보정 지표 비교"],
        "DOING": ["포지션 커버리지 표 정리"],
        "DONE": ["비용/납기/지원 채널 비교"]
      },
      "메모": "커버리지 차이는 기술 직군에서 뚜렷",
      "다음액션": [
        {
          "작업": "비교표 초안 회람",
          "기한": "2024-07-19"
        }
      ],
      "태그": ["보상", "벤더비교", "데이터"]
    }
  ]
}
```

## 예제 실행

```bash
# preprocessor_test.py 실행
python -m data_preprocess.preprocessor_test
```

## 주의사항

1. 파일 인코딩은 UTF-8을 기본으로 사용합니다.
2. 파일 타입 감지는 휴리스틱 기반으로 작동하므로 정확하지 않을 수 있습니다.
3. 파싱 실패 시 해당 파일은 건너뛰고 계속 진행됩니다.
4. 대용량 파일 처리 시 메모리 사용량을 고려하세요.
