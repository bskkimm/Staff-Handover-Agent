# extract_schedule_batch.py
# -*- coding: utf-8 -*-

import os, json, re, glob, uuid, time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import pandas as pd
from openai import AzureOpenAI

# ===== 0) 설정 =====
load_dotenv()
MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT", "aicore-gpt4o")
DATA_DIR = "/home/hyundo/project1/Staff-Handover-Agent/data"
OUT_DIR = os.getenv("OUTPUT_FOLDER", "./output")
MD_DIR = os.path.join(OUT_DIR, "markdown")
OUT_MD = os.getenv("OUT_MD", os.path.join(OUT_DIR, "combined_schedule.md"))
OUT_MONTH_DIR = os.getenv("OUT_MONTH_DIR", os.path.join(OUT_DIR, "out_cal_bars"))
os.makedirs(MD_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

# ===== 1) 프롬프트 =====
SYSTEM_PROMPT = (
    "당신은 전처리 데이터 해석 전문가입니다. 이메일/회의록/개인노트에서 실제 '액션'을 식별합니다. "
    "각 액션은 시작=가장 이른 시각, 종료=가장 늦은 시각으로 합칩니다. "
    "모든 날짜·시간은 Asia/Seoul 기준 ISO8601(YYYY-MM-DD HH:MM) 24시간 형식. "
    "시간이 없으면 09:00과 18:00을 가정합니다."
)

USER_TMPL = """다음 전처리 텍스트에서 액션과 일정을 추출하세요.

요구사항:
1) 하나의 액션이 여러 출처에서 반복되면 시작=최초, 종료=최후.
2) 날짜만 있으면 시작 09:00, 종료 18:00.
3) 반드시 JSON 하나만 출력. 마크다운/코드블록 금지.
4) 스키마:
{{
  "title": "<문서 요약 제목>",
  "actions": [
    {{
      "action": "<액션명>",
      "start": "YYYY-MM-DD HH:MM",
      "end":   "YYYY-MM-DD HH:MM",
      "assignees": ["이름"],
      "source_refs": ["근거 요약"],
      "notes": "<선택>"
    }}
  ]
}}

전처리 텍스트:
{sample}
"""

# ===== 2) JSON 파서 =====
def _parse_json_str(s: str) -> Dict[str, Any]:
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", s, re.S)
    raw = m.group(1) if m else s
    raw = raw.strip()
    raw = re.sub(r"\s*(?:php|코드\s*복사)\s*$", "", raw, flags=re.I)
    return json.loads(raw)

# ===== 3) LLM 호출(재시도) =====
def extract_actions_from_text(text: str, retries: int = 3, backoff: float = 1.5) -> Dict[str, Any]:
    prompt = USER_TMPL.format(sample=text)
    last_err: Optional[Exception] = None
    for i in range(retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1800,
            )
            content = resp.choices[0].message.content
            return _parse_json_str(content)
        except Exception as e:
            last_err = e
            time.sleep(backoff ** i)
    raise last_err if last_err else RuntimeError("LLM 호출 실패")

# ===== 4) 마크다운(개별 파일) =====
def actions_to_markdown(title: str, actions: List[Dict[str, Any]]) -> str:
    lines = [f"# {title}".strip()]
    for a in actions:
        lines.append(f"## {a.get('action','(미정)')}")
        lines.append(f"- 일정: {a.get('start','')} - {a.get('end','')}")
        if a.get("assignees"): lines.append(f"- 담당: {', '.join(a['assignees'])}")
        if a.get("notes"): lines.append(f"- 메모: {a['notes']}")
        if a.get("source_refs"): lines.append(f"- 근거: " + " / ".join(a["source_refs"][:3]))
        lines.append("")
    return "\n".join(lines).strip() + "\n"

# ===== 5) 정규화 =====
def _norm_dt(s: Optional[str]) -> Optional[str]:
    if not s: return None
    s = s.replace("T", " ").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s + " 09:00"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}\s+\d{2}", s):
        return s + ":00"
    return s

def normalize_actions(doc_title: str, file_name: str, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    today = datetime.today().strftime("%Y-%m-%d")
    out = []
    for a in actions:
        action = (a.get("action") or "").strip() or "(미정 액션)"
        start = _norm_dt(a.get("start")) or f"{today} 09:00"
        end   = _norm_dt(a.get("end"))   or f"{today} 18:00"
        out.append({
            "uid": str(uuid.uuid4()),
            "doc_title": doc_title,
            "source_file": file_name,
            "action": action,
            "start": start,
            "end": end,
            "assignees": ", ".join(a.get("assignees", [])),
            "notes": a.get("notes", ""),
        })
    return out

# ===== 6) 배치 처리 =====
def read_all_txt(data_dir: str) -> List[str]:
    paths = glob.glob(os.path.join(data_dir, "**", "*.txt"), recursive=True)
    return sorted(paths)

def process_all_txt() -> pd.DataFrame:
    all_events: List[Dict[str, Any]] = []
    paths = read_all_txt(DATA_DIR)
    if not paths:
        print(f"[info] TXT 없음: {os.path.abspath(DATA_DIR)}")
    for path in paths:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        try:
            result = extract_actions_from_text(text)
            title = result.get("title") or os.path.basename(path)
            actions = result.get("actions", []) or []
        except Exception as e:
            print(f"[warn] LLM 파싱 실패: {path} -> {e}")
            title, actions = os.path.basename(path), []
        md = actions_to_markdown(title, actions)
        md_name = os.path.splitext(os.path.basename(path))[0] + ".md"
        with open(os.path.join(MD_DIR, md_name), "w", encoding="utf-8") as f:
            f.write(md)
        all_events.extend(normalize_actions(title, os.path.basename(path), actions))
    if not all_events:
        return pd.DataFrame(columns=["uid","doc_title","source_file","action","start","end","assignees","notes"])
    df = pd.DataFrame(all_events).sort_values(["start","end","action"])
    df = df.drop_duplicates(subset=["action","start","end"])
    return df

# ===== 7) combined MD 생성(Bar Viz용 포맷) =====
def build_combined_md_for_bars(df: pd.DataFrame) -> str:
    """
    desk_calendar_bar_viz.render_all_months_bars 가 기대하는 형태:
    ## 헤더
    Start: YYYY-MM-DD HH:MM (KST)
    Deadline: YYYY-MM-DD HH:MM (KST)
    Source: foo, bar ...
    """
    if df.empty:
        return "# 인수인계 일정 요약\n\n"
    # 그룹: (action, assignees)
    df2 = df.copy()
    df2["assignees"] = df2["assignees"].fillna("").astype(str)
    # 날짜 문자열 -> datetime 정렬용
    def to_dt(s):
        try:
            return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")
        except Exception:
            return None
    df2["_st"] = df2["start"].map(to_dt)
    df2["_ed"] = df2["end"].map(to_dt)
    blocks = ["# 인수인계 일정 요약", ""]
    for (act, own), g in df2.groupby(["action","assignees"]):
        g = g.sort_values("_st")
        st = g["_st"].dropna().min()
        ed = g["_ed"].dropna().max() or st
        start_s = st.strftime("%Y-%m-%d %H:%M") if st else ""
        end_s   = ed.strftime("%Y-%m-%d %H:%M") if ed else start_s
        owners_str = own.strip()
        title = f"## {act} ({owners_str})" if owners_str else f"## {act}"
        sources = ", ".join(sorted(set(g["source_file"].tolist())))
        blocks += [title, f"Start: {start_s} (KST)", f"Deadline: {end_s} (KST)", f"Source: {sources}", ""]
    return "\n".join(blocks)

# ===== 8) viz 연동: render_all_months_bars 고정 사용 =====
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

# ===== 9) main =====
def main():
    df = process_all_txt()
    out_csv = os.path.join(OUT_DIR, "events.csv")
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"[ok] 통합 CSV 저장: {out_csv}")
    print(f"[ok] 마크다운 폴더: {os.path.abspath(MD_DIR)}")

    # combined MD 생성 후 저장
    combined_md = build_combined_md_for_bars(df)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(combined_md)
    print(f"[ok] Combined Markdown 저장: {OUT_MD}")

    # 월별 바 차트 생성
    send_to_viz_with_bars(OUT_MD, OUT_MONTH_DIR)

if __name__ == "__main__":
    main()
