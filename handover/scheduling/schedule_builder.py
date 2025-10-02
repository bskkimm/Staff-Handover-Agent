"""Aggregate LLM output into schedule summaries."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Iterable, List, Tuple, Optional
import re

from .llm_parser import extract_events_json_per_file


def source_title_from_filename(filename: str) -> str:
    base = Path(filename).stem
    match = re.match(r"^(\d{4}[-_/\.]?\d{2}[-_/\.]?\d{2})[_\-\s\.]*(.*)$", base)
    title = match.group(2) if match else base
    return title.strip() or base


def normalize_project(title: str) -> str:
    cleaned = re.sub(r"^\s*(Re:|Fwd:)\s*", "", title or "", flags=re.IGNORECASE)
    cleaned = re.sub(r"\[[^\]]+\]\s*", "", cleaned).strip()
    return cleaned or (title or "Untitled")


def normalize_owners(owners: Iterable[str]) -> Tuple[str, ...]:
    cleaned = []
    for owner in owners or []:
        owner = re.sub(r"<[^>]+>", "", owner).strip()
        if owner:
            cleaned.append(owner)
    return tuple(sorted(set(cleaned)))


def to_dt(value: str) -> Optional[datetime]:
    value = (value or "").strip()
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


def aggregate_events(files_with_text: Iterable[Tuple[str, str]], client) -> Dict[Tuple[str, Tuple[str, ...]], Dict[str, Any]]:
    groups: Dict[Tuple[str, Tuple[str, ...]], Dict[str, Any]] = {}
    for fname, text in files_with_text:
        data = extract_events_json_per_file(client, text)
        for project_block in data.get("projects", []):
            project = normalize_project(project_block.get("project", ""))
            owners = normalize_owners(project_block.get("owners", []))
            key = (project, owners)
            group = groups.setdefault(key, {"start": None, "deadline": None, "sources": set()})
            group["sources"].add(source_title_from_filename(fname))
            for event in project_block.get("events", []) or []:
                start = to_dt(event.get("start", ""))
                deadline = to_dt(event.get("deadline", ""))
                if start and (group["start"] is None or start < group["start"]):
                    group["start"] = start
                if deadline and (group["deadline"] is None or deadline > group["deadline"]):
                    group["deadline"] = deadline
                if start and not deadline and (group["deadline"] is None or start > group["deadline"]):
                    group["deadline"] = start
    return groups


def build_markdown(groups: Dict[Tuple[str, Tuple[str, ...]], Dict[str, Any]]) -> str:
    blocks = ["# 인수인계 일정 요약", ""]

    def sort_key(item):
        (project, owners), info = item
        start = info["start"] or datetime(2100, 1, 1)
        return (project, owners, start)

    for (project, owners), info in sorted(groups.items(), key=sort_key):
        owners_str = ", ".join(owners) if owners else ""
        start_str = info["start"].strftime("%Y-%m-%d %H:%M") if info["start"] else ""
        deadline_str = info["deadline"].strftime("%Y-%m-%d %H:%M") if info["deadline"] else ""
        sources = sorted(list(info["sources"]))
        source_preview = ", ".join(sources[:3]) + (f" (+{len(sources) - 3} more)" if len(sources) > 3 else "")
        header = f"## {project} ({owners_str})" if owners_str else f"## {project}"
        blocks.extend([
            header,
            f"Start: {start_str} (KST)",
            f"Deadline: {deadline_str} (KST)",
            f"Source: {source_preview}",
            "",
        ])
    return "\n".join(blocks)


def parse_summary_blocks(md_text: str) -> List[Dict[str, str]]:
    lines = [line.strip() for line in md_text.splitlines()]
    items: List[Dict[str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            header = line[3:].strip()
            project = header
            owners = ""
            match = re.match(r"^(.*)\((.*)\)\s*$", header)
            if match:
                project = match.group(1).strip()
                owners = match.group(2).strip()
            start = deadline = source = ""
            j = i + 1
            while j < len(lines) and lines[j]:
                if lines[j].startswith("Start:"):
                    start = lines[j].split("Start:", 1)[1].strip()
                elif lines[j].startswith("Deadline:"):
                    deadline = lines[j].split("Deadline:", 1)[1].strip()
                elif lines[j].startswith("Source:"):
                    source = lines[j].split("Source:", 1)[1].strip()
                j += 1
            items.append({
                "project": project,
                "owners": owners,
                "start": start.replace("(KST)", "").strip(),
                "deadline": deadline.replace("(KST)", "").strip(),
                "source": source,
            })
            i = j
        else:
            i += 1
    return items
