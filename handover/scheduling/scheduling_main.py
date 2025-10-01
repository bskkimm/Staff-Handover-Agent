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

# 입력 파일(전처리 TXT 위치)
INPUT_FILE = "/home/hyundo/project1/Staff-Handover-Agent/data/preprocessed_data/No_1.txt"

# 출력 파일들(절대경로)
OUT_MD  = os.path.join(OUT_DIR, "combined_schedule.md")
OUT_PNG = os.path.join(OUT_DIR, "combined_schedule_timeline.png")
OUT_ICS = os.path.join(OUT_DIR, "combined_schedule.ics")

# 타임라인 PNG 생성 요청으로 비활성화
GENERATE_TIMELINE_PNG = False

# 폴더 생성
for d in [OUT_DIR, VIZ_DIR]:
    os.makedirs(d, exist_ok=True)

# -------------------- 설정 --------------------
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
KST = ZoneInfo("Asia/Seoul")
TODAY_STR = datetime.now(KST).strftime("%Y-%m-%d")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_CHAT_DEPLOY = (os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or "aicore-gpt4o").strip()
if not AZURE_API_KEY or not AZURE_ENDPOINT or not AZURE_CHAT_DEPLOY:
    raise RuntimeError("필수 Azure OpenAI 환경변수가 설정되지 않았습니다.")

client = AzureOpenAI(api_key=AZURE_API_KEY, api_version="2024-02-01", azure_endpoint=AZURE_ENDPOINT)

# -------------------- 유틸 --------------------
def source_title_from_filename(filename: str) -> str:
    base = Path(filename).stem
    m = re.match(r'^(\d{4}[-_/\.]?\d{2}[-_/\.]?\d{2})[_\-\s\.]*(.*)$', base)
    title = m.group(2) if m else base
    return title.strip() or base

def read_input_txt(file_path: str):
    try:
        file = Path(file_path)
        if not file.exists():
            raise FileNotFoundError(f"파일이 없습니다: {file.resolve()}")
        text = file.read_text(encoding="utf-8", errors="ignore")
        if text.strip():
            return [(file.name, text)]
        return []
    except Exception as e:
        print(f"[warn] {file_path} 읽기 실패: {e}")
        return []



JSON_INSTRUCTIONS = f"""
입력(JSON: emails/meetings/personal_notes)에서 '세분화된 프로젝트/주제'별 **단일 창구 이벤트(earliest~latest)**만 추출해 **유효한 JSON만** 출력하라.
- JSON 외 텍스트/코드블록 금지.
- 타임존: KST. 상대 날짜는 기준일 {TODAY_STR} 00:00(KST)로 절대화.

출력 스키마(고정):
{{ 
  "projects": [
    {{
      "project": "보상·예산가이드",                 # 상위·구체(예: 보상·킥오프/예산가이드/1차시뮬레이션/확정안/연간정책/시장데이터)
      "owners": ["이름1","이름2","이름3"],          # 등장빈도 상위 3명, 이름만, 오름차순
      "events": [
        {{
          "title": "{{프로젝트}} | 창구",          # 한 개만. 창구 대표 이벤트
          "start": "YYYY-MM-DD HH:MM",             # 해당 주제의 최소 시각
          "deadline": "YYYY-MM-DD HH:MM"           # 해당 주제의 최대 시각
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
  1) emails 본문 "일정(안)" 항목들(예: 자료 초안/팀별 회신/최종 안내)
  2) emails 본문 일반 문장 속 날짜/월-일(예: "컷 08-05", "공지 08-14", "착수 10-02", "마감 08-20")
  3) meetings."일시"
  4) meetings."결정사항" 내 날짜/월-일
  5) meetings."액션아이템[].기한"
  6) personal_notes."날짜", "다음액션[].기한"
  7) emails 헤더 date(본문에 일정 항목이 전혀 없을 때만 보조)
- earliest = 위 모든 시각의 **최소**, latest = **최대**.
- 시간이 없는 날짜는:
  - 시작계열(공지/초안/회의/착수 등) → 09:00
  - 마감계열(마감/회신/컷/공지/안내/확정 등) → 23:59
- "MM-DD"는 같은 레코드의 절대 연도를 상속. 없으면 기준일의 연도 사용.
- 파싱 실패 항목은 제외.
- 같은 이메일의 "일정(안)" 블록에 포함된 항목들은 **모두 동일한 프로젝트/주제**에 귀속하며,
  해당 블록 내 모든 시각의 **최소→최대**로 창구(window)를 산출한다.
  예: "킥오프" 메일의 [자료 초안, 팀별 회신, 최종 안내]가 함께 있으면
      start=자료 초안, end=최종 안내(예: 2024-08-01 10:00).

[owners 추출]
- emails: sender+recipients+cc 표시명, meetings: 참석자+작성자, personal_notes: 작성자.
- 중복 제거 후 **등장빈도 상위 3명**, 이름 오름차순. 비어 있으면 최소 1명 포함.

[정렬/제한]
- projects는 events[0].start 오름차순으로 정렬.
- 각 project의 events는 **반드시 1개만** 포함(창구 대표).
- 스키마 외 필드 금지. 비어 있으면 "projects": []만 출력.
"""



def extract_events_json_per_file(client, text: str) -> Optional[Dict[str, Any]]:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            messages = [
                {"role": "system", "content": "당신은 신뢰성 높은 일정 파서입니다. 반드시 유효한 JSON만 출력합니다. 어떤 설명이나 추가 텍스트도 포함하지 마세요."},
                {"role": "user", "content": JSON_INSTRUCTIONS + "\n\n텍스트:\n" + text}
            ]
            
            # API 호출
            resp = client.chat.completions.create(
                model=AZURE_CHAT_DEPLOY,
                messages=messages,
                temperature=0.0,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # 응답 처리
            if not getattr(resp, "choices", None):
                raise ValueError("빈 응답을 수신했습니다.")

            raw = resp.choices[0].message.content.strip()
            
            # JSON 문자열 정제
            raw = raw.replace('\n', ' ').replace('\r', '')
            raw = re.sub(r'\s+', ' ', raw)
            raw = re.sub(r',\s*}', '}', raw)  # 후행 쉼표 제거
            raw = re.sub(r',\s*]', ']', raw)  # 후행 쉼표 제거
            
            # JSON 시작/끝 위치 조정
            if not raw.startswith('{'): 
                raw = raw[raw.find('{'):] if '{' in raw else '{}'
            if not raw.endswith('}'): 
                raw = raw[:raw.rfind('}')+1] if '}' in raw else '{}'
            
            # JSON 파싱 시도
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and "projects" in parsed:
                    return parsed
                return {"projects": []}
            except json.JSONDecodeError:
                if attempt == max_retries - 1:
                    print(f"[info] JSON 파싱 실패 (마지막 시도)")
                    return {"projects": []}
                continue
                
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[info] API 호출 실패: {str(e)}")
                return {"projects": []}
            continue
            
    return {"projects": []}

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
    files_with_text = read_input_txt(INPUT_FILE)
    if not files_with_text:
        print("처리할 TXT가 없습니다.")
        return
    groups = aggregate_all(files_with_text)
    md = build_markdown(groups)
    save_markdown(md, OUT_MD)
    if GENERATE_TIMELINE_PNG:
        visualize_calendar(md, OUT_PNG)
    write_ics(md, OUT_ICS)
    # viz 산출물도 scheduling/output 하위에 생성
    render_all_months_bars(OUT_MD, VIZ_DIR)
    print(f"[ok] Viz 폴더: {VIZ_DIR}")

if __name__ == "__main__":
    main()
