from typing import Dict, Any
import os, json
from pathlib import Path
import streamlit as st

from openai import AzureOpenAI
from dotenv import load_dotenv


def _load_preprocessed_json() -> Dict[str, Any]:
    json_path = Path(__file__).resolve().parent.parent / "data" / "preprocessed" / "preprocessed.json"
    if not json_path.exists():
        return {}
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _summarize_from_json(data: Dict[str, Any]) -> str:
    load_dotenv()
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-02-01",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
    system = "당신은 HR 인수인계 보고서를 작성하는 보조자입니다. 명확한 마크다운으로 구조화하세요."
    user = (
        "다음 전처리된 JSON 데이터를 기반으로 인수인계용 요약 보고서를 마크다운으로 작성하세요.\n"
        "필수 섹션: 프로젝트 개요, 진행 현황, 주요 일정, 미해결 과제, 인수인계 체크리스트.\n\n"
        f"JSON:\n{json.dumps(data, ensure_ascii=False)[:100000]}"
    )
    resp = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "aicore-gpt4o"),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=1500,
        temperature=0.2,
    )
    return resp.choices[0].message.content


def build_report() -> Dict[str, Any]:
    data = _load_preprocessed_json()
    if not data:
        st.error("전처리 JSON이 없습니다. 먼저 전처리를 실행하세요.")
        return {"success": False}
    md = _summarize_from_json(data)
    if not md:
        return {"success": False}
    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / "report.md"
    out_md.write_text(md, encoding="utf-8")
    return {"success": True, "markdown": str(out_md)}


