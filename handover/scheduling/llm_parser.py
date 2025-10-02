"""LLM-based event extraction utilities."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from openai import AzureOpenAI

from .config import TODAY_STR, AZURE_CHAT_DEPLOYMENT


def build_instructions() -> str:
    return f"""
입력(JSON: emails/meetings/personal_notes)에서 '세분화된 프로젝트/주제'별 **단일 창구 이벤트(earliest~latest)**만 추출해 **유효한 JSON만** 출력하라.
- JSON 외 텍스트/코드블록 금지.
- 타임존: KST. 상대 날짜는 기준일 {TODAY_STR} 00:00(KST)로 절대화.

출력 스키마(고정):
{{ 
  "projects": [
    {{
      "project": "보상·예산가이드",
      "owners": ["이름1","이름2","이름3"],
      "events": [
        {{
          "title": "{{프로젝트}} | 창구",
          "start": "YYYY-MM-DD HH:MM",
          "deadline": "YYYY-MM-DD HH:MM"
        }}
      ]
    }}
  ]
}}

[세분화 규칙]
- '보상' 등 상위로 통일 금지. emails.subject 우선으로 "상위·구체" 구성:
  - 킥오프 → "보상·킥오프"
  - 예산가이드 → "보상·예산가이드"
  - 1차시뮬레이션 → "보상·1차시뮬레이션"
  - 확정안공유 → "보상·확정안"
  - 연간정책킥오프 → "보상·연간정책"
  - 시장데이터상황 → "보상·시장데이터"
- meetings.제목/배경, personal_notes.프로젝트/태그도 동일 기준으로 귀속.
- "이전 메일: YYYY-MM-DD", "후속"은 같은 **구체 토픽**으로 묶기.

[창구 산출 규칙]
- 고려하는 시각 소스(모두 포함하여 최소/최대 계산):
  1) emails 본문 "일정(안)" 항목들
  2) emails 본문 일반 문장 속 날짜/월-일
  3) meetings."일시"
  4) meetings."결정사항" 내 날짜/월-일
  5) meetings."액션아이템[].기한"
  6) personal_notes."날짜", "다음액션[].기한"
  7) emails 헤더 date(본문에 일정 항목이 전혀 없을 때만 보조)
- earliest = 위 모든 시각의 **최소**, latest = **최대**.
- 시간이 없는 날짜는:
  - 시작계열 → 09:00
  - 마감계열 → 23:59
- "MM-DD"는 같은 레코드의 절대 연도를 상속. 없으면 기준일 연도 사용.
- 파싱 실패 항목은 제외.
- 같은 이메일의 "일정(안)" 블록에 포함된 항목들은 모두 동일 주제로 간주.

[owners 추출]
- emails: sender+recipients+cc 표시명, meetings: 참석자+작성자, personal_notes: 작성자.
- 중복 제거 후 등장빈도 상위 3명, 이름 오름차순.

[정렬/제한]
- projects는 events[0].start 오름차순 정렬.
- 각 project의 events는 반드시 1개만 포함.
- 스키마 외 필드 금지. 비어 있으면 "projects": []만 출력.
"""


JSON_INSTRUCTIONS = build_instructions()


def read_input_txt(file_path: Path) -> List[Tuple[str, str]]:
    items: List[Tuple[str, str]] = []
    file = Path(file_path)
    try:
        if not file.exists():
            raise FileNotFoundError(f"파일이 없습니다: {file.resolve()}")
        text = file.read_text(encoding="utf-8", errors="ignore")
        if text.strip():
            items.append((file.name, text))
    except Exception as exc:
        print(f"[warn] {file_path} 읽기 실패: {exc}")
    return items


def _clean_json_payload(raw: str) -> str:
    raw = raw.replace("\n", " ").replace("\r", "")
    raw = re.sub(r"\s+", " ", raw)
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)
    if not raw.startswith("{"):
        raw = raw[raw.find("{"):] if "{" in raw else "{}"
    if not raw.endswith("}"):
        raw = raw[:raw.rfind("}")+1] if "}" in raw else "{}"
    return raw


def extract_events_json_per_file(client: AzureOpenAI, text: str) -> Dict[str, Any]:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            messages = [
                {
                    "role": "system",
                    "content": "당신은 신뢰성 높은 일정 파서입니다. 반드시 유효한 JSON만 출력합니다."
                },
                {
                    "role": "user",
                    "content": JSON_INSTRUCTIONS + "\n\n텍스트:\n" + text
                },
            ]

            response = client.chat.completions.create(
                model=AZURE_CHAT_DEPLOYMENT,
                messages=messages,
                temperature=0.0,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            if not getattr(response, "choices", None):
                raise ValueError("빈 응답을 수신했습니다.")

            raw = response.choices[0].message.content.strip()
            cleaned = _clean_json_payload(raw)
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict) and "projects" in parsed:
                    return parsed
                return {"projects": []}
            except json.JSONDecodeError:
                if attempt == max_retries - 1:
                    print("[info] JSON 파싱 실패 (마지막 시도)")
                    return {"projects": []}
        except Exception as exc:
            if attempt == max_retries - 1:
                print(f"[info] API 호출 실패: {exc}")
                return {"projects": []}
    return {"projects": []}
