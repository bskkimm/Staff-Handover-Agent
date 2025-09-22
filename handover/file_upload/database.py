# file_upload/database.py
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from file_upload.models import UploadedFile, get_db_session

class FileDatabase:
    def __init__(self):
        self.upload_dir = os.getenv("UPLOAD_DIR", "./data/uploads")
        # 업로드 디렉토리 생성
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
    
    def save_file(self, file_buffer: bytes, original_name: str) -> Optional[UploadedFile]:
        """파일을 디스크에 저장하고 DB에 메타데이터 등록"""
        try:
            # 파일 해시 계산 (중복 체크용)
            file_hash = hashlib.md5(file_buffer).hexdigest()
            
            # 중복 파일 체크
            if self.is_duplicate(file_hash):
                return None  # 이미 존재하는 파일
            
            # 안전한 파일명 생성 (타임스탬프 + 해시 + 확장자)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_ext = os.path.splitext(original_name)[1]
            safe_filename = f"{timestamp}_{file_hash[:8]}{file_ext}"
            file_path = os.path.join(self.upload_dir, safe_filename)
            
            session = get_db_session()
            try:
                # 1. 실제 파일을 디스크에 저장
                with open(file_path, 'wb') as f:
                    f.write(file_buffer)
                
                # 2. 메타데이터를 DB에 저장
                file_record = UploadedFile(
                    filename=safe_filename,
                    original_name=original_name,
                    file_type=os.path.splitext(original_name)[1].lower().lstrip('.'),
                    file_size=len(file_buffer),
                    file_hash=file_hash,
                    file_path=os.path.abspath(file_path)  # 절대 경로로 저장
                )
                
                session.add(file_record)
                session.commit()
                session.refresh(file_record)
                return file_record
                
            except Exception as e:
                session.rollback()
                # 저장된 파일 삭제 (롤백)
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise e
            finally:
                session.close()
                
        except Exception as e:
            raise Exception(f"파일 저장 중 오류 발생: {str(e)}")
    
    def get_all_files(self) -> List[UploadedFile]:
        """모든 업로드된 파일 목록 조회 (최신순)"""
        session = get_db_session()
        try:
            return session.query(UploadedFile).order_by(UploadedFile.upload_time.desc()).all()
        finally:
            session.close()
    
    def get_file_by_id(self, file_id: int) -> Optional[UploadedFile]:
        """ID로 특정 파일 조회"""
        session = get_db_session()
        try:
            return session.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        finally:
            session.close()
    
    def delete_file(self, file_id: int) -> bool:
        """파일과 메타데이터 삭제"""
        session = get_db_session()
        try:
            file_record = session.query(UploadedFile).filter(UploadedFile.id == file_id).first()
            if file_record:
                # 1. 실제 파일 삭제
                if os.path.exists(file_record.file_path):
                    os.remove(file_record.file_path)
                
                # 2. DB에서 메타데이터 삭제
                session.delete(file_record)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_all_files(self) -> int:
        """모든 파일과 메타데이터 삭제"""
        files = self.get_all_files()
        deleted_count = 0
        
        for file_record in files:
            if self.delete_file(file_record.id):
                deleted_count += 1
        
        return deleted_count
    
    def is_duplicate(self, file_hash: str) -> bool:
        """파일 해시로 중복 체크"""
        session = get_db_session()
        try:
            exists = session.query(UploadedFile).filter(UploadedFile.file_hash == file_hash).first()
            return exists is not None
        finally:
            session.close()
    
    def get_files_by_type(self, file_type: str) -> List[UploadedFile]:
        """파일 타입별 조회 (전처리팀이 사용할 수 있는 유틸리티)"""
        session = get_db_session()
        try:
            return session.query(UploadedFile).filter(UploadedFile.file_type == file_type).all()
        finally:
            session.close()
    
    def get_files_after_date(self, date: datetime) -> List[UploadedFile]:
        """특정 날짜 이후 업로드된 파일들 조회"""
        session = get_db_session()
        try:
            return session.query(UploadedFile).filter(UploadedFile.upload_time >= date).all()
        finally:
            session.close()

# 전역 인스턴스 (싱글톤 패턴)
file_db = FileDatabase()