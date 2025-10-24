"""Configuration and shared utilities for schedule extraction."""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Tuple

from dotenv import load_dotenv
from openai import AzureOpenAI

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent

# 프로젝트 실행 동안 공유 환경변수를 한 번만 불러온다.
load_dotenv(PROJECT_ROOT / ".env")

# ✅ 가장 최근 세션 폴더 찾기
def get_latest_session_dir() -> Path:
    """가장 최근에 수정된 세션 폴더를 반환합니다."""
    sessions_dir = PROJECT_ROOT / "data" / "sessions"
    if not sessions_dir.exists():
        raise RuntimeError(f"세션 디렉토리가 없습니다: {sessions_dir}")
    
    # 모든 세션 폴더를 찾아서 수정 시간 기준으로 정렬
    session_folders = [d for d in sessions_dir.iterdir() if d.is_dir()]
    if not session_folders:
        raise RuntimeError(f"세션 폴더가 없습니다: {sessions_dir}")
    
    # 가장 최근 폴더 선택
    latest_session = max(session_folders, key=lambda d: d.stat().st_mtime)
    return latest_session

# 스케줄 산출물들이 공통으로 사용하는 기준 경로.
SCHED_DIR = BASE_DIR

# ✅ 세션 기반 경로 사용
try:
    LATEST_SESSION = get_latest_session_dir()
    INPUT_FILE = LATEST_SESSION / "preprocessed_data" / "No_1.txt"
    print(f"[INFO] 사용할 세션: {LATEST_SESSION.name}")
    print(f"[INFO] 입력 파일: {INPUT_FILE}")
except Exception as e:
    print(f"[WARN] 세션 폴더를 찾을 수 없습니다: {e}")
    INPUT_FILE = PROJECT_ROOT / "data" / "preprocessed_data" / "No_1.txt"

# Staff-Handover-Agent/data/schedule 디렉토리 사용
OUT_DIR = PROJECT_ROOT / "data" / "schedule"
VIZ_DIR = OUT_DIR / "out_cal_bars"
OUT_MD = OUT_DIR / "combined_schedule.md"
OUT_PNG = OUT_DIR / "combined_schedule_timeline.png"
OUT_ICS = OUT_DIR / "combined_schedule.ics"
GENERATE_TIMELINE_PNG = False

KST = ZoneInfo("Asia/Seoul")
TODAY_STR = datetime.now(KST).strftime("%Y-%m-%d")

API_KEY = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
API_VERSION = (os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-01").strip()
AZURE_ENDPOINT = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip()
AZURE_CHAT_DEPLOYMENT = (os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or "aicore-gpt4o").strip()

if not API_KEY or not AZURE_ENDPOINT or not AZURE_CHAT_DEPLOYMENT:
    raise RuntimeError("필수 Azure OpenAI 환경변수가 설정되지 않았습니다.")


def ensure_directories() -> Tuple[Path, Path]:
    # 후속 작업이 경로 존재를 가정할 수 있도록 출력 폴더를 미리 만든다.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    VIZ_DIR.mkdir(parents=True, exist_ok=True)
    return OUT_DIR, VIZ_DIR


@lru_cache()
def get_client() -> AzureOpenAI:
    # 인증 과정을 반복하지 않도록 Azure 클라이언트를 한 번 생성해 재사용한다.
    return AzureOpenAI(
        api_key=API_KEY,
        api_version=API_VERSION,
        azure_endpoint=AZURE_ENDPOINT,
    )