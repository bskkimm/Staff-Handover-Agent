from pathlib import Path
from typing import Tuple, Optional
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

def _summary_dir() -> Path:
    # Staff-Handover-Agent/data/summary_report 디렉토리 사용
    staff_handover_agent_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = staff_handover_agent_dir / "data" / "summary_report"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def report_path(filename: str = "test_report.md") -> Path:
    return _summary_dir() / filename


def generate_and_save_report(filename: str = "test_report.md") -> Tuple[Optional[str], Path]:
    """Generate markdown report via summarizer and save to summary_report directory.

    Returns (markdown_content, saved_path).
    """
    from . import summarizer  # local import to avoid circulars on Streamlit boot

    markdown = summarizer.test_llm_markdown_output()
    if markdown:
        out_path = report_path(filename)
        summarizer.save_markdown_to_file(markdown, str(out_path))
        return markdown, out_path
    return None, report_path(filename)


def load_report(filename: str = "test_report.md") -> Optional[str]:
    p = report_path(filename)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None

