# -*- coding: utf-8 -*-
"""
desk_calendar_bar_viz.py — Monthly "desk calendar" with horizontal bars per event
- 오늘 날짜 '칸'만 하이라이트
- 오늘 이전 bar는 회색(흑백) 처리
- 진행중(bar에 today 포함) 라벨에 '(진행중)' 표시
- 바가 날짜 숫자를 가리지 않도록 cell 내 하단 영역에 배치
"""

from pathlib import Path
from datetime import datetime, timedelta, date
import re, calendar, hashlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams
from matplotlib import cm

WEEKDAYS_KO = ["일", "월", "화", "수", "목", "금", "토"]

# z-order
Z_BG = 0
Z_GRID = 1
Z_TODAY = 3
Z_BARS = 5
Z_DATE = 7
Z_LABELS = 8

def _set_korean_font():
    candidates = [
        "Malgun Gothic", "Apple SD Gothic Neo", "NanumGothic", "Noto Sans CJK KR",
    ]
    for name in candidates:
        try:
            fontpath = font_manager.findfont(name, fallback_to_default=False)
            if fontpath and Path(fontpath).exists():
                rcParams["font.family"] = name
                rcParams["axes.unicode_minus"] = False
                return name
        except Exception:
            pass
    rcParams["axes.unicode_minus"] = False
    return None

def _parse_blocks(md_text: str):
    lines = [ln.strip() for ln in md_text.splitlines()]
    items = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("## "):
            header = ln[3:].strip()
            project = header; owners = ""
            m = re.match(r"^(.*)\((.*)\)\s*$", header)
            if m:
                project = m.group(1).strip()
                owners = m.group(2).strip()
            start = deadline = source = ""
            j = i+1
            while j < len(lines) and lines[j]:
                if lines[j].startswith("Start:"):
                    start = lines[j].split("Start:",1)[1].strip().replace("(KST)","").strip()
                elif lines[j].startswith("Deadline:"):
                    deadline = lines[j].split("Deadline:",1)[1].strip().replace("(KST)","").strip()
                elif lines[j].startswith("Source:"):
                    source = lines[j].split("Source:",1)[1].strip()
                j += 1
            items.append({"project":project,"owners":owners,"start":start,"deadline":deadline,"source":source})
            i = j
        else:
            i += 1
    return items

def _parse_dt(s: str, default_time="00:00"):
    s = (s or "").strip()
    if not s:
        return None
    if len(s) == 10:
        s = s + f" {default_time}"
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M")
    except Exception:
        return None

def _month_date_range(year:int, month:int):
    first = date(year, month, 1)
    if month == 12:
        last = date(year+1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month+1, 1) - timedelta(days=1)
    return first, last

def _week_date_grid(year:int, month:int, firstweekday=6):
    cal = calendar.Calendar(firstweekday=firstweekday)
    raw = cal.monthdayscalendar(year, month)  # 0 for overflow
    weeks = []
    for wk in raw:
        row = []
        for d in wk:
            if d == 0:
                row.append(None)
            else:
                row.append(date(year, month, d))
        weeks.append(row)
    return weeks

def _clip_span_to_month(st: date, ed: date, month_first: date, month_last: date):
    a = max(st, month_first)
    b = min(ed, month_last)
    if b < a:
        return None, None
    return a, b

def _segments_for_week(week_dates, st: date, ed: date):
    indices = [i for i,d in enumerate(week_dates) if d is not None]
    if not indices:
        return None
    leftmost = indices[0]; rightmost = indices[-1]
    if ed < week_dates[leftmost] or st > week_dates[rightmost]:
        return None
    c0 = leftmost
    for i, d in enumerate(week_dates):
        if d and d >= st:
            c0 = i; break
    c1 = rightmost
    for i in range(len(week_dates)-1, -1, -1):
        d = week_dates[i]
        if d and d <= ed:
            c1 = i; break
    if c1 < c0:
        return None
    return c0, c1

def _allocate_lane(lanes, c0, c1):
    for li, occ in enumerate(lanes):
        overlap = any(not (c1 < oc0 or c0 > oc1) for (oc0, oc1) in occ)
        if not overlap:
            occ.append((c0,c1))
            return li
    lanes.append([(c0,c1)])
    return len(lanes)-1

def _build_color_map(project_names):
    from matplotlib import cm
    cmap = cm.get_cmap("tab20", 20)
    colors = {}
    for name in project_names:
        import hashlib
        idx = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16) % 20
        colors[name] = cmap(idx)
    return colors

def _ideal_text_color(rgb):
    r, g, b = rgb[:3]
    y = 0.2126*r + 0.7152*g + 0.0722*b
    return "black" if y > 0.6 else "white"

def render_month_bars(md_text: str, year: int, month: int, out_png: str, max_lanes_per_week=5, color_map=None, label_once_per_span=True, today: date=None):
    if today is None:
        today = date(2024, 7, 11)  # prototype default
    _set_korean_font()

    items = _parse_blocks(md_text)
    spans = []
    projects = set()
    for it in items:
        st_dt = _parse_dt(it["start"], "00:00")
        ed_dt = _parse_dt(it["deadline"], "18:00") or st_dt
        if not st_dt: continue
        if ed_dt < st_dt: ed_dt = st_dt
        title = it["project"].strip()
        projects.add(title)
        spans.append({"title": title, "st": st_dt.date(), "ed": ed_dt.date()})
    if not spans:
        raise RuntimeError("No valid spans")

    if color_map is None:
        color_map = _build_color_map(sorted(projects))

    month_first, month_last = _month_date_range(year, month)
    weeks = _week_date_grid(year, month, firstweekday=6)

    for sp in spans:
        a, b = _clip_span_to_month(sp["st"], sp["ed"], month_first, month_last)
        sp["clip_a"], sp["clip_b"] = a, b

    labeled_keys = set()

    rows = len(weeks) + 1
    cols = 7
    fig_w, fig_h = 12, max(8, 1.3 * rows)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")

    left_margin, right_margin, top_margin, bottom_margin = 0.03, 0.03, 0.08, 0.03
    grid_w = 1.0 - left_margin - right_margin
    grid_h = 1.0 - top_margin - bottom_margin
    cell_w = grid_w / cols
    cell_h = grid_h / rows
    day_header_band = 0.28 * cell_h

    ax.text(0.5, 0.98, f"{year}년 {month}월", ha="center", va="top", fontsize=18, transform=ax.transAxes, zorder=7)

    # Header row
    for c in range(cols):
        x0 = left_margin + c * cell_w
        y0 = 1.0 - top_margin - cell_h
        ax.add_patch(plt.Rectangle((x0, y0), cell_w, cell_h, fill=False, zorder=1))
        ax.text(x0 + 0.5*cell_w, y0 + 0.5*cell_h, WEEKDAYS_KO[c], ha="center", va="center", fontsize=12, zorder=7)

    # Body grid & day numbers with today cell highlight
    for r, week in enumerate(weeks):
        today_col = None
        for c, d in enumerate(week):
            if d and today and d == today:
                today_col = c; break
        for c, d in enumerate(week):
            x0 = left_margin + c * cell_w
            y0 = 1.0 - top_margin - (r+2) * cell_h
            ax.add_patch(plt.Rectangle((x0, y0), cell_w, cell_h, fill=False, zorder=1))
            if today_col is not None and c == today_col:
                ax.add_patch(plt.Rectangle((x0, y0), cell_w, cell_h, facecolor=(1.0, 0.96, 0.6, 0.35), edgecolor='none', zorder=3))
            if d and d.month == month:
                ax.text(x0 + 0.01, y0 + cell_h - 0.02, f"{d.day}", ha="left", va="top", fontsize=10, zorder=7)

    # Bars
    for r, week in enumerate(weeks):
        col_date = {c:d for c,d in enumerate(week) if d is not None}
        lanes = []
        for sp in spans:
            a, b = sp["clip_a"], sp["clip_b"]
            if not a or not b: continue
            seg = _segments_for_week(week, a, b)
            if not seg: continue
            c0, c1 = seg
            lane = _allocate_lane(lanes, c0, c1)
            if lane >= max_lanes_per_week: continue

            y0 = 1.0 - top_margin - (r+2) * cell_h
            lane_h = (cell_h - day_header_band) / (max_lanes_per_week + 0.6)
            bar_y = y0 + day_header_band + lane * lane_h + 0.02
            bar_h = lane_h * 0.8

            base_color = _build_color_map([sp["title"]])[sp["title"]] if color_map is None else color_map.get(sp["title"])
            is_active = (today and a <= today <= b)

            today_c = None
            for c, d in col_date.items():
                if today and d == today:
                    today_c = c; break

            def _draw_range(col_start, col_end, color):
                x0 = left_margin + col_start * cell_w + 0.01
                w = (col_end - col_start + 1) * cell_w - 0.02
                if w <= 0: 
                    return None
                rect = plt.Rectangle((x0, bar_y), w, bar_h, fill=True, color=color, zorder=5)
                ax.add_patch(rect)
                return x0, w

            if today_c is not None and c0 <= today_c <= c1:
                if c0 <= today_c - 1:
                    _draw_range(c0, today_c - 1, (0.85, 0.85, 0.85, 1.0))
                xw = _draw_range(today_c, c1, base_color)
                if label_once_per_span:
                    ax.text((left_margin + c0 * cell_w) + 0.02, bar_y + bar_h/2,
                            sp["title"] + " (진행중)", ha="left", va="center", fontsize=9,
                            color=_ideal_text_color(base_color), zorder=8, clip_on=True)
            else:
                seg_end_date = col_date.get(c1)
                if today and seg_end_date and seg_end_date < today:
                    _draw_range(c0, c1, (0.85, 0.85, 0.85, 1.0))
                    if label_once_per_span:
                        ax.text((left_margin + c0 * cell_w) + 0.02, bar_y + bar_h/2,
                                sp["title"], ha="left", va="center", fontsize=9, color="black", zorder=8, clip_on=True)
                else:
                    xw = _draw_range(c0, c1, base_color)
                    if label_once_per_span:
                        ax.text((left_margin + c0 * cell_w) + 0.02, bar_y + bar_h/2,
                                sp["title"], ha="left", va="center", fontsize=9,
                                color=_ideal_text_color(base_color), zorder=8, clip_on=True)

    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    return out_png

def render_all_months_bars(md_path: str, out_dir: str, today: date=None):
    if today is None:
        today = date(2024, 7, 11)  # prototype default
    md_text = Path(md_path).read_text(encoding="utf-8")

    lines = [ln.strip() for ln in md_text.splitlines()]
    items = []
    projects = set()
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("## "):
            header = ln[3:].strip()
            project = header; owners = ""
            m = re.match(r"^(.*)\((.*)\)\s*$", header)
            if m:
                project = m.group(1).strip()
                owners = m.group(2).strip()
            start = deadline = ""
            j = i+1
            while j < len(lines) and lines[j]:
                if lines[j].startswith("Start:"):
                    start = lines[j].split("Start:",1)[1].strip().replace("(KST)","").strip()
                elif lines[j].startswith("Deadline:"):
                    deadline = lines[j].split("Deadline:",1)[1].strip().replace("(KST)","").strip()
                j += 1
            items.append({"project":project,"start":start,"deadline":deadline})
            projects.add(project.strip())
            i = j
        else:
            i += 1

    def parse_dt(s: str, default_time="00:00"):
        s = s.strip()
        if len(s) == 10:
            s += f" {default_time}"
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M")
        except Exception:
            return None

    starts = [parse_dt(it["start"], "00:00") for it in items if parse_dt(it["start"], "00:00")]
    ends   = [parse_dt(it["deadline"], "18:00") for it in items if parse_dt(it["deadline"], "18:00")]
    if not starts:
        raise RuntimeError("No items")
    smin = min(starts)
    emax = max(ends) if ends else smin

    color_map = _build_color_map(sorted(projects))

    out_dir_path = Path(out_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    y, m = smin.year, smin.month
    while True:
        out_png = out_dir_path / f"calendar_bars_{y}_{m:02d}.png"
        render_month_bars(md_text, y, m, str(out_png), color_map=color_map, label_once_per_span=True, today=today)
        if (y, m) == (emax.year, emax.month):
            break
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return True
