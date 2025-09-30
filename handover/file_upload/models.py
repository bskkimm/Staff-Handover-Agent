# file_upload/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from pathlib import Path

Base = declarative_base()

class UploadedFile(Base):
    __tablename__ = 'uploaded_files'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)          # 저장된 파일명 (안전한 이름)
    original_name = Column(String(255), nullable=False)     # 원본 파일명
    file_type = Column(String(10), nullable=False)          # 파일 확장자 (pdf, txt, docx, csv)
    file_size = Column(Integer, nullable=False)             # 파일 크기 (바이트)
    file_hash = Column(String(32), nullable=False, unique=True)  # MD5 해시 (중복 체크용)
    upload_time = Column(DateTime, default=datetime.now)    # 업로드 시간
    file_path = Column(Text, nullable=False)                # 파일 저장 경로 (절대 경로)
    
    def __repr__(self):
        return f"<UploadedFile(id={self.id}, original_name='{self.original_name}')>"

def get_db_engine():
    """데이터베이스 엔진 생성 및 테이블 초기화"""
    db_path = os.getenv("UPLOAD_DB_PATH", "./Staff-Handover-Agent/data/file_metadata.db")
    
    # DB 파일이 저장될 디렉토리 생성
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    # SQLite 엔진 생성
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    
    # 모든 테이블 생성
    Base.metadata.create_all(bind=engine)
    
    return engine

def get_db_session():
    """데이터베이스 세션 반환"""
    engine = get_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()