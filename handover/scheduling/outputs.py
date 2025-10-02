"""Output helpers for schedule artifacts."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from .schedule_builder import parse_summary_blocks
from .config import OUT_PNG
from .desk_calendar_bar_viz import render_all_months_bars


def save_markdown(markdown: str, path: Path) -> None:
    path.write_text(markdown, encoding="utf-8")
    print(f"[ok] Markdown 저장: {path}")


def visualize_calendar(md_text: str, output_path: Path) -> None:
    items = parse_summary_blocks(md_text)
    if not items:
        print("[info] 시각화할 일정이 없습니다.")
        return

    def parse_dt(value: str) -> Optional[datetime]:
        # 마크다운에 있는 전체 시각과 날짜만 있는 값 모두를 허용한다.
        value = value.strip()
        if not value:
            return None
        try:
            if len(value) == 16:
                return datetime.strptime(value, "%Y-%m-%d %H:%M")
            if len(value) == 10:
                return datetime.strptime(value, "%Y-%m-%d")
        except Exception:
            return None
        return None

    starts: List[datetime] = []
    ends: List[datetime] = []
    labels: List[str] = []
    for item in items:
        start = parse_dt(item["start"]) or datetime(2100, 1, 1)
        end = parse_dt(item["deadline"]) or (start + timedelta(hours=1))
        starts.append(start)
        ends.append(end)
        label = f"{item['project']} ({item['owners']})" if item["owners"] else item["project"]
        labels.append(label)

    # 시작 시각 순으로 정렬해 막대가 시간 순으로 보이게 한다.
    order = sorted(range(len(starts)), key=lambda idx: starts[idx])
    starts = [starts[idx] for idx in order]
    ends = [ends[idx] for idx in order]
    labels = [labels[idx] for idx in order]

    fig, ax = plt.subplots(figsize=(10, 0.6 * len(labels) + 2))
    y_positions = list(range(len(labels)))
    left = [mdates.date2num(dt) for dt in starts]
    widths = [mdates.date2num(ends[i]) - mdates.date2num(starts[i]) for i in range(len(starts))]

    ax.barh(y_positions, widths, left=left)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.set_xlabel("Date")
    ax.set_title("Combined Schedule Timeline")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"[ok] 타임라인 PNG 저장: {output_path}")


def write_ics(md_text: str, output_path: Path) -> None:
    items = parse_summary_blocks(md_text)

    def parse_dt_full(value: str, default_time: str = "00:00") -> Optional[datetime]:
        # 부분 시각을 보정해 ICS 항목을 유효하게 만든다.
        value = value.replace("(KST)", "").strip()
        if len(value) == 10:
            value = f"{value} {default_time}"
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M")
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

    for idx, item in enumerate(items):
        start = parse_dt_full(item["start"], "00:00")
        end = parse_dt_full(item["deadline"], "18:00") or start
        if not start:
            continue
        uid = f"{idx}-{abs(hash(item['project'] + item['owners'] + item['start']))}@local"
        dtstart = start.strftime("%Y%m%dT%H%M%S")
        dtend = (end or start).strftime("%Y%m%dT%H%M%S")
        summary = f"{item['project']} ({item['owners']})" if item["owners"] else item["project"]
        desc = f"Source: {item['source']}"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;TZID=Asia/Seoul:{dtstart}",
            f"DTEND;TZID=Asia/Seoul:{dtend}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[ok] ICS 저장: {output_path}")


def render_monthly_bars(md_path: Path, out_dir: Path) -> None:
    render_all_months_bars(str(md_path), str(out_dir))
    print(f"[ok] Viz 폴더: {out_dir}")
