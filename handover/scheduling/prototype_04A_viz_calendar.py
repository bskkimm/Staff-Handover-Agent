# /home/hyundo/project1/Staff-Handover-Agent/handover/scheduling/extract_schedule_batch.py
# -*- coding: utf-8 -*-

import os, re, glob, uuid, time, json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import pandas as pd
from openai import AzureOpenAI

# ===== 0) 경로/설정 =====
load_dotenv()

SCHED_DIR = "/home/hyundo/project1/Staff-Handover-Agent/handover/scheduling"
DATA_DIR = os.getenv("INPUT_DIR", "/home/hyundo/project1/Staff-Handover-Agent/data")

OUT_DIR = os.path.join(SCHED_DIR, "output")
MD_DIR = os.path.join(OUT_DIR, "markdown")       # LLM이 만든 개별 MD 저장
LLM_MD_DIR = os.path.join(OUT_DIR, "llm_md_raw") # 원문 MD 그대로 저장(동일하지만 원문 보관용)
OUT_MD = os.path.join(OUT_DIR, "combined_schedule.md")
OUT_MONTH_DIR = os.path.join(OUT_DIR, "out_cal_bars")
for d in [OUT_DIR, MD_DIR, LLM_MD_DIR, OUT_MONTH_DIR]:
    os.makedirs(d, exist_ok=True)

MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT", "aicore-gpt4o")
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

# ===== 1) 프롬프트 =====
SYSTEM_PROMPT = (
    "당신은 전처리된 인수인계 문서에서 액션 일정을 추출해 깔끔한 마크다운을 작성하는 전문가입니다. "
    "가능한 한 구체적인 날짜와 시간을 사용합니다. 날짜만 있으면 시작 09:00, 종료 18:00(Asia/Seoul). "
    "출력은 마크다운 본문만. 코드블록/설명/접두사 금지."
)

USER_TMPL = """다음 인수인계 문서 전처리한 내용을 바탕으로 일정을 추출하고 해당 액션에 맞게 마크다운 형식으로 정리해주세요.

**요구사항:**
1. 제목은 # 으로 시작
2. 액션별로 ## 사용
3. 하나의 액션에 가장 이른 시간을 시작 시간으로 설정
4. 하나의 액션에 가장 늦은 시간을 종료 시간으로 설정
5. 액션별로 시작시간-종료시간 형태로 일정 표기

**전처리된 데이터:**
{sample_data}

다음 구조로 작성해주세요:
- 제목
- 액션명
- 일정
"""

# ===== 2) 유틸 =====
DT_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DT_HOUR = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}$")
DT_FULL = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}$")

def _norm_dt(s: Optional[str]) -> Optional[str]:
    if not s: return None
    s = s.replace("T", " ").strip()
    if DT_FULL.fullmatch(s): return s
    if DT_HOUR.fullmatch(s): return s + ":00"
    if DT_DATE.fullmatch(s): return s + " 09:00"
    return s

def _ensure_pair(start: Optional[str], end: Optional[str]) -> Tuple[str, str]:
    today = datetime.today().strftime("%Y-%m-%d")
    s = _norm_dt(start) or f"{today} 09:00"
    e = _norm_dt(end)   or f"{today} 18:00"
    return s, e

# ===== 3) LLM 호출(마크다운 생성) =====
def llm_make_markdown(sample_text: str, retries: int = 3, backoff: float = 1.5) -> str:
    prompt = USER_TMPL.format(sample_data=sample_text)
    last_err: Optional[Exception] = None
    for i in range(retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role":"system","content":SYSTEM_PROMPT},
                          {"role":"user","content":prompt}],
                temperature=0.1,
                max_tokens=2000,
            )
            md = (resp.choices[0].message.content or "").strip()
            # 코드펜스 제거 방어
            if md.startswith("```"):
                md = re.sub(r"^```(?:markdown|md)?\n?","",md).rstrip("` \n")
            return md.strip()
        except Exception as e:
            last_err = e
            time.sleep(backoff ** i)
    raise last_err if last_err else RuntimeError("LLM 호출 실패")

# ===== 4) MD 파서 → events rows =====
# 기대 포맷:
# # 제목
# ## 액션명
# - 일정: YYYY-MM-DD HH:MM - YYYY-MM-DD HH:MM   또는  YYYY-MM-DD - YYYY-MM-DD
ACTION_H = re.compile(r"^##\s+(.*)\s*$")
TITLE_H  = re.compile(r"^#\s+(.*)\s*$", re.M)
SCHED_L  = re.compile(r"^-+\s*일정\s*[:：]\s*(.+)$")

def parse_md_to_events(md: str, source_file: str) -> Tuple[str, List[Dict[str, Any]]]:
    title_m = TITLE_H.search(md)
    title = title_m.group(1).strip() if title_m else source_file

    actions: List[Dict[str, Any]] = []
    current_action = None
    start = end = None

    lines = md.splitlines()
    for ln in lines:
        m_act = ACTION_H.match(ln.strip())
        if m_act:
            # flush 이전 액션
            if current_action:
                s, e = _ensure_pair(start, end)
                actions.append({"action": current_action, "start": s, "end": e})
            current_action = m_act.group(1).strip()
            start = end = None
            continue

        m_s = SCHED_L.match(ln.strip())
        if m_s and current_action:
            span = m_s.group(1).strip()
            # 구분자 " - " 또는 "-" 둘 다 허용
            # 우측에 추가 텍스트가 있어도 앞부분만 사용
            span = span.split("  ")[0]
            parts = [p.strip() for p in re.split(r"\s*-\s*", span, maxsplit=1)]
            if len(parts) == 2:
                start, end = parts[0], parts[1]
            elif len(parts) == 1:
                start, end = parts[0], parts[0]

    # flush last
    if current_action:
        s, e = _ensure_pair(start, end)
        actions.append({"action": current_action, "start": s, "end": e})

    # events rows로 변환
    rows: List[Dict[str, Any]] = []
    for a in actions:
        rows.append({
            "uid": str(uuid.uuid4()),
            "doc_title": title,
            "source_file": source_file,
            "action": a["action"],
            "start": a["start"],
            "end": a["end"],
            "assignees": "",
            "notes": "",
        })
    return title, rows

# ===== 5) 배치 처리 =====
def read_all_txt(data_dir: str) -> List[str]:
    return sorted(glob.glob(os.path.join(data_dir, "**", "*.txt"), recursive=True))

def process_all_txt() -> Tuple[pd.DataFrame, pd.DataFrame]:
    all_events: List[Dict[str, Any]] = []
    idx_rows: List[Dict[str, Any]] = []

    paths = read_all_txt(DATA_DIR)
    if not paths:
        print(f"[info] TXT 없음: {os.path.abspath(DATA_DIR)}")

    for path in paths:
        base = os.path.splitext(os.path.basename(path))[0]
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            sample = f.read()

        # 1) LLM MD 생성
        try:
            md = llm_make_markdown(sample)
        except Exception as e:
            print(f"[warn] LLM 실패: {path} -> {e}")
            md = f"# {os.path.basename(path)}\n"

        # 2) 원문/가공 MD 저장
        raw_path = os.path.join(LLM_MD_DIR, f"{base}.md")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(md + "\n")

        md_path = os.path.join(MD_DIR, f"{base}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md + "\n")

        # 3) MD 파싱 → 이벤트
        title, rows = parse_md_to_events(md, os.path.basename(path))
        all_events.extend(rows)

        # 4) 인덱스
        idx_rows.append({
            "source_file": os.path.basename(path),
            "title": title,
            "llm_md_file": os.path.relpath(raw_path, OUT_DIR),
            "markdown_file": os.path.relpath(md_path, OUT_DIR),
            "action_count": len(rows),
        })

    # DF 생성
    df_events = pd.DataFrame(all_events, columns=["uid","doc_title","source_file","action","start","end","assignees","notes"])
    if not df_events.empty:
        df_events = df_events.sort_values(["start","end","action"]).drop_duplicates(subset=["action","start","end"])

    df_index = pd.DataFrame(idx_rows, columns=["source_file","title","llm_md_file","markdown_file","action_count"])
    return df_events, df_index

# ===== 6) 종합 MD(바 차트용) =====
def build_combined_md_for_bars(df: pd.DataFrame) -> str:
    if df.empty:
        return "# 인수인계 일정 요약\n\n"
    df2 = df.copy()
    def to_dt(s):
        try: return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")
        except: return None
    df2["_st"] = df2["start"].map(to_dt)
    df2["_ed"] = df2["end"].map(to_dt)
    blocks = ["# 인수인계 일정 요약", ""]
    for act, g in df2.groupby("action"):
        g = g.sort_values("_st")
        st = g["_st"].dropna().min()
        ed = g["_ed"].dropna().max() or st
        s = st.strftime("%Y-%m-%d %H:%M") if st else ""
        e = ed.strftime("%Y-%m-%d %H:%M") if ed else s
        sources = ", ".join(sorted(set(g["source_file"].tolist())))
        blocks += [f"## {act}", f"Start: {s} (KST)", f"Deadline: {e} (KST)", f"Source: {sources}", ""]
    return "\n".join(blocks)

# ===== 7) viz 연동 =====
def send_to_viz_with_bars(md_path: str, out_dir: str):
    try:
        from desk_calendar_bar_viz import render_all_months_bars
    except ImportError:
        print("[viz] desk_calendar_bar_viz 모듈 없음 → combined MD만 생성")
        return
    try:
        os.makedirs(out_dir, exist_ok=True)
        render_all_months_bars(md_path, out_dir)
        print(f"[viz] render_all_months_bars 완료 → {out_dir}")
    except Exception as e:
        print(f"[viz] render_all_months_bars 실패: {e}")

# ===== 8) main =====
def main():
    df_events, df_index = process_all_txt()

    out_csv = os.path.join(OUT_DIR, "events.csv")
    df_events.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"[ok] 통합 CSV: {out_csv}")

    out_idx = os.path.join(OUT_DIR, "llm_index.csv")
    df_index.to_csv(out_idx, index=False, encoding="utf-8-sig")
    print(f"[ok] LLM 인덱스: {out_idx}")

    combined_md = build_combined_md_for_bars(df_events)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(combined_md)
    print(f"[ok] Combined Markdown: {OUT_MD}")

    send_to_viz_with_bars(OUT_MD, OUT_MONTH_DIR)

if __name__ == "__main__":
    main()
