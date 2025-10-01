"""
이메일 파싱 관련 모듈
"""
import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Email:
    """이메일 데이터를 담는 클래스"""
    date: str
    subject: str
    sender: str
    recipients: List[str]
    cc: List[str]
    content: str

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            '날짜': self.date,
            '제목': self.subject,
            '발신자': self.sender,
            '수신자': ', '.join(self.recipients),
            '참조': ', '.join(self.cc),
            '내용': self.content
        }
    
    def __str__(self) -> str:
        """포맷팅된 문자열 출력"""
        return f"""날짜: {self.date}
제목: {self.subject}
발신자: {self.sender}
수신자: {', '.join(self.recipients)}
참조: {', '.join(self.cc) if self.cc else '없음'}
내용: {self.content}"""


def parse_email(email_text: str) -> List[Email]:
    """
    이메일 텍스트를 파싱하여 Email 객체 리스트로 반환
    Reply 메일과 Original 메일을 분리하여 처리
    """
    emails = []
    
    # Reply와 Original Message를 분리
    parts = re.split(r'-----Original Message-----', email_text)
    
    for part in parts:
        if not part.strip():
            continue
            
        email = parse_single_email(part)
        if email:
            emails.append(email)
    
    return emails


def parse_single_email(email_part: str) -> Optional[Email]:
    """단일 이메일 파트를 파싱"""
    try:
        # 날짜 추출
        date_match = re.search(r'Date:\s*([^\n]+)', email_part)
        date = clean_date(date_match.group(1)) if date_match else ""
        
        # 제목 추출 (Re:, RE:, Fwd: 등 제거)
        subject_match = re.search(r'Subject:\s*([^\n]+)', email_part)
        subject = clean_subject(subject_match.group(1)) if subject_match else ""
        
        # 발신자 추출 (이메일 주소 제거, 이름만 추출)
        from_match = re.search(r'From:\s*([^<]+)<([^>]+)>', email_part)
        if from_match:
            sender = from_match.group(1).strip()  # 이름만
        else:
            from_match = re.search(r'From:\s*([^\n]+)', email_part)
            sender = from_match.group(1).strip() if from_match else ""
        
        # 수신자 추출 (이름만)
        to_match = re.search(r'To:\s*([^\n]+)', email_part)
        recipients = parse_recipients_names_only(to_match.group(1)) if to_match else []
        
        # 참조 추출 (이름만)
        cc_match = re.search(r'Cc:\s*([^\n]+)', email_part)
        cc = parse_recipients_names_only(cc_match.group(1)) if cc_match else []
        
        # 내용 추출 및 정리
        content = extract_and_clean_content(email_part)
        
        return Email(
            date=date,
            subject=subject,
            sender=sender,
            recipients=recipients,
            cc=cc,
            content=content
        )
    except Exception as e:
        print(f"이메일 파싱 오류: {e}")
        return None


def clean_date(date_str: str) -> str:
    """날짜 문자열 정리 - 간단한 형식으로 변환"""
    # 예: "Thu, 18 Jul 2024 17:00 +0900 (KST)" -> "2024-07-18 17:00"
    try:
        # 다양한 날짜 형식 처리
        date_patterns = [
            r'(\w+),\s*(\d+)\s+(\w+)\s+(\d{4})\s+(\d{2}:\d{2})',
            r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2}:\d{2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                # 첫 번째 패턴 매칭 시
                if len(match.groups()) == 5:
                    months = {
                        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                        'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                    }
                    month = months.get(match.group(3), match.group(3))
                    return f"{match.group(4)}-{month}-{match.group(2).zfill(2)} {match.group(5)}"
                # 두 번째 패턴 매칭 시
                else:
                    return date_str.split(' +')[0]  # 시간대 정보 제거
        
        return date_str.split(' +')[0] if ' +' in date_str else date_str
    except:
        return date_str


def clean_subject(subject: str) -> str:
    """제목에서 불필요한 접두사 제거"""
    # Re:, RE:, Fwd:, FW:, [태그] 등 제거
    cleaned = re.sub(r'^(Re:|RE:|Fwd:|FW:|Fw:)\s*', '', subject.strip())
    cleaned = re.sub(r'^\[.*?\]\s*', '', cleaned)  # [보상] 같은 태그 제거
    return cleaned.strip()


def parse_recipients_names_only(recipients_str: str) -> List[str]:
    """수신자/참조 문자열에서 이름만 추출"""
    recipients = []
    # 이메일 주소 패턴으로 이름만 추출
    matches = re.findall(r'([^<,]+)<[^>]+>', recipients_str)
    
    for name in matches:
        recipients.append(name.strip())
    
    # 매칭이 없으면 이메일 주소가 없는 경우로 간주
    if not recipients and recipients_str:
        # @ 기호가 있으면 이메일만 있는 경우
        if '@' in recipients_str:
            # 이메일 주소만 있으면 빈 리스트 반환
            return []
        # 이름만 있는 경우
        recipients = [r.strip() for r in recipients_str.split(',')]
    
    return recipients


def extract_and_clean_content(email_part: str) -> str:
    """이메일 본문 내용 추출 및 정리"""
    # Message-ID 이후의 내용을 본문으로 간주
    content_match = re.search(r'Message-ID:[^\n]+\n+(.*)', email_part, re.DOTALL)
    if content_match:
        content = content_match.group(1).strip()
        
        # 인사말 제거 (안녕하세요로 시작하는 첫 줄)
        lines = content.split('\n')
        cleaned_lines = []
        
        for i, line in enumerate(lines):
            # 첫 번째 줄의 안녕하세요 제거
            if i == 0 and '안녕하세요' in line:
                # 안녕하세요 다음 내용이 있으면 그것만 유지
                after_greeting = re.sub(r'^.*안녕하세요[^,]*,?\s*', '', line)
                if after_greeting and after_greeting != line:
                    cleaned_lines.append(after_greeting)
                continue
            
            # 마지막 인사 제거
            if any(phrase in line for phrase in ['감사합니다', '드림', '배상','올림']):
                # 해당 줄이 인사말만 있는 경우 제거
                if re.match(r'^(감사합니다\.?|.*드림\.?|.*배상\.?)$', line.strip()):
                    continue
            
            cleaned_lines.append(line)
        
        # 과도한 줄바꿈 제거 및 정리
        content = '\n'.join(cleaned_lines)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 앞뒤 공백 제거
        content = content.strip()
        
        # 마지막 인사말 제거
        content = re.sub(r'(감사합니다\.?\s*$|.*드림\.?\s*$)', '', content)
        
        return content.strip()
    
    return ""
