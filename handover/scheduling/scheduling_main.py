# -*- coding: utf-8 -*-
"""
Prototype 04A+Viz — Per-file extract → aggregate + Calendar 시각화
"""

from openai import AzureOpenAI
import os, json, re
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Tuple, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from desk_calendar_bar_viz import render_all_months_bars

# -------------------- 고정 경로 --------------------
SCHED_DIR = "/home/hyundo/project1/Staff-Handover-Agent/handover/scheduling"
OUT_DIR   = os.path.join(SCHED_DIR, "output")
VIZ_DIR   = os.path.join(OUT_DIR, "out_cal_bars")

# 입력 폴더(전처리 TXT 위치)
FOLDER_PATH = "/home/hyundo/project1/Staff-Handover-Agent/data"

# 출력 파일들(절대경로)
OUT_MD  = os.path.join(OUT_DIR, "combined_schedule.md")
OUT_PNG = os.path.join(OUT_DIR, "combined_schedule_timeline.png")
OUT_ICS = os.path.join(OUT_DIR, "combined_schedule.ics")

# 폴더 생성
for d in [OUT_DIR, VIZ_DIR]:
    os.makedirs(d, exist_ok=True)

# -------------------- 설정 --------------------
load_dotenv()
KST = ZoneInfo("Asia/Seoul")
TODAY_STR = datetime.now(KST).strftime("%Y-%m-%d")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_CHAT_DEPLOY = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "aicore-gpt4o")

if not AZURE_API_KEY or not AZURE_ENDPOINT:
    raise RuntimeError("AZURE_OPENAI_API_KEY / AZURE_OPENAI_ENDPOINT 설정 필요")

client = AzureOpenAI(api_key=AZURE_API_KEY, api_version="2024-02-01", azure_endpoint=AZURE_ENDPOINT)

# -------------------- 유틸 --------------------
def source_title_from_filename(filename: str) -> str:
    base = Path(filename).stem
    m = re.match(r'^(\d{4}[-_/\.]?\d{2}[-_/\.]?\d{2})[_\-\s\.]*(.*)$', base)
    title = m.group(2) if m else base
    return title.strip() or base

def read_all_txt(folder_path: str):
    base = Path(folder_path)
    if not base.exists():
        raise FileNotFoundError(f"폴더가 없습니다: {base.resolve()}")
    files = list(base.rglob("*.txt"))
    docs = []
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
            if text.strip():
                docs.append((fp.name, text))
        except Exception as e:
            print(f"[warn] {fp.name} 읽기 실패: {e}")
    return docs

JSON_INSTRUCTIONS = f"""
다음 텍스트(이메일 또는 업무일지)에서 프로젝트와 일정 이벤트를 JSON으로만 출력하세요.
- JSON 외의 모든 텍스트 금지 (코드블록 금지).
- 날짜는 KST로 해석. 상대 날짜는 기준일 {TODAY_STR} (KST)을 기준으로 절대 날짜로 변환.
- 필드 정의:
{{
  "projects": [
    {{
      "project": "문서의 프로젝트/제목(Subject 정제 또는 '프로젝트:'/'제목:' 값)",
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

def extract_events_json_per_file(client, text: str) -> Optional[Dict[str, Any]]:
    try:
        messages = [
            {"role": "system", "content": "당신은 신뢰성 높은 일정 파서입니다. 반드시 유효한 JSON만 출력합니다."},
            {"role": "user", "content": JSON_INSTRUCTIONS + "\n\n텍스트:\n" + text}
        ]
        resp = client.chat.completions.create(
            model=AZURE_CHAT_DEPLOY,
            messages=messages,
            temperature=0.0,
            max_tokens=1000,
        )
        raw = resp.choices[0].message.content.strip()
        start_idx = raw.find("{"); end_idx = raw.rfind("}")
        if start_idx == -1 or end_idx == -1: return None
        json_str = raw[start_idx:end_idx+1]
        return json.loads(json_str)
    except Exception as e:
        print(f"[warn] JSON 추출 실패: {e}")
        return None

def to_dt(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s: return None
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
        if o: clean.append(o)
    return tuple(sorted(set(clean)))

def aggregate_all(files_with_text):
    groups = {}
    for fname, text in files_with_text:
        data = extract_events_json_per_file(client, text)
        if not data or "projects" not in data: continue
        for proj in data["projects"]:
            project = normalize_project(proj.get("project",""))
            owners = normalize_owners(proj.get("owners", []))
            events = proj.get("events", []) or []
            source_title = source_title_from_filename(fname)
            key = (project, owners)
            if key not in groups:
                groups[key] = {"start": None, "deadline": None, "sources": set()}
            g = groups[key]
            g["sources"].add(source_title)
            for ev in events:
                st = to_dt(ev.get("start",""))
                dl = to_dt(ev.get("deadline",""))
                if st:
                    if not g["start"] or st < g["start"]:
                        g["start"] = st
                if dl:
                    if not g["deadline"] or dl > g["deadline"]:
                        g["deadline"] = dl
                if st and not dl:
                    if not g["deadline"] or st > g["deadline"]:
                        g["deadline"] = st
    return groups

def build_markdown(groups):
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
    print(f"[ok] Markdown 저장: {out_path}")

def parse_summary_blocks(md_text: str):
    lines = [ln.strip() for ln in md_text.splitlines()]
    items = []
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
            j = i+1
            while j < len(lines) and lines[j]:
                if lines[j].startswith("Start:"):
                    start = lines[j].split("Start:",1)[1].strip()
                elif lines[j].startswith("Deadline:"):
                    deadline = lines[j].split("Deadline:",1)[1].strip()
                elif lines[j].startswith("Source:"):
                    source = lines[j].split("Source:",1)[1].strip()
                j += 1
            start = start.replace("(KST)","").strip()
            deadline = deadline.replace("(KST)","").strip()
            items.append({
                "project": project,
                "owners": owners,
                "start": start,
                "deadline": deadline,
                "source": source
            })
            i = j
        else:
            i += 1
    return items

def visualize_calendar(md_text: str, out_png: str):
    items = parse_summary_blocks(md_text)
    if not items:
        print("[info] 시각화할 항목이 없습니다.")
        return
    def parse_dt(s: str):
        s = s.replace("(KST)","").strip()
        if not s: return None
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
        st = parse_dt(it["start"]) or datetime(2100,1,1)
        ed = parse_dt(it["deadline"]) or st + timedelta(hours=1)
        starts.append(st); ends.append(ed)
        labels.append(f'{it["project"]} ({it["owners"]})' if it["owners"] else it["project"])
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
    print(f"[ok] 타임라인 PNG 저장: {out_png}")

def write_ics(md_text: str, out_ics: str):
    items = parse_summary_blocks(md_text)
    def parse_dt_full(s: str, default_time="00:00"):
        s = s.replace("(KST)","").strip()
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
        st = parse_dt_full(it["start"], "00:00")
        ed = parse_dt_full(it["deadline"], "18:00")
        if not st: continue
        if not ed: ed = st
        uid = f"{idx}-{abs(hash(it['project']+it['owners']+it['start']))}@local"
        dtstart = st.strftime("%Y%m%dT%H%M%S")
        dtend = ed.strftime("%Y%m%dT%H%M%S")
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
    print(f"[ok] ICS 저장: {out_ics}")

def main():
    files_with_text = read_all_txt(FOLDER_PATH)
    if not files_with_text:
        print("처리할 TXT가 없습니다.")
        return
    groups = aggregate_all(files_with_text)
    md = build_markdown(groups)
    save_markdown(md, OUT_MD)
    visualize_calendar(md, OUT_PNG)
    write_ics(md, OUT_ICS)
    # viz 산출물도 scheduling/output 하위에 생성
    render_all_months_bars(OUT_MD, VIZ_DIR)
    print(f"[ok] Viz 폴더: {VIZ_DIR}")

if __name__ == "__main__":
    main()
