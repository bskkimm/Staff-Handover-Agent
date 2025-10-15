"""
DB 마이그레이션: session_id 컬럼 추가
"""
import sqlite3
from pathlib import Path

db_path = Path("data/file_metadata.db")

if not db_path.exists():
    print("DB 파일이 없습니다. 마이그레이션 불필요.")
    exit(0)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

try:
    # session_id 컬럼이 이미 있는지 확인
    cursor.execute("PRAGMA table_info(uploaded_files)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'session_id' in columns:
        print("✅ session_id 컬럼이 이미 존재합니다.")
    else:
        # session_id 컬럼 추가 (NULL 허용)
        cursor.execute("ALTER TABLE uploaded_files ADD COLUMN session_id TEXT")
        conn.commit()
        print("✅ session_id 컬럼을 추가했습니다.")

    print("\n현재 테이블 구조:")
    cursor.execute("PRAGMA table_info(uploaded_files)")
    for col in cursor.fetchall():
        print(f"  - {col[1]} ({col[2]})")

except Exception as e:
    print(f"❌ 마이그레이션 실패: {e}")
    conn.rollback()
finally:
    conn.close()

print("\n마이그레이션 완료!")
