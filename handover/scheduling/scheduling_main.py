"""Entry point for schedule extraction pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from handover.scheduling.config import (
    INPUT_FILE,
    OUT_MD,
    OUT_PNG,
    OUT_ICS,
    VIZ_DIR,
    GENERATE_TIMELINE_PNG,
    ensure_directories,
    get_client,
)
from handover.scheduling.llm_parser import read_input_txt
from handover.scheduling.schedule_builder import aggregate_events, build_markdown
from handover.scheduling.outputs import (
    save_markdown,
    visualize_calendar,
    write_ics,
    render_monthly_bars,
)


def main() -> None:
    ensure_directories()

    files_with_text: List[Tuple[str, str]] = read_input_txt(Path(INPUT_FILE))
    if not files_with_text:
        print("처리할 TXT가 없습니다.")
        return

    # 추출 파이프라인을 구동해 LLM 파싱→집계→산출물 생성을 수행한다.
    client = get_client()
    groups = aggregate_events(files_with_text, client)
    markdown = build_markdown(groups)
    save_markdown(markdown, OUT_MD)

    if GENERATE_TIMELINE_PNG:
        visualize_calendar(markdown, OUT_PNG)

    write_ics(markdown, OUT_ICS)
    render_monthly_bars(OUT_MD, VIZ_DIR)


if __name__ == "__main__":
    main()
