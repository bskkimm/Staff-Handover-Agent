from typing import Dict, Any
from pathlib import Path
import json

import streamlit as st

from handover.data_preprocess.preprocessor_test import process_all_files
from handover.utils import get_uploaded_files_data


def run_preprocess(files_data: Dict[str, str]) -> Dict[str, Any]:
    with st.spinner("📝 파일 전처리 중..."):
        processed_data = process_all_files(files_data)

    summary = {
        "total_files": len(files_data),
        "emails": len(processed_data.get("emails", [])),
        "meetings": len(processed_data.get("meetings", [])),
        "personal_notes": len(processed_data.get("personal_notes", [])),
    }

    # Convert to JSON-serializable structure
    def _to_jsonable(value):
        from datetime import datetime, date
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, list):
            return [_to_jsonable(v) for v in value]
        if isinstance(value, tuple):
            return [_to_jsonable(v) for v in value]
        if isinstance(value, dict):
            return {str(k): _to_jsonable(v) for k, v in value.items()}
        # Prefer custom to_dict
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            try:
                return _to_jsonable(to_dict())
            except Exception:
                pass
        # Fallback to __dict__
        d = getattr(value, "__dict__", None)
        if isinstance(d, dict):
            return {str(k): _to_jsonable(v) for k, v in d.items() if not k.startswith("_")}
        # Last resort string
        return str(value)

    serializable_data = _to_jsonable(processed_data)

    # Save preprocessed JSON
    out_dir = Path(__file__).resolve().parent.parent / "data" / "preprocessed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "preprocessed.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=2)

    return {"processed_data": serializable_data, "summary": summary, "json_path": str(out_path)}


def run_preprocess_from_db() -> Dict[str, Any]:
    """Fetch uploaded files from DB and preprocess them."""
    files_data = get_uploaded_files_data()
    if not files_data:
        st.warning("업로드된 파일이 없습니다.")
        return {"processed_data": {}, "summary": {}, "json_path": ""}
    return run_preprocess(files_data)


