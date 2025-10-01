"""
json_chunker.py

Schema-aware chunking for HR handover JSON:
- emails[]      -> header + content (windowed if long)
- meetings[]    -> header + per-section chunks (안건/논의/결정사항/액션아이템)
- personal_notes[] -> header + per-section chunks

Usage:
    from chunkers import json_chunker
    json_chunker.set_tokenizer(tok)  # tok must have .encode/.decode
    items = json_chunker.chunks_from_json_obj(data, source="hr_schedule.json")

Each returned item is a dict containing:
    {
      "text": str,
      "source": str,
      "type": "email" | "meeting" | "personal",
      "section": str,
      # + identifying metadata like subject/title, date/datetime, etc.
      "chunk_index_in_doc": int
    }

Note: Token-aware splitting requires that you call set_tokenizer() first.
"""

from typing import List, Dict, Any, Iterable, Tuple

__all__ = [
    "set_tokenizer",
    "chunks_from_json_obj",
]

# ----------------------------
# Tokenizer injection
# ----------------------------
_tok = None  # inject with set_tokenizer() before use


def set_tokenizer(tok) -> None:
    """
    Inject a tokenizer object that provides:
      - encode(str) -> List[int]
      - decode(List[int]) -> str
    """
    global _tok
    _tok = tok


def _require_tok():
    if _tok is None:
        raise RuntimeError(
            "Tokenizer is not set. Call set_tokenizer(tok) before using json_chunker."
        )


def _encode(text: str) -> List[int]:
    _require_tok()
    # defensive: ensure text is a string
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    return _tok.encode(text)


def _decode(ids: List[int]) -> str:
    _require_tok()
    return _tok.decode(ids)


# ----------------------------
# Small helpers
# ----------------------------
def _tlen(text: str) -> int:
    return len(_encode(text))


def _split_long_text(text: str, max_tokens: int, overlap: int) -> Iterable[str]:
    """
    Token-window splitter with overlap and forward-progress safety.
    """
    ids = _encode(text)
    n = len(ids)
    if n == 0:
        return
    # ensure we always advance
    step = max(1, max_tokens - max(0, overlap))
    start = 0
    while start < n:
        end = min(start + max_tokens, n)
        yield _decode(ids[start:end])
        if end == n:
            break
        start += step


def _join_lines(lines: Iterable[str]) -> str:
    return "\n".join([ln for ln in lines if str(ln).strip()])


# ----------------------------
# Email chunking
# ----------------------------
def _prefix_email(e: Dict[str, Any]) -> str:
    rcpts = ", ".join(e.get("recipients", []) or [])
    cc = ", ".join(e.get("cc", []) or [])
    return (
        "[EMAIL]\n"
        f"Date: {e.get('date', '')}\n"
        f"Subject: {e.get('subject', '')}\n"
        f"From: {e.get('sender', '')}\n"
        f"To: {rcpts}\n"
        f"CC: {cc}"
    ).strip()


def _email_chunks(
    e: Dict[str, Any],
    source: str,
    base_idx: int,
    max_tokens: int,
    overlap: int,
) -> List[Dict[str, Any]]:
    header = _prefix_email(e)
    body = str(e.get("content", "")).strip()
    header_len = _tlen(header + "\n\n")
    body_budget = max(1, max_tokens - header_len)

    out: List[Dict[str, Any]] = []
    ci = 0

    # Fits into one piece
    if _tlen(header + "\n\n" + body) <= max_tokens:
        out.append(
            {
                "text": header + "\n\n" + body,
                "source": source,
                "type": "email",
                "section": "content",
                "date": e.get("date", ""),
                "subject": e.get("subject", ""),
                "sender": e.get("sender", ""),
                "chunk_index_in_doc": base_idx + ci,
            }
        )
        return out

    # Long body: split into windows and repeat header
    for piece in _split_long_text(body, body_budget, overlap):
        out.append(
            {
                "text": header + "\n\n" + piece,
                "source": source,
                "type": "email",
                "section": "content",
                "date": e.get("date", ""),
                "subject": e.get("subject", ""),
                "sender": e.get("sender", ""),
                "chunk_index_in_doc": base_idx + ci,
            }
        )
        ci += 1

    return out


# ----------------------------
# Meeting chunking
# ----------------------------
def _prefix_meeting(m: Dict[str, Any]) -> str:
    return _join_lines(
        [
            "[MEETING]",
            f"제목: {m.get('제목', '')}",
            f"일시: {m.get('일시', '')}",
            f"장소: {m.get('장소', '')}",
            f"작성자: {m.get('작성자', '')}",
            f"참석자: {m.get('참석자', '')}",
            f"배경: {m.get('배경', '')}",
        ]
    )


def _meeting_chunks(
    m: Dict[str, Any],
    source: str,
    base_idx: int,
    max_tokens: int,
    overlap: int,
) -> List[Dict[str, Any]]:
    header = _prefix_meeting(m)
    header_len = _tlen(header + "\n\n")
    body_budget = max(1, max_tokens - header_len)

    out: List[Dict[str, Any]] = []
    ci = 0

    # section name -> value
    sections: List[Tuple[str, Any]] = [
        ("안건", m.get("안건", [])),
        ("논의", m.get("논의", "")),
        ("결정사항", m.get("결정사항", [])),
        ("액션아이템", m.get("액션아이템", [])),
    ]

    for sec_name, sec_val in sections:
        if not sec_val:
            continue

        # 액션아이템: list of dicts {작업, 기한, 담당자}
        if isinstance(sec_val, list) and sec_name == "액션아이템" and sec_val and isinstance(
            sec_val[0], dict
        ):
            for ai in sec_val:
                ai_text = _join_lines(
                    [
                        f"[{sec_name}]",
                        f"- 작업: {ai.get('작업', '')}",
                        f"- 기한: {ai.get('기한', '')}",
                        f"- 담당자: {ai.get('담당자', '')}",
                    ]
                )
                if _tlen(header + "\n\n" + ai_text) <= max_tokens:
                    out.append(
                        {
                            "text": header + "\n\n" + ai_text,
                            "source": source,
                            "type": "meeting",
                            "section": sec_name,
                            "title": m.get("제목", ""),
                            "datetime": m.get("일시", ""),
                            "chunk_index_in_doc": base_idx + ci,
                        }
                    )
                    ci += 1
                else:
                    for piece in _split_long_text(ai_text, body_budget, overlap):
                        out.append(
                            {
                                "text": header + "\n\n" + piece,
                                "source": source,
                                "type": "meeting",
                                "section": sec_name,
                                "title": m.get("제목", ""),
                                "datetime": m.get("일시", ""),
                                "chunk_index_in_doc": base_idx + ci,
                            }
                        )
                        ci += 1
            continue

        # Generic list sections (안건/결정사항) or list-type 액션아이템 fallback
        if isinstance(sec_val, list):
            sec_text = _join_lines([f"[{sec_name}]"] + [f"- {x}" for x in sec_val])
        else:
            # String-like sections (논의)
            sec_text = _join_lines([f"[{sec_name}]", str(sec_val)])

        if _tlen(header + "\n\n" + sec_text) <= max_tokens:
            out.append(
                {
                    "text": header + "\n\n" + sec_text,
                    "source": source,
                    "type": "meeting",
                    "section": sec_name,
                    "title": m.get("제목", ""),
                    "datetime": m.get("일시", ""),
                    "chunk_index_in_doc": base_idx + ci,
                }
            )
            ci += 1
        else:
            for piece in _split_long_text(sec_text, body_budget, overlap):
                out.append(
                    {
                        "text": header + "\n\n" + piece,
                        "source": source,
                        "type": "meeting",
                        "section": sec_name,
                        "title": m.get("제목", ""),
                        "datetime": m.get("일시", ""),
                        "chunk_index_in_doc": base_idx + ci,
                    }
                )
                ci += 1

    return out


# ----------------------------
# Personal notes chunking
# ----------------------------
def _prefix_personal(p: Dict[str, Any]) -> str:
    return _join_lines(
        [
            "[PERSONAL]",
            f"제목: {p.get('제목', '')}",
            f"날짜: {p.get('날짜', '')}",
            f"프로젝트: {p.get('프로젝트', '')}",
        ]
    )


def _personal_chunks(
    p: Dict[str, Any],
    source: str,
    base_idx: int,
    max_tokens: int,
    overlap: int,
) -> List[Dict[str, Any]]:
    header = _prefix_personal(p)
    header_len = _tlen(header + "\n\n")
    body_budget = max(1, max_tokens - header_len)

    out: List[Dict[str, Any]] = []
    ci = 0

    sections: List[Tuple[str, Any]] = [
        ("관련메일", p.get("관련메일", [])),
        ("목표", p.get("목표", [])),
        ("참고자료", p.get("참고자료", [])),
        ("진행상태", p.get("진행상태", {})),
        ("메모", p.get("메모", "")),
        ("다음액션", p.get("다음액션", [])),
        ("태그", p.get("태그", [])),
    ]

    for sec_name, sec_val in sections:
        if not sec_val:
            continue

        if isinstance(sec_val, dict):  # 진행상태 {TODO/DOING/DONE}
            lines = [f"[{sec_name}]"]
            for k, v in sec_val.items():
                if isinstance(v, list):
                    for item in v:
                        lines.append(f"- {k}: {item}")
                else:
                    lines.append(f"- {k}: {v}")
            sec_text = _join_lines(lines)
        elif isinstance(sec_val, list):
            sec_text = _join_lines([f"[{sec_name}]"] + [f"- {x}" for x in sec_val])
        else:
            sec_text = _join_lines([f"[{sec_name}]", str(sec_val)])

        if _tlen(header + "\n\n" + sec_text) <= max_tokens:
            out.append(
                {
                    "text": header + "\n\n" + sec_text,
                    "source": source,
                    "type": "personal",
                    "section": sec_name,
                    "title": p.get("제목", ""),
                    "date": p.get("날짜", ""),
                    "project": p.get("프로젝트", ""),
                    "chunk_index_in_doc": base_idx + ci,
                }
            )
            ci += 1
        else:
            for piece in _split_long_text(sec_text, body_budget, overlap):
                out.append(
                    {
                        "text": header + "\n\n" + piece,
                        "source": source,
                        "type": "personal",
                        "section": sec_name,
                        "title": p.get("제목", ""),
                        "date": p.get("날짜", ""),
                        "project": p.get("프로젝트", ""),
                        "chunk_index_in_doc": base_idx + ci,
                    }
                )
                ci += 1

    return out


# ----------------------------
# Public entry point
# ----------------------------
def chunks_from_json_obj(
    data: Dict[str, Any],
    source: str = "hr_schedule.json",
    max_tokens: int = 800,
    overlap: int = 100,
) -> List[Dict[str, Any]]:
    """
    Build schema-aware chunks from a normalized HR JSON dict.
    Returns a list of chunk dicts with 'text' and metadata as described above.
    """
    out: List[Dict[str, Any]] = []
    base_idx = 0

    # emails
    for e in (data.get("emails") or []):
        ecs = _email_chunks(e, source, base_idx, max_tokens, overlap)
        out.extend(ecs)
        base_idx += len(ecs)

    # meetings
    for m in (data.get("meetings") or []):
        mcs = _meeting_chunks(m, source, base_idx, max_tokens, overlap)
        out.extend(mcs)
        base_idx += len(mcs)

    # personal notes
    for p in (data.get("personal_notes") or []):
        pcs = _personal_chunks(p, source, base_idx, max_tokens, overlap)
        out.extend(pcs)
        base_idx += len(pcs)

    return out
