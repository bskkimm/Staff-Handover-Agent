import os, json, re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import streamlit as st
from openai import AzureOpenAI

from handover.utils import get_uploaded_files_data


# -------------------- 환경 및 클라이언트 --------------------
KST = ZoneInfo("Asia/Seoul")
TODAY_STR = datetime.now(KST).strftime("%Y-%m-%d")

AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_CHAT_DEPLOY = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "aicore-gpt4o")

client = None
if AZURE_API_KEY and AZURE_ENDPOINT:
    client = AzureOpenAI(api_key=AZURE_API_KEY, api_version="2024-02-01", azure_endpoint=AZURE_ENDPOINT)


# -------------------- 프롬프트 --------------------
JSON_INSTRUCTIONS = f"""
다음 텍스트(이메일 또는 업무일지)에서 프로젝트와 일정 이벤트를 JSON으로만 출력하세요.
- JSON 외의 모든 텍스트 금지 (코드블록 금지).
- 날짜는 KST로 해석. 상대 날짜는 기준일 {TODAY_STR} (KST)을 기준으로 절대 날짜로 변환.
- start와 deadline과 title이 모두 동일하다면 하나의 이벤트로 간주.
- start와 deadline이 모두 없으면 이벤트로 간주하지 않음.
- start만 있으면 deadline은 start와 동일하게 설정.
- 필드 정의:
{{
  "projects": [
    {{
      "project": "문서의 프로젝트/제목",
      "owners": ["담당자1","담당자2"],
      "events": [
        {{
          "title": "간단한 액션 제목",
          "start": "YYYY-MM-DD HH:MM",
          "deadline": "YYYY-MM-DD HH:MM"
        }}
      ]
    }}
  ]
}}
"""


# -------------------- 유틸 --------------------
def source_title_from_filename(filename: str) -> str:
    base = Path(filename).stem
    m = re.match(r'^(\d{4}[-_/\.?]?\d{2}[-_/\.?]?\d{2})[_\-\s\.]*(.*)$', base)
    title = m.group(2) if m else base
    return title.strip() or base


def to_dt(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        if len(s) == 16:
            return datetime.strptime(s, "%Y-%m-%d %H:%M")
        elif len(s) == 10:
            return datetime.strptime(s, "%Y-%m-%d")
    except Exception:
        return None
    return None


def normalize_project(title: str) -> str:
    t = re.sub(r'^\s*(Re:|Fwd:)\s*', '', title or '', flags=re.IGNORECASE)
    t = re.sub(r'\[[^\]]+\]\s*', '', t).strip()
    return t or (title or "Untitled")


def normalize_owners(owners: List[str]):
    clean = []
    for o in owners or []:
        o = re.sub(r'<[^>]+>', '', o).strip()
        if o:
            clean.append(o)
    return tuple(sorted(set(clean)))


# -------------------- LLM 추출 --------------------
def extract_events_json_per_file(client: AzureOpenAI, text: str) -> Optional[Dict[str, Any]]:
    try:
        messages = [
            {"role": "system", "content": "당신은 신뢰성 높은 일정 파서입니다. 반드시 유효한 JSON만 출력합니다."},
            {"role": "user", "content": JSON_INSTRUCTIONS + "\n\n텍스트:\n" + text},
        ]
        resp = client.chat.completions.create(
            model=AZURE_CHAT_DEPLOY,
            messages=messages,
            temperature=0.0,
            max_tokens=1000,
        )
        raw = resp.choices[0].message.content.strip()
        start_idx = raw.find("{"); end_idx = raw.rfind("}")
        if start_idx == -1 or end_idx == -1:
            return None
        json_str = raw[start_idx:end_idx+1]
        return json.loads(json_str)
    except Exception:
        return None


# -------------------- 집계 및 마크다운 --------------------
def aggregate_all(files_with_text: List[Tuple[str, str]]):
    groups: Dict[Tuple[str, Tuple[str, ...]], Dict[str, Any]] = {}
    for fname, text in files_with_text:
        data = extract_events_json_per_file(client, text) if client else None
        if not data or "projects" not in data:
            continue
        for proj in data["projects"]:
            project = normalize_project(proj.get("project", ""))
            owners = normalize_owners(proj.get("owners", []))
            events = proj.get("events", []) or []
            source_title = source_title_from_filename(fname)
            key = (project, owners)
            if key not in groups:
                groups[key] = {"start": None, "deadline": None, "sources": set()}
            g = groups[key]
            g["sources"].add(source_title)
            for ev in events:
                st_dt = to_dt(ev.get("start", ""))
                dl_dt = to_dt(ev.get("deadline", ""))
                if st_dt and (not g["start"] or st_dt < g["start"]):
                    g["start"] = st_dt
                if dl_dt and (not g["deadline"] or dl_dt > g["deadline"]):
                    g["deadline"] = dl_dt
                if st_dt and not dl_dt and (not g["deadline"] or st_dt > g["deadline"]):
                    g["deadline"] = st_dt
    return groups


def build_markdown(groups: Dict[Tuple[str, Tuple[str, ...]], Dict[str, Any]]) -> str:
    blocks = ["# 인수인계 일정 요약", ""]
    def sort_key(item):
        (project, owners), g = item
        s = g["start"] or datetime(2100,1,1)
        return (project, owners, s)
    for (project, owners), g in sorted(groups.items(), key=sort_key):
        owners_str = ", ".join(owners) if owners else ""
        start_s = g["start"].strftime("%Y-%m-%d %H:%M") if g["start"] else ""
        deadline_s = g["deadline"].strftime("%Y-%m-%d %H:%M") if g["deadline"] else ""
        src_list = sorted(list(g["sources"]))
        src_show = ", ".join(src_list[:3]) + (f" (+{len(src_list)-3} more)" if len(src_list) > 3 else "")
        title = f"## {project} ({owners_str})" if owners_str else f"## {project}"
        blocks += [title, f"Start: {start_s} (KST)", f"Deadline: {deadline_s} (KST)", f"Source: {src_show}", ""]
    return "\n".join(blocks)


def save_markdown(md_text: str, out_path: str):
    Path(out_path).write_text(md_text, encoding="utf-8")


def _parse_summary_blocks(md_text: str) -> List[Dict[str, str]]:
    lines = [ln.strip() for ln in md_text.splitlines()]
    items: List[Dict[str, str]] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("## "):
            header = ln[3:].strip()
            project = header
            owners = ""
            m = re.match(r"^(.*)\((.*)\)\s*$", header)
            if m:
                project = m.group(1).strip()
                owners = m.group(2).strip()
            start = deadline = source = ""
            j = i + 1
            while j < len(lines):
                current_line = lines[j]
                if not current_line:
                    break
                if current_line.startswith("Start:"):
                    start = current_line.split("Start:", 1)[1].strip()
                elif current_line.startswith("Deadline:"):
                    deadline = current_line.split("Deadline:", 1)[1].strip()
                elif current_line.startswith("Source:"):
                    source = current_line.split("Source:", 1)[1].strip()
                j += 1
            start = start.replace("(KST)", "").strip()
            deadline = deadline.replace("(KST)", "").strip()
            items.append({"project": project, "owners": owners, "start": start, "deadline": deadline, "source": source})
            i = j
        else:
            i += 1
    return items


def visualize_calendar(md_text: str, out_png: str):
    items = _parse_summary_blocks(md_text)
    if not items:
        return
    def parse_dt(s: str):
        s = s.replace("(KST)", "").strip()
        if not s:
            return None
        try:
            if len(s) == 16:
                return datetime.strptime(s, "%Y-%m-%d %H:%M")
            elif len(s) == 10:
                return datetime.strptime(s, "%Y-%m-%d")
        except Exception:
            return None
        return None
    starts, ends, labels = [], [], []
    for it in items:
        st_dt = parse_dt(it["start"]) or datetime(2100,1,1)
        ed_dt = parse_dt(it["deadline"]) or st_dt + timedelta(hours=1)
        starts.append(st_dt)
        ends.append(ed_dt)
        labels.append(f"{it['project']} ({it['owners']})" if it["owners"] else it["project"])
    order = sorted(range(len(starts)), key=lambda k: starts[k])
    starts = [starts[k] for k in order]
    ends = [ends[k] for k in order]
    labels = [labels[k] for k in order]
    fig, ax = plt.subplots(figsize=(10, 0.6*len(labels) + 2))
    y_pos = list(range(len(labels)))
    left = [mdates.date2num(d) for d in starts]
    width = [mdates.date2num(ends[i]) - mdates.date2num(starts[i]) for i in range(len(starts))]
    ax.barh(y_pos, width, left=left)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.set_xlabel("Date")
    ax.set_title("Combined Schedule Timeline")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def write_ics(md_text: str, out_ics: str):
    items = _parse_summary_blocks(md_text)
    def parse_dt_full(s: str, default_time="00:00"):
        s = s.replace("(KST)", "").strip()
        if len(s) == 10:
            s = s + f" {default_time}"
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M")
        except Exception:
            return None
    now_utc = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ScheduleGen//KST//EN",
        "CALSCALE:GREGORIAN",
        "X-WR-TIMEZONE:Asia/Seoul",
    ]
    for idx, it in enumerate(items):
        st_dt = parse_dt_full(it["start"], "00:00")
        ed_dt = parse_dt_full(it["deadline"], "18:00")
        if not st_dt:
            continue
        if not ed_dt:
            ed_dt = st_dt
        uid = f"{idx}-{abs(hash(it['project']+it['owners']+it['start']))}@local"
        dtstart = st_dt.strftime("%Y%m%dT%H%M%S")
        dtend = ed_dt.strftime("%Y%m%dT%H%M%S")
        summary = f"{it['project']} ({it['owners']})" if it["owners"] else it["project"]
        desc = f"Source: {it['source']}"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;TZID=Asia/Seoul:{dtstart}",
            f"DTEND;TZID=Asia/Seoul:{dtend}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            "END:VEVENT",
        ]
    lines += ["END:VCALENDAR"]
    Path(out_ics).write_text("\n".join(lines), encoding="utf-8")


# -------------------- 엔트리 함수 --------------------
def build_schedule_from_db() -> Dict[str, Any]:
    files_data = get_uploaded_files_data()
    if not files_data:
        st.warning("업로드된 파일이 없습니다.")
        return {"success": False, "outputs": {}}

    files_with_text = list(files_data.items())
    groups = aggregate_all(files_with_text)

    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Only PNG output per requirement
    md_content = build_markdown(groups)
    png_path = os.path.join(output_dir, "combined_schedule_timeline.png")
    visualize_calendar(md_content, png_path)

    return {"success": True, "outputs": {"timeline_png": png_path}}

