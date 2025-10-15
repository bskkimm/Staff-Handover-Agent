"""
DB 강제 초기화 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from handover.file_upload.models import get_db_engine, Base

print("DB 초기화 시작...")
engine = get_db_engine()
print(f"엔진 생성 완료: {engine.url}")

# 테이블 강제 생성
Base.metadata.create_all(bind=engine)
print("테이블 생성 완료!")

# DB 파일 확인
db_path = project_root / "data" / "file_metadata.db"
if db_path.exists():
    print(f"[OK] DB 파일 생성 확인: {db_path}")
    print(f"   파일 크기: {db_path.stat().st_size} bytes")
else:
    print(f"[ERROR] DB 파일이 생성되지 않았습니다: {db_path}")
