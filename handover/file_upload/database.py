# file_upload/database.py
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from file_upload.models import UploadedFile, get_db_session

class FileDatabase:
    def __init__(self):
        # 기본 데이터 루트 디렉토리
        self.data_root = Path(os.getenv("DATA_ROOT", "./data"))
        self.data_root.mkdir(parents=True, exist_ok=True)

    def _get_session_upload_dir(self, session_id: str) -> Path:
        """세션별 업로드 디렉토리 경로 반환"""
        if not session_id:
            # session_id 없으면 레거시 경로 (하위 호환성)
            return self.data_root / "uploads"
        session_dir = self.data_root / "sessions" / session_id / "uploads"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    
    def save_file(self, file_buffer: bytes, original_name: str, session_id: str = None) -> Optional[UploadedFile]:
        """파일을 디스크에 저장하고 DB에 메타데이터 등록"""
        try:
            print(f"[DEBUG] save_file 시작: {original_name}, session_id={session_id}")

            # 파일 해시 계산 (중복 체크용)
            file_hash = hashlib.md5(file_buffer).hexdigest()
            print(f"[DEBUG] 파일 해시: {file_hash[:8]}")

            # 중복 파일 체크 (같은 세션 내에서만)
            if self.is_duplicate(file_hash, session_id):
                print(f"[DEBUG] 중복 파일 감지: {original_name}")
                return None  # 이미 존재하는 파일

            # 세션별 업로드 디렉토리 가져오기
            upload_dir = self._get_session_upload_dir(session_id)
            print(f"[DEBUG] 업로드 디렉토리: {upload_dir}")

            # 안전한 파일명 생성 (타임스탬프 + 해시 + 확장자)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_ext = os.path.splitext(original_name)[1]
            safe_filename = f"{timestamp}_{file_hash[:8]}{file_ext}"
            file_path = upload_dir / safe_filename
            print(f"[DEBUG] 저장 경로: {file_path}")
            
            session = get_db_session()
            try:
                # 1. 실제 파일을 디스크에 저장
                print(f"[DEBUG] 파일 쓰기 시작...")
                with open(str(file_path), 'wb') as f:
                    f.write(file_buffer)
                print(f"[DEBUG] 파일 쓰기 완료: {len(file_buffer)} bytes")
                print(f"[DEBUG] 파일 존재 확인: {os.path.exists(file_path)}")

                # 2. 메타데이터를 DB에 저장
                print(f"[DEBUG] DB 저장 시작...")
                file_record = UploadedFile(
                    filename=safe_filename,
                    original_name=original_name,
                    file_type=os.path.splitext(original_name)[1].lower().lstrip('.'),
                    file_size=len(file_buffer),
                    file_hash=file_hash,
                    file_path=os.path.abspath(file_path),  # 절대 경로로 저장
                    session_id=session_id  # 세션 ID 추가
                )
                
                session.add(file_record)
                session.commit()
                session.refresh(file_record)
                print(f"[DEBUG] DB 저장 완료! ID={file_record.id}")
                return file_record

            except Exception as e:
                print(f"[DEBUG] 오류 발생: {e}")
                session.rollback()
                # 저장된 파일 삭제 (롤백)
                if os.path.exists(file_path):
                    print(f"[DEBUG] 파일 롤백 삭제: {file_path}")
                    os.remove(file_path)
                raise e
            finally:
                session.close()
                
        except Exception as e:
            raise Exception(f"파일 저장 중 오류 발생: {str(e)}")
    
    def get_all_files(self, session_id: str = None) -> List[UploadedFile]:
        """모든 업로드된 파일 목록 조회 (최신순)"""
        session = get_db_session()
        try:
            query = session.query(UploadedFile)
            if session_id:
                query = query.filter(UploadedFile.session_id == session_id)
            return query.order_by(UploadedFile.upload_time.desc()).all()
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
    
    def is_duplicate(self, file_hash: str, session_id: str = None) -> bool:
        """파일 해시로 중복 체크 (같은 세션 내에서만)"""
        session = get_db_session()
        try:
            query = session.query(UploadedFile).filter(UploadedFile.file_hash == file_hash)
            if session_id:
                query = query.filter(UploadedFile.session_id == session_id)
            exists = query.first()
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