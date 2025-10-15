# auth/database.py
"""
인증 및 세션 관리 데이터베이스
"""
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from .models import User, HandoverSession


class AuthDatabase:
    """사용자 인증 및 세션 관리 DB"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Staff-Handover-Agent/data/auth.db
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "auth.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        """DB 연결"""
        return sqlite3.connect(str(self.db_path))

    def _init_db(self):
        """테이블 초기화"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # users 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    employee_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # handover_sessions 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS handover_sessions (
                    session_id TEXT PRIMARY KEY,
                    transferor_id TEXT NOT NULL,
                    receiver_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    FOREIGN KEY (transferor_id) REFERENCES users(employee_id),
                    FOREIGN KEY (receiver_id) REFERENCES users(employee_id)
                )
            """)

            conn.commit()

    # ============ User 관리 ============

    def get_or_create_user(self, employee_id: str, name: str = None) -> User:
        """사용자 조회 또는 생성"""
        user = self.get_user(employee_id)
        if user:
            return user

        # 신규 사용자 생성
        if name is None:
            name = f"사원{employee_id}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO users (employee_id, name, created_at) VALUES (?, ?, ?)",
                (employee_id, name, now)
            )
            conn.commit()

        return User(employee_id=employee_id, name=name, created_at=datetime.fromisoformat(now))

    def get_user(self, employee_id: str) -> Optional[User]:
        """사용자 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT employee_id, name, created_at FROM users WHERE employee_id = ?",
                (employee_id,)
            )
            row = cursor.fetchone()

            if row:
                return User(
                    employee_id=row[0],
                    name=row[1],
                    created_at=datetime.fromisoformat(row[2])
                )
            return None

    # ============ Session 관리 ============

    def create_session(self, transferor_id: str, receiver_id: str) -> HandoverSession:
        """인계/인수 세션 생성"""
        # 사용자 생성/확인
        self.get_or_create_user(transferor_id)
        self.get_or_create_user(receiver_id)

        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO handover_sessions
                   (session_id, transferor_id, receiver_id, created_at, status)
                   VALUES (?, ?, ?, ?, 'active')""",
                (session_id, transferor_id, receiver_id, now)
            )
            conn.commit()

        return HandoverSession(
            session_id=session_id,
            transferor_id=transferor_id,
            receiver_id=receiver_id,
            created_at=datetime.fromisoformat(now),
            status='active'
        )

    def get_session(self, session_id: str) -> Optional[HandoverSession]:
        """세션 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT session_id, transferor_id, receiver_id, created_at, status
                   FROM handover_sessions WHERE session_id = ?""",
                (session_id,)
            )
            row = cursor.fetchone()

            if row:
                return HandoverSession(
                    session_id=row[0],
                    transferor_id=row[1],
                    receiver_id=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    status=row[4]
                )
            return None

    def get_sessions_by_receiver(self, receiver_id: str) -> List[HandoverSession]:
        """인수자로 지정된 세션 목록 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT session_id, transferor_id, receiver_id, created_at, status
                   FROM handover_sessions
                   WHERE receiver_id = ? AND status = 'active'
                   ORDER BY created_at DESC""",
                (receiver_id,)
            )
            rows = cursor.fetchall()

            return [
                HandoverSession(
                    session_id=row[0],
                    transferor_id=row[1],
                    receiver_id=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    status=row[4]
                )
                for row in rows
            ]

    def get_sessions_by_transferor(self, transferor_id: str) -> List[HandoverSession]:
        """인계자로 생성한 세션 목록 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT session_id, transferor_id, receiver_id, created_at, status
                   FROM handover_sessions
                   WHERE transferor_id = ?
                   ORDER BY created_at DESC""",
                (transferor_id,)
            )
            rows = cursor.fetchall()

            return [
                HandoverSession(
                    session_id=row[0],
                    transferor_id=row[1],
                    receiver_id=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    status=row[4]
                )
                for row in rows
            ]


# 싱글톤 인스턴스
auth_db = AuthDatabase()
