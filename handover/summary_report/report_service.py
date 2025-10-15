from pathlib import Path
from typing import Tuple, Optional
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

def _summary_dir(session_id: str = None) -> Path:
    staff_handover_agent_dir = Path(__file__).resolve().parent.parent.parent
    if session_id:
        data_dir = staff_handover_agent_dir / "data" / "sessions" / session_id / "summary_report"
    else:
        data_dir = staff_handover_agent_dir / "data" / "summary_report"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def report_path(filename: str = "test_report.md", session_id: str = None) -> Path:
    return _summary_dir(session_id) / filename


def generate_and_save_report(filename: str = "test_report.md", session_id: str = None) -> Tuple[Optional[str], Path]:
    """Generate markdown report via summarizer and save to summary_report directory.

    Returns (markdown_content, saved_path).
    """
    from . import summarizer

    markdown = summarizer.test_llm_markdown_output(session_id)
    if markdown:
        out_path = report_path(filename, session_id)
        summarizer.save_markdown_to_file(markdown, str(out_path))
        return markdown, out_path
    return None, report_path(filename, session_id)


def load_report(filename: str = "test_report.md") -> Optional[str]:
    p = report_path(filename)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None

