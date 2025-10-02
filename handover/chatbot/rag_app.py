# rag_app.py (BAR-TONG ONLY)
# ------------------------------------------------------------
# Single-file RAG app using ONLY the original "바통이" persona.
# Features kept:
#   - Temporal normalizer (LLM JSON + validation + fallback)
#   - Time-first retrieval, then semantic re-rank
#   - Markdown stripping for context/answers
# Removed:
#   - General persona/mode and intent router
# ------------------------------------------------------------

import os
import json
import html
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re

import numpy as np
import faiss
from openai import AzureOpenAI
import streamlit as st


# =========================
#        Persona (KEEP)
# =========================
SYSTEM_PERSONA = """
당신은 '바통이'입니다. 인수인계 전문 AI 어시스턴트로, 업무 인계를 돕는 것이 목적입니다.

## 바통이의 정체성:
- 5년차 선임 직원의 따뜻함과 전문성을 갖춘 AI
- 이름의 의미: 릴레이에서 다음 주자에게 전달하는 '바통'처럼, 업무를 안전하게 인계하는 역할
- 후배를 진심으로 아끼고, 성공적인 업무 적응을 돕고 싶어함

## 바통이의 대화 스타일:
- 존댓말 사용 (예: "~입니다", "~해요", "~하시면 됩니다")
- 따뜻하고 격려하는 톤 (예: "잘 물어보셨어요", "천천히 하나씩 익혀가시면 됩니다")
- 구체적이고 실용적인 정보 제공 (날짜, 시간, 담당자명 등 정확히 명시)
- 필요시 팁이나 주의사항 추가 (예: "💡 참고로~", "⚠️ 주의할 점은~")
- 공감과 이해를 표현 (예: "처음엔 복잡해 보일 수 있는데~", "그 부분 궁금하실 만해요")

## 답변 원칙:
1. **자기소개 질문 대응**: "넌 누구야?", "누구세요?", "소개해줘", "뭐 하는 애야?" 처럼 바통이 자신에 대해 묻는 질문에만 자기소개를 합니다. 업무 관련 질문에는 절대 자기소개를 하지 않습니다.
2. **정확성 우선**: 제공된 인수인계 문서 내용만을 근거로 답변합니다.
3. **투명성**: 문서에 없는 내용은 솔직하게 "해당 내용은 제공된 자료에서 확인되지 않네요. 추가로 확인이 필요할 것 같습니다"라고 답변합니다.
4. **구체성**: 일정, 담당자, 절차 등은 가능한 한 구체적으로 안내합니다.
5. **시간 표기**: 모든 시간은 KST(한국 표준시)로 명시합니다.
6. **자연스러운 대화**: 이메일이나 보고서가 아닌, 선배가 후배에게 설명하듯 자연스럽게 답변합니다.
7. **핵심 집중**: 업무 질문에는 불필요한 인사말과 자기소개를 생략하고 질문에 대한 답변만 제공합니다.

## 답변 형식:
- 간단한 질문: 2-3문장으로 간결하게
- 복잡한 질문: 단계별로 구조화하여 설명
- 다수의 정보: 번호나 구분을 활용해 명확하게 정리
- 추가 정보가 도움될 경우: 자연스럽게 팁 형태로 추가

당신은 단순한 정보 전달자가 아니라, 후배의 성공적인 업무 적응을 진심으로 바라는 선임입니다.
"""

INDEX_PATH = "./data/rag_store/index.faiss"
META_PATH  = "./data/rag_store/meta.jsonl"


# =========================
#            Utils
# =========================
def _norm(a: np.ndarray) -> np.ndarray:
    return a / (np.linalg.norm(a, axis=-1, keepdims=True) + 1e-12)

def get_azure_client() -> AzureOpenAI:
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_ver = os.getenv("AZURE_OPENAI_API_VERSION")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not api_key or not api_ver or not endpoint:
        raise RuntimeError(
            "Azure OpenAI env vars missing. "
            "Set AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_ENDPOINT in .env"
        )
    return AzureOpenAI(api_key=api_key, api_version=api_ver, azure_endpoint=endpoint)

def load_rag_store(index_path: str, meta_path: str):
    if not Path(index_path).exists():
        raise FileNotFoundError(f"FAISS index not found: {index_path}")
    if not Path(meta_path).exists():
        raise FileNotFoundError(f"Metadata JSONL not found: {meta_path}")
    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = [json.loads(line) for line in f]
    return index, meta

def embed_text(client: AzureOpenAI, text: str) -> np.ndarray:
    emb_deploy = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    if not emb_deploy:
        raise RuntimeError("AZURE_OPENAI_EMBEDDING_DEPLOYMENT is not set in .env")
    vec = client.embeddings.create(model=emb_deploy, input=text).data[0].embedding
    return np.array(vec, dtype="float32")

def retrieve_topk(index, meta, q_vec: np.ndarray, k: int = 6) -> List[Tuple[float, Dict]]:
    q = _norm(q_vec).reshape(1, -1)
    scores, idxs = index.search(q, k)
    results = []
    for s, i in zip(scores[0], idxs[0]):
        if int(i) >= 0:
            results.append((float(s), meta[int(i)]))
    return results

def build_context(snippets: List[Tuple[float, Dict]]) -> str:
    """
    검색된 문서 조각들을 컨텍스트로 조합 — 마크다운 기호 제거(바통이 규칙 유지)
    """
    lines = []
    for score, m in snippets:
        src = f"{Path(m['source']).name}#chunk{m['chunk_index_in_doc']}"
        text = m['text']
        text = text.replace('**', '').replace('*', '').replace('##', '').replace('#', '')
        lines.append(f"[{src}] {text}")
    return "\n\n".join(lines)

def _render_msg(role: str, content: str):
    """Streamlit-safe message bubble renderer"""
    safe = html.escape(content).replace("\n", "<br>")
    row_cls = "user" if role == "user" else "assistant"
    bub_cls = "user" if role == "user" else "assistant"
    st.markdown(
        f'<div class="msg-row {row_cls}"><div class="bubble {bub_cls}">{safe}</div></div>',
        unsafe_allow_html=True
    )


# =========================
#  Temporal Normalizer
# =========================
KST = ZoneInfo("Asia/Seoul")

def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt.isoformat(timespec="seconds")

def _start_of_day(dt: datetime) -> datetime:
    return dt.astimezone(KST).replace(hour=0, minute=0, second=0, microsecond=0)

def _end_of_day(dt: datetime) -> datetime:
    return dt.astimezone(KST).replace(hour=23, minute=59, second=59, microsecond=999000)

def _parse_iso(s: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        return dt.astimezone(KST)
    except Exception:
        return None

def _detect_until_ko(query: str) -> bool:
    return "까지" in query

WEEKDAY_MAP_KO = {"월":0,"화":1,"수":2,"목":3,"금":4,"토":5,"일":6}
WEEKDAY_MAP_EN = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,"friday":4,"saturday":5,"sunday":6}
_DUR_RE = re.compile(r"(?P<num>\d+)\s*(?P<unit>주|주일|일|개월|달)\s*(?:뒤|후)?")

def _count_dada_next(s: str) -> int:
    m = re.search(r"(다+)?다음주", s)
    if not m:
        return -1
    prefix = m.group(1) or ""
    return len(prefix)

def _this_week_monday(now: datetime) -> datetime:
    return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=KST)

def _nth_weekday_from(now: datetime, weekday: int, n_weeks: int) -> datetime:
    base = _this_week_monday(now)
    target = (base + timedelta(weeks=n_weeks, days=weekday)).replace(hour=0, minute=0, second=0, microsecond=0)
    if n_weeks == 0 and target.date() < now.date():
        target += timedelta(weeks=1)
    return target

def _fallback_resolve(query: str, now_kst: datetime) -> datetime | None:
    q_en = query.lower()
    q_ko = " ".join(query.split())

    n_weeks = None
    if ("이번주" in q_ko) or ("이번 주" in q_ko):
        n_weeks = 0
    elif ("다음주" in q_ko) or ("다음 주" in q_ko):
        n_weeks = 1
    else:
        n_das = _count_dada_next(q_ko)
        if n_das >= 0:
            n_weeks = 1 + n_das

    if n_weeks is not None:
        for k, wd in WEEKDAY_MAP_KO.items():
            if (k in q_ko) or ((k + "요일") in q_ko):
                return _nth_weekday_from(now_kst, wd, n_weeks)

    for k, wd in WEEKDAY_MAP_KO.items():
        if (k + "요일") in q_ko:
            return _nth_weekday_from(now_kst, wd, 0)

    m = _DUR_RE.search(q_ko)
    if m:
        num = int(m.group("num"))
        unit = m.group("unit")
        if unit in ("주", "주일"):
            return now_kst + timedelta(weeks=num)
        elif unit == "일":
            return now_kst + timedelta(days=num)
        elif unit in ("개월", "달"):
            return now_kst + timedelta(days=30 * num)

    m = re.search(r"in\s+(\d+)\s*(day|days|week|weeks|month|months)", q_en)
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        if "week" in unit:
            return now_kst + timedelta(weeks=num)
        elif "day" in unit:
            return now_kst + timedelta(days=num)
        elif "month" in unit:
            return now_kst + timedelta(days=30 * num)

    m = re.search(r"\b(this|upcoming|coming|next)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", q_en)
    if m:
        n = 0 if m.group(1) in ("this", "upcoming", "coming") else 1
        wd = WEEKDAY_MAP_EN[m.group(2)]
        return _nth_weekday_from(now_kst, wd, n)

    return None

def _get_chat_deploy_from_env() -> str:
    deploy = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    if not deploy:
        raise RuntimeError("AZURE_OPENAI_CHAT_DEPLOYMENT not set")
    return deploy

def _try_parse_json(raw: str) -> Dict[str, Any] | None:
    try:
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = re.sub(r"^json", "", raw.strip(), flags=re.IGNORECASE).strip()
        return json.loads(raw)
    except Exception:
        return None

def normalize_interval_via_llm(
    client: AzureOpenAI,
    query: str,
    now_kst: datetime,
    tz_name: str = "Asia/Seoul",
    point_window_days: int = 3
) -> Any:
    """
    Ask LLM for strict JSON → validate/repair → fallback parser → safe default.
    Returns: {kind, tz, anchor_date, start, end, derived_from, confidence}
    """
    anchor_date = now_kst.strftime("%Y-%m-%d")
    system = (
        "You convert Korean/English time expressions about tasks into a strict JSON interval in Asia/Seoul (KST). "
        "Correct typos/variants (e.g., '다다다다음주'). Do NOT include prose. JSON only."
    )
    user = f"""Text: "{query}"
Today (KST): {anchor_date}
Timezone: {tz_name}

Return JSON ONLY with fields:
kind: "deadline_range" | "point_window" | "absolute_range"
tz: "{tz_name}"
anchor_date: YYYY-MM-DD
start: ISO 8601 datetime with KST timezone
end: ISO 8601 datetime with KST timezone
derived_from: short string
confidence: 0..1

Rules:
- If the text includes a deadline like '~까지', set kind='deadline_range' and set start=today 00:00 KST, end=end-of-day(target).
- If it's a point question (e.g., '1주뒤는?'), set kind='point_window' with start=target-3d 00:00, end=target+3d 23:59.
- If the text names a whole span (e.g., '이번주'), set kind='absolute_range' for that span.
- Always fill ALL fields. Do not add extra keys.
"""
    resp = client.chat.completions.create(
        model=_get_chat_deploy_from_env(),
        temperature=0.0,
        max_tokens=300,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    raw = (resp.choices[0].message.content or "").strip()
    data = _try_parse_json(raw)

    interval = _validate_and_repair(data, query, now_kst, tz_name, point_window_days)
    if interval:
        return interval

    # repair pass
    err_reason = "Invalid or incomplete JSON for required fields."
    repair_user = f"""The previous JSON failed validation: {err_reason}
Fix only the fields so that:
- tz == "{tz_name}"
- start/end are ISO datetimes with timezone and start <= end
- anchor_date == "{anchor_date}"
- kind in ["deadline_range","point_window","absolute_range"]
- confidence in [0,1]

Original text: "{query}"
Today (KST): {anchor_date}
Timezone: {tz_name}

Return JSON only."""
    resp2 = client.chat.completions.create(
        model=_get_chat_deploy_from_env(),
        temperature=0.0,
        max_tokens=200,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": repair_user}],
    )
    raw2 = (resp2.choices[0].message.content or "").strip()
    data2 = _try_parse_json(raw2)
    interval = _validate_and_repair(data2, query, now_kst, tz_name, point_window_days)
    if interval:
        return interval

    # fallback parser
    target = _fallback_resolve(query, now_kst)
    if target:
        if _detect_until_ko(query):
            start = _start_of_day(now_kst)
            end = _end_of_day(target)
            return {
                "kind": "deadline_range",
                "tz": tz_name,
                "anchor_date": anchor_date,
                "start": _iso(start),
                "end": _iso(end),
                "derived_from": "fallback_parser_until",
                "confidence": 0.4,
            }
        else:
            start = _start_of_day(target - timedelta(days=point_window_days))
            end = _end_of_day(target + timedelta(days=point_window_days))
            return {
                "kind": "point_window",
                "tz": tz_name,
                "anchor_date": anchor_date,
                "start": _iso(start),
                "end": _iso(end),
                "derived_from": "fallback_parser_point",
                "confidence": 0.35,
            }

    # absolute safe default (next 14 days)
    start = _start_of_day(now_kst)
    end = _end_of_day(now_kst + timedelta(days=14))
    return {
        "kind": "absolute_range",
        "tz": tz_name,
        "anchor_date": anchor_date,
        "start": _iso(start),
        "end": _iso(end),
        "derived_from": "absolute_fallback_next_14d",
        "confidence": 0.2,
    }

def _validate_and_repair(
    data: Dict[str, Any] | None,
    query: str,
    now_kst: datetime,
    tz_name: str,
    point_window_days: int
) -> Dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    required = ["kind", "tz", "anchor_date", "start", "end", "confidence"]
    if any(k not in data for k in required):
        return None

    kind = data.get("kind")
    if kind not in ("deadline_range", "point_window", "absolute_range"):
        return None

    tz = data.get("tz")
    if tz != tz_name:
        tz = tz_name

    anchor_date = data.get("anchor_date")
    try:
        datetime.strptime(anchor_date, "%Y-%m-%d")
    except Exception:
        anchor_date = now_kst.strftime("%Y-%m-%d")

    start_dt = _parse_iso(data.get("start", ""))
    end_dt   = _parse_iso(data.get("end", ""))
    if not start_dt or not end_dt:
        return None

    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    if _detect_until_ko(query) and start_dt.date() > now_kst.date():
        start_dt = _start_of_day(now_kst)  # ensure deadline starts today

    try:
        conf = float(data.get("confidence", 0.5))
    except Exception:
        conf = 0.5
    conf = max(0.0, min(1.0, conf))

    return {
        "kind": kind,
        "tz": tz,
        "anchor_date": anchor_date,
        "start": _iso(start_dt),
        "end": _iso(end_dt),
        "derived_from": str(data.get("derived_from", "llm")),
        "confidence": conf
    }


# =========================
#   Time-first Retrieval
# =========================
def _parse_meta_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=KST)

def _snippets_in_range(meta: List[Dict], start: datetime, end: datetime, limit: int = 50) -> List[Tuple[float, Dict]]:
    rows = []
    for m in meta:
        try:
            dt = _parse_meta_dt(m.get("date", "1970-01-01 00:00"))
        except Exception:
            continue
        if start <= dt <= end:
            rows.append((1.0, m, dt))
    rows.sort(key=lambda x: x[2])  # earliest first
    return [(s, m) for (s, m, _) in rows[:limit]]

def _merge_dedup_time_first(primary: List[Tuple[float, Dict]], secondary: List[Tuple[float, Dict]], max_total: int = 40) -> List[Tuple[float, Dict]]:
    seen = set()
    merged: List[Tuple[float, Dict]] = []
    for lst in (primary, secondary):
        for s, m in lst:
            key = (m.get("source"), m.get("chunk_index_in_doc"))
            if key in seen:
                continue
            seen.add(key)
            merged.append((s, m))
            if len(merged) >= max_total:
                return merged
    return merged

def temporal_rerank(hits: List[Tuple[float, Dict]], target_date: datetime | None, window_days: int = 7):
    if target_date is None:
        return hits
    filtered = []
    for s, m in hits:
        try:
            dt = _parse_meta_dt(m.get("date", "1970-01-01 00:00"))
        except Exception:
            continue
        delta = abs((dt.date() - target_date.date()).days)
        if delta <= window_days:
            filtered.append((s, m, delta))
    if filtered:
        filtered.sort(key=lambda x: (-x[0], x[2]))
        return [(s, m) for (s, m, _) in filtered]
    scored = []
    for s, m in hits:
        try:
            dt = _parse_meta_dt(m.get("date", "1970-01-01 00:00"))
            delta = abs((dt.date() - target_date.date()).days)
        except Exception:
            delta = 9999
        scored.append((s, m, delta))
    scored.sort(key=lambda x: (-x[0], x[2]))
    return [(s, m) for (s, m, _) in scored]


# =========================
#            RAG
# =========================
def build_user_prompt(question: str, context: str, range_hint: str | None = None) -> str:
    note = f"\n검색·정렬은 이 기간을 우선했어요: {range_hint} (KST)." if range_hint else ""
    return f"""
{SYSTEM_PERSONA}

다음은 인수인계 문서에서 검색된 관련 내용입니다:

{context}

질문: {question}{note}

답변 지침:
1. 질문 유형 판단하기:
   A. 바통이 자신에 대한 질문 (예: "너 누구야?", "소개해줘", "뭐 물어보면 돼?", "어떤 질문 할 수 있어?")
      → 자기소개 및 기능 설명을 해주세요. 이때는 보기 쉽게 마크다운을 사용해도 좋습니다.
      
   B. 업무 관련 질문 (예: "내가 당장 해야 할 일?", "담당자가 누구야?", "일정이 어떻게 돼?")
      → 위 문서 내용을 바탕으로 답변하되, 절대 자기소개를 포함하지 마세요.
      → [중요] 답변에 마크다운 기호를 절대 사용하지 마세요. **, *, #, - 같은 기호 없이 순수한 텍스트로만 작성하세요.

2. 업무 질문 답변 규칙:
   - 위 문서 내용만을 기반으로 정확하게 답변하세요
   - 자기소개나 "저는 바통이예요" 같은 문구는 절대 포함하지 마세요
   - 문서에 정보가 없으면 "해당 내용은 제공된 자료에서 확인되지 않네요. 추가로 확인이 필요할 것 같습니다"라고 답변하세요
   - 날짜, 시간, 담당자 등은 정확히 명시하세요 (시간은 KST 기준)
   - 선배가 후배에게 설명하듯 따뜻하고 자연스럽게 답변하세요
   - 도움이 될 만한 팁이 있다면 자연스럽게 추가하세요
""".strip()

def chat_with_context(client: AzureOpenAI, system_prompt: str, user_prompt: str) -> str:
    chat_deploy = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    if not chat_deploy:
        raise RuntimeError("AZURE_OPENAI_CHAT_DEPLOYMENT is not set in .env")
    resp = client.chat.completions.create(
        model=chat_deploy,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=1000,
    )
    answer = (resp.choices[0].message.content or "").strip()
    # 마크다운 기호 강제 제거 (바통이 규칙 유지)
    answer = answer.replace('**', '').replace('##', '')
    return answer


class RAGChatbot:
    """RAG 챗봇의 비즈니스 로직을 담당하는 클래스 (바통이 only)"""
    
    def __init__(self):
        self.client = None
        self.index = None
        self.meta = None
        self._initialized = False
    
    def initialize(self) -> Tuple[bool, str]:
        try:
            if not os.getenv("AZURE_OPENAI_API_KEY"):
                return False, "❌ AZURE_OPENAI_API_KEY가 설정되지 않았습니다. .env를 확인하세요."
            self.client = get_azure_client()
            self.index, self.meta = load_rag_store(INDEX_PATH, META_PATH)
            self._initialized = True
            return True, "✅ 바통이가 준비되었습니다! 궁금한 점을 편하게 물어보세요."
        except FileNotFoundError as e:
            return False, f"❌ {str(e)}\n💡 먼저 임베딩 스크립트를 실행해 index.faiss / meta.jsonl을 생성하세요."
        except Exception as e:
            return False, f"❌ 초기화 실패: {e}"
    
    def ask(self, query: str, k: int = 6) -> Dict[str, Any]:
        if not self._initialized:
            return {'answer': None, 'sources': [], 'error': 'RAG 시스템이 초기화되지 않았습니다.'}
        try:
            now_kst = datetime.now(KST)

            # 1) Temporal normalization
            interval = normalize_interval_via_llm(
                client=self.client,
                query=query,
                now_kst=now_kst,
                tz_name="Asia/Seoul",
                point_window_days=3,
            )
            start_dt = datetime.fromisoformat(interval["start"]).astimezone(KST)
            end_dt   = datetime.fromisoformat(interval["end"]).astimezone(KST)
            range_hint = f"{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}"

            # 2) Time-first selection
            time_hits = _snippets_in_range(self.meta, start_dt, end_dt, limit=50)

            # 3) Semantic retrieval + temporal rerank
            q_vec = embed_text(self.client, query)
            sem_hits = retrieve_topk(self.index, self.meta, q_vec, k=k)
            target_for_rerank = start_dt + (end_dt - start_dt) / 2
            sem_hits = temporal_rerank(sem_hits, target_for_rerank, window_days=7)

            # 4) Merge
            hits = _merge_dedup_time_first(time_hits, sem_hits, max_total=40)

            # 5) If no usable hits → persona-consistent fallback
            if not hits:
                return {
                    'answer': "해당 내용은 제공된 자료에서 확인되지 않네요. 추가로 확인이 필요할 것 같습니다",
                    'sources': [],
                    'error': None
                }

            # 6) Build context and answer
            context = build_context(hits)
            user_prompt = build_user_prompt(query, context, range_hint=range_hint)
            answer = chat_with_context(self.client, SYSTEM_PERSONA, user_prompt)

            # 7) Sources for UI/debug
            sources = []
            for score, meta in hits:
                try:
                    src_dt = _parse_meta_dt(meta.get("date", "1970-01-01 00:00")).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    src_dt = meta.get("date", None)
                sources.append({
                    'filename': Path(meta['source']).name,
                    'chunk_index': meta['chunk_index_in_doc'],
                    'score': score,
                    'date': src_dt
                })

            # 8) Last safety: empty answer → minimal, persona-safe fallback
            if not answer or answer.strip() == "":
                answer = "해당 내용은 제공된 자료에서 확인되지 않네요. 추가로 확인이 필요할 것 같습니다"

            return {'answer': answer, 'sources': sources, 'error': None}

        except Exception as e:
            return {'answer': None, 'sources': [], 'error': f"오류가 발생했습니다: {e}\n궁금한 점이 있으시면 다시 물어봐 주세요."}
    
    def is_initialized(self) -> bool:
        return self._initialized
    
    def get_persona_info(self) -> Dict[str, str]:
        return {
            'name': '바통이',
            'role': '인수인계 전문 AI 어시스턴트',
            'description': '5년차 선임의 따뜻함으로 업무 인계를 돕습니다',
            'greeting': '안녕하세요! 저는 바통이예요. 업무 인수인계를 도와드릴게요. 궁금한 점을 편하게 물어보세요! 😊'
        }
