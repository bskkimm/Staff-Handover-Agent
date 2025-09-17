import re
import os
import glob
from datetime import datetime, timedelta
from typing import List

class SimpleEmailPreprocessor:
    def __init__(self, reference_date: str = None):
        """
        Args:
            reference_date: 기준 날짜 (YYYY-MM-DD 형식)
        """
        if reference_date:
            self.reference_date = datetime.strptime(reference_date, "%Y-%m-%d")
        else:
            self.reference_date = datetime.now()
    
    def preprocess_email(self, email_content: str) -> str:
        """이메일을 간단한 텍스트 형태로 전처리"""
        
        # 1. 이메일 체인을 개별 이메일로 분리
        email_parts = re.split(r'-----Original Message-----', email_content)
        
        processed_emails = []
        for part in reversed(email_parts):  # 시간순 정렬 (오래된 것부터)
            if part.strip():
                processed = self._process_single_email(part.strip())
                if processed:
                    processed_emails.append(processed)
        
        # 2. 모든 이메일을 하나의 텍스트로 결합
        return '\n\n'.join(processed_emails)
    
    def _process_single_email(self, email_part: str) -> str:
        """개별 이메일 처리"""
        lines = email_part.split('\n')
        
        # 메타데이터 추출
        metadata = {}
        content_start = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if line.startswith('From:'):
                metadata['from'] = self._clean_email_field(line[5:].strip())
            elif line.startswith('To:'):
                metadata['to'] = self._clean_email_field(line[3:].strip())
            elif line.startswith('Cc:'):
                metadata['cc'] = self._clean_email_field(line[3:].strip())
            elif line.startswith('Date:'):
                metadata['date'] = self._clean_date_field(line[5:].strip())
            elif line.startswith('Subject:'):
                metadata['subject'] = self._clean_subject_field(line[8:].strip())
            elif line.startswith('Message-ID:'):
                continue  # Message-ID는 건너뛰기
            elif not line or (i > 0 and not any(line.startswith(prefix) for prefix in ['From:', 'To:', 'Cc:', 'Date:', 'Subject:', 'Message-ID:'])):
                content_start = i
                break
        
        # 본문 내용 추출 및 정리
        content_lines = lines[content_start:]
        content = '\n'.join(content_lines).strip()
        
        # 발신자 정보 제거 (예: "김민수 드림", "감사합니다." 등 인사말 정리)
        content = self._clean_content(content)
        
        # 최종 형태로 조립
        result_parts = []
        
        if 'to' in metadata and metadata['to']:
            result_parts.append(f"수신인: {metadata['to']}")
        
        if 'cc' in metadata and metadata['cc']:
            result_parts.append(f"참조: {metadata['cc']}")
        
        if 'date' in metadata and metadata['date']:
            result_parts.append(f"날짜: {metadata['date']}")
        
        if 'subject' in metadata and metadata['subject']:
            result_parts.append(f"제목: {metadata['subject']}")
        
        if content:
            result_parts.append(f"내용:\n{content}")
        
        return '\n'.join(result_parts)
    
    def _clean_email_field(self, field: str) -> str:
        """이메일 주소에서 이름만 추출"""
        names = []
        parts = field.split(',')
        
        for part in parts:
            part = part.strip()
            if '<' in part and '>' in part:
                name = part.split('<')[0].strip()
                if name:
                    names.append(name)
            else:
                if '@' not in part:  # 이메일 주소가 아닌 경우만 추가
                    names.append(part)
        
        return ', '.join(names)
    
    def _clean_date_field(self, date_str: str) -> str:
        """날짜 필드를 YYYY-MM-DD, HH:MM 형식으로 정리"""
        try:
            # "Thu, 18 Jul 2024 17:00 +0900 (KST)" → "2024-07-18, 17:00"
            match = re.search(r'(\d{1,2}) (\w+) (\d{4}) (\d{2}):(\d{2})', date_str)
            if match:
                day, month, year, hour, minute = match.groups()
                
                month_map = {
                    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                    'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                    'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                }
                
                month_num = month_map.get(month, '01')
                return f"{year}-{month_num}-{day.zfill(2)}, {hour}:{minute}"
            
            return date_str
        except:
            return date_str
    
    def _clean_subject_field(self, subject: str) -> str:
        """제목에서 Re: 제거 및 공백 정리"""
        # "Re: Re: [보상] 킥오프" → "[보상] 킥오프"
        cleaned = re.sub(r'^(Re:\s*)+', '', subject, flags=re.IGNORECASE)
        return cleaned.strip()
    
    def _clean_content(self, content: str) -> str:
        """본문 내용 정리"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 불필요한 인사말이나 서명 제거
            if any(phrase in line for phrase in [
                '드림', '감사합니다', '안녕하세요', '수고하세요', 
                '좋은 하루', '문의사항', '연락드리겠습니다'
            ]) and len(line) < 20:  # 짧은 인사말만 제거
                continue
            
            if line:  # 빈 줄이 아닌 경우만 추가
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

def extract_earliest_date(processed_content: str) -> str:
    """
    전처리된 내용에서 가장 이른 날짜를 추출하여 정렬 기준으로 사용
    
    Args:
        processed_content: 전처리된 이메일 내용
        
    Returns:
        YYYY-MM-DD HH:MM 형식의 날짜 문자열
    """
    # 날짜 패턴 찾기: "날짜: YYYY-MM-DD, HH:MM"
    date_pattern = r'날짜: (\d{4}-\d{2}-\d{2}, \d{2}:\d{2})'
    dates = re.findall(date_pattern, processed_content)
    
    if dates:
        # 가장 이른 날짜 반환 (정렬하면 첫 번째가 가장 이름)
        return min(dates)
    else:
        # 날짜를 찾을 수 없으면 기본값 반환
        return "1900-01-01, 00:00"

def process_email_directory(directory_path: str, reference_date: str = "2025-02-06") -> str:
    """
    디렉토리 내의 모든 txt 파일을 읽어서 전처리 후 시간순으로 합치기
    
    Args:
        directory_path: 이메일 파일들이 있는 디렉토리 경로
        reference_date: 상대 날짜 변환의 기준 날짜
        
    Returns:
        시간순으로 정렬되어 합쳐진 전처리 결과
    """
    
    # 디렉토리에서 txt 파일들 찾기
    txt_files = glob.glob(os.path.join(directory_path, "*.txt"))
    
    if not txt_files:
        print(f"❌ {directory_path} 디렉토리에 txt 파일이 없습니다.")
        return ""
    
    print(f"📁 {len(txt_files)}개의 txt 파일을 발견했습니다:")
    for file in txt_files:
        print(f"  - {os.path.basename(file)}")
    
    preprocessor = SimpleEmailPreprocessor(reference_date=reference_date)
    processed_files = []
    
    # 각 파일별로 처리
    for file_path in txt_files:
        try:
            print(f"\n📄 처리 중: {os.path.basename(file_path)}")
            
            # 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                email_content = f.read()
            
            # 전처리 수행
            processed_content = preprocessor.preprocess_email(email_content)
            
            # 날짜 추출 (첫 번째 이메일의 날짜를 기준으로 정렬용)
            timestamp = extract_earliest_date(processed_content)
            
            processed_files.append({
                'filename': os.path.basename(file_path),
                'content': processed_content,
                'timestamp': timestamp,
                'file_path': file_path
            })
            
            print(f"완료 (날짜: {timestamp})")
            
        except Exception as e:
            print(f"실패: {str(e)}")
            continue
    
    if not processed_files:
        print("처리된 파일이 없습니다.")
        return ""
    
    # 시간순 정렬 (오래된 것부터)
    processed_files.sort(key=lambda x: x['timestamp'])
    
    print(f"\n시간순 정렬 결과:")
    for i, file_info in enumerate(processed_files, 1):
        print(f"  {i}. {file_info['filename']} ({file_info['timestamp']})")
    
    # 시간순으로 합치기
    final_content = []
    final_content.append(f"# 인수인계 문서 통합 정리")
    final_content.append(f"총 {len(processed_files)}개 파일 처리 완료")
    final_content.append(f"처리 기준일: {reference_date}")
    final_content.append(f"처리 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    final_content.append("")
    
    for i, file_info in enumerate(processed_files, 1):
        final_content.append(f"{'='*80}")
        final_content.append(f"파일 {i}: {file_info['filename']} ")
        final_content.append(f"{'='*80}")
        final_content.append(file_info['content'])
        final_content.append("")
    
    return "\n".join(final_content)

# 테스트 함수 - 디렉토리 기반으로 수정
def test_directory_processing():
    """디렉토리 내 실제 파일들로 전처리 테스트"""
    
    # 현재 작업 디렉토리 표시
    current_dir = os.getcwd()
    print(f"현재 작업 디렉토리: {current_dir}")
    
    # 사용자가 직접 입력할 디렉토리 경로
    directory_path = input("이메일 파일들이 있는 디렉토리 경로를 입력하세요 (예: ./emails 또는 C:/my_emails): ").strip()
    
    # 빈 입력시 현재 디렉토리에서 찾기
    if not directory_path:
        directory_path = "."
        print("입력이 없어서 현재 디렉토리에서 txt 파일을 찾습니다.")
    
    # 디렉토리 존재 확인
    if not os.path.exists(directory_path):
        print(f"디렉토리 '{directory_path}'가 존재하지 않습니다.")
        return
    
    # 기준 날짜 입력
    reference_date = input("기준 날짜를 입력하세요 (YYYY-MM-DD 형식, 빈값이면 2025-02-06): ").strip()
    if not reference_date:
        reference_date = "2025-02-06"
    
    print("=" * 80)
    print("디렉토리 기반 이메일 전처리 시작")
    print("=" * 80)
    
    # 처리 실행
    result = process_email_directory(directory_path, reference_date)
    
    if result:
        print("\n" + "=" * 80)
        print("전처리 결과")
        print("=" * 80)
        print(result)
        
        # 결과를 파일로 저장할지 묻기
        save_choice = input("\n결과를 파일로 저장하시겠습니까? (y/n): ").strip().lower()
        if save_choice in ['y', 'yes', '예']:
            output_filename = input("출력 파일명을 입력하세요 (기본값: processed_emails.txt): ").strip()
            if not output_filename:
                output_filename = "processed_emails.txt"
            
            try:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"✅ 결과가 '{output_filename}' 파일로 저장되었습니다.")
            except Exception as e:
                print(f"❌ 파일 저장 실패: {str(e)}")
    else:
        print("\n❌ 처리할 파일이 없습니다.")

if __name__ == "__main__":
    test_directory_processing()