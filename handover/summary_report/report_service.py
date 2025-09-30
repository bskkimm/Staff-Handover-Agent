from pathlib import Path
from typing import Tuple, Optional


def _summary_dir() -> Path:
    return Path(__file__).resolve().parent


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


