# auth/models.py
"""
사용자 인증 및 인계/인수 세션 관리를 위한 데이터 모델
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """사용자 (사번 기반)"""
    employee_id: str  # 사번 (PK)
    name: str
    created_at: datetime


@dataclass
class HandoverSession:
    """인계/인수 세션"""
    session_id: str  # UUID
    transferor_id: str  # 인계자 사번
    receiver_id: str  # 인수자 사번
    created_at: datetime
    status: str  # 'active', 'completed', 'archived'

    def __post_init__(self):
        if self.status not in ('active', 'completed', 'archived'):
            raise ValueError(f"Invalid status: {self.status}")
