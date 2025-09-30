import os
import re
import json
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class FileType(Enum):
    EMAIL = "email"
    MEETING = "meeting"
    PERSONAL = "personal"
    UNKNOWN = "unknown"

def read_txt_file(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            content = file.read()
            return content
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return None
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
        return None

def read_multiple_txt_files(directory_path: str, file_pattern: str = "*.txt") -> Dict[str, str]:
    """
    반환값:
        Dict[str, str]: {파일명: 파일내용} 형태의 딕셔너리
    """
    files_content = {}
    path = Path(directory_path)
    
    if not path.exists():
        print(f"디렉토리가 존재하지 않습니다: {directory_path}")
        return files_content
    
    for file_path in path.glob(file_pattern):
        if file_path.is_file():
            content = read_txt_file(str(file_path))
            if content is not None:
                files_content[file_path.name] = content
                print(f"✓ 파일 로드 완료: {file_path.name}")
    
    print(f"총 {len(files_content)}개 파일 로드 완료")
    return files_content

#파일 타입이 메일인지 회의록인지 개인기록인지 구분하는 함수
def detect_file_type(content: str) -> FileType:
    email_headers = {
        'from': bool(re.search(r'^From:\s*.+<.+@.+>', content, re.MULTILINE)),
        'to': bool(re.search(r'^To:\s*.+<.+@.+>', content, re.MULTILINE)),
        'date': bool(re.search(r'^Date:\s*.+\d{4}', content, re.MULTILINE)),
        'subject': bool(re.search(r'^Subject:\s*.+', content, re.MULTILINE))
    }
    if all(email_headers.values()):
        return FileType.EMAIL
    
    has_title = bool(re.search(r'^제목:\s*.+', content, re.MULTILINE))
    has_datetime = bool(re.search(r'^일시:\s*.+\d{4}', content, re.MULTILINE))
    
    meeting_patterns = {
        'title_with_meeting': bool(re.search(r'^제목:\s*.+(회의|미팅)', content, re.MULTILINE)),
        'location': bool(re.search(r'^장소:\s*.+', content, re.MULTILINE)),
        'attendees': bool(re.search(r'^참석자:\s*.+', content, re.MULTILINE)),
        'agenda': bool(re.search(r'^안건\s*$', content, re.MULTILINE)),
        'discussion': bool(re.search(r'^논의\s*$', content, re.MULTILINE)),
        'decisions': bool(re.search(r'^결정사항\s*$', content, re.MULTILINE)),
        'action_items': bool(re.search(r'^액션아이템\s*$', content, re.MULTILINE)),
        'background': bool(re.search(r'^배경\s*$', content, re.MULTILINE))
    }
    
    personal_patterns = {
        'author': bool(re.search(r'^작성자:\s*.+', content, re.MULTILINE)),
        'project': bool(re.search(r'^프로젝트:\s*.+', content, re.MULTILINE)),
        'related_mail': bool(re.search(r'^관련 메일\s*$', content, re.MULTILINE)),
        'goal': bool(re.search(r'^목표\s*$', content, re.MULTILINE)),
        'reference': bool(re.search(r'^참고 자료\s*$', content, re.MULTILINE)),
        'progress': bool(re.search(r'^진행 상태\s*$', content, re.MULTILINE)),
        'memo': bool(re.search(r'^메모\s*$', content, re.MULTILINE)),
        'next_action': bool(re.search(r'^다음 액션\s*$', content, re.MULTILINE)),
        'todo_markers': bool(re.search(r'(TODO:|DOING:|DONE:)', content))
    }
    
    meeting_score = sum([
        meeting_patterns['title_with_meeting'] * 3,  # 제목에 '회의' 있으면 가중치 3
        meeting_patterns['location'] * 2,
        meeting_patterns['attendees'] * 2,
        meeting_patterns['agenda'],
        meeting_patterns['discussion'],
        meeting_patterns['decisions'],
        meeting_patterns['action_items'],
        meeting_patterns['background']
    ])
    
    personal_score = sum([
        personal_patterns['author'] * 2,
        personal_patterns['project'] * 2,
        personal_patterns['related_mail'],
        personal_patterns['goal'],
        personal_patterns['reference'],
        personal_patterns['progress'] * 2,  # 진행 상태는 가중치 2
        personal_patterns['memo'],
        personal_patterns['next_action'],
        personal_patterns['todo_markers'] * 3  # TODO/DOING/DONE은 가중치 3
    ])
    
    if meeting_patterns['attendees'] and meeting_score > personal_score:
        return FileType.MEETING
    
    if personal_patterns['author'] and personal_score > meeting_score:
        return FileType.PERSONAL
    
    if meeting_patterns['title_with_meeting']:
        return FileType.MEETING
    
    if personal_patterns['todo_markers']:
        return FileType.PERSONAL
    
    if has_title and has_datetime:
        if meeting_patterns['attendees']:
            return FileType.MEETING
        elif personal_patterns['author']:
            return FileType.PERSONAL
    
    # 이메일 주소가 있고 From: 헤더가 있으면 이메일 가능성
    if '@' in content and 'From:' in content:
        return FileType.EMAIL
    
    return FileType.UNKNOWN

#이메일 파트
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

#이메일 파싱 함수
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

#이메일 파싱 보조 함수들
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

# def process_email_files(files_dict: Dict[str, str]) -> Dict[str, List[Dict]]:
#     """
#     read_multiple_txt_files로 읽어온 파일들을 처리
    
#     Args:
#         files_dict: {파일명: 내용} 형태의 딕셔너리
    
#     Returns:
#         {파일명: [파싱된 이메일 딕셔너리 리스트]} 형태의 딕셔너리
#     """
#     processed_emails = {}
    
#     for filename, content in files_dict.items():
#         print(f"\n처리 중: {filename}")
#         emails = parse_email(content)
        
#         if emails:
#             # Email 객체를 딕셔너리로 변환
#             processed_emails[filename] = [email.to_dict() for email in emails]
#             print(f"  → {len(emails)}개 이메일 파싱 완료")
            
#             # 첫 번째 이메일 미리보기
#             if emails:
#                 print(f"  첫 번째 이메일:")
#                 first_email = emails[0]
#                 print(f"    날짜: {first_email.date}")
#                 print(f"    제목: {first_email.subject}")
#                 print(f"    발신자: {first_email.sender}")
#         else:
#             processed_emails[filename] = []
#             print(f"  → 파싱 실패")
#     return processed_emails

#회의록 파트
@dataclass
class MeetingMinutes:
    """회의록 데이터 클래스"""
    title: str
    date: str
    location: str
    author: str
    attendees: List[str]
    background: str
    agenda: List[str]
    discussion: str
    decisions: List[str]
    action_items: List[Dict[str, str]]
    
    def to_dict(self) -> Dict:
        return {
            '타입': 'meeting',
            '제목': self.title,
            '일시': self.date,
            '장소': self.location,
            '작성자': self.author,
            '참석자': ', '.join(self.attendees),
            '배경': self.background,
            '안건': self.agenda,
            '논의': self.discussion,
            '결정사항': self.decisions,
            '액션아이템': self.action_items
        }

#회의록 파싱 함수
def parse_meeting_minutes(content: str) -> Optional[Dict]:
    """
    회의록 전체 파싱
    """
    try:
        # 제목
        title_match = re.search(r'제목:\s*(.+)', content)
        title = title_match.group(1).strip() if title_match else ""
        
        # 일시
        date_match = re.search(r'일시:\s*(.+)', content)
        date = clean_meeting_date(date_match.group(1)) if date_match else ""
        
        # 장소
        location_match = re.search(r'장소:\s*(.+)', content)
        location = location_match.group(1).strip() if location_match else ""
        
        # 작성자
        author_match = re.search(r'작성/소유:\s*(.+)', content)
        author = extract_author_name(author_match.group(1)) if author_match else ""
        
        # 참석자
        attendees_match = re.search(r'참석자:\s*(.+)', content)
        attendees = parse_attendees(attendees_match.group(1)) if attendees_match else []
        
        # 각 섹션 추출
        background = extract_background(content)
        agenda = extract_agenda_items(content)
        discussion = extract_discussion(content)
        decisions = extract_decisions(content)
        action_items = extract_action_items(content)
        
        return {
            '타입': 'meeting',
            '제목': title,
            '일시': date,
            '장소': location,
            '작성자': author,
            '참석자': ', '.join(attendees),
            '배경': background,
            '안건': agenda,
            '논의': discussion,
            '결정사항': decisions,
            '액션아이템': action_items
        }
        
    except Exception as e:
        print(f"회의록 파싱 오류: {e}")
        return None
    
def clean_meeting_date(date_str: str) -> str:
    """
    회의 일시 정리
    입력: "Fri, 19 Jul 2024 11:00 +0900 (KST) ~ 12:00"
    출력: "2024-07-19 11:00"
    """
    # 종료 시간 제거 (~ 이후 부분)
    date_str = re.sub(r'\s*~.*', '', date_str)
    
    # 시간대 정보 제거
    date_str = re.sub(r'\s*\+\d{4}\s*\([^)]+\)', '', date_str)
    
    # 날짜 형식 변환
    months = {
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
        'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
    }
    
    # "Fri, 19 Jul 2024 11:00" 패턴
    pattern = r'(\w+),\s*(\d+)\s+(\w+)\s+(\d{4})\s+(\d{2}:\d{2})'
    match = re.search(pattern, date_str)
    if match:
        month = months.get(match.group(3), match.group(3))
        return f"{match.group(4)}-{month}-{match.group(2).zfill(2)} {match.group(5)}"
    
    return date_str.strip()

def extract_author_name(author_str: str) -> str:
    """
    작성자에서 이름만 추출
    입력: "김민수(인사팀 대리)"
    출력: "김민수"
    """
    # 괄호 앞의 이름만 추출
    match = re.match(r'([^(\s]+)', author_str.strip())
    return match.group(1) if match else author_str.strip()

def parse_attendees(attendees_str: str) -> List[str]:
    """
    참석자 문자열 파싱
    입력: "김민수, 박서연, 오현우"
    출력: ["김민수", "박서연", "오현우"]
    """
    # 콤마로 분리하고 공백 제거
    return [name.strip() for name in attendees_str.split(',') if name.strip()]

def extract_background(content: str) -> str:
    """
    배경 섹션 추출
    입력: 전체 회의록 내용
    출력: "2024-07-18 '보상_킥오프' 메일 후속"
    """
    # '배경' 다음 줄의 '- ' 내용 추출
    pattern = r'배경\s*\n\s*-\s*(.+?)(?=\n[^\s-]|\n\n|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def extract_agenda_items(content: str) -> List[str]:
    """
    안건 리스트 추출
    입력: 전체 회의록 내용
    출력: ["시장 데이터 소싱 계획", "레벨/밴드 규칙 재확인", "예외 승인 프로세스"]
    """
    items = []
    # '안건' 섹션 찾기
    pattern = r'안건\s*\n((?:\d+\..*\n?)+)'
    match = re.search(pattern, content)
    
    if match:
        lines = match.group(1).strip().split('\n')
        for line in lines:
            # "1. 시장 데이터 소싱 계획" → "시장 데이터 소싱 계획"
            item = re.sub(r'^\d+\.\s*', '', line.strip())
            if item:
                items.append(item)
    
    return items

def extract_discussion(content: str) -> str:
    """
    논의 섹션 텍스트 추출
    입력: 전체 회의록 내용
    출력: "데이터 벤더 2곳 비교, 07-25까지 계약 선택\n예외 위원회 구성안 초안 합의"
    """
    # '논의' 섹션의 모든 '- ' 항목들 추출
    pattern = r'논의\s*\n((?:\s*-\s*.+\n?)+)'
    match = re.search(pattern, content)
    
    if match:
        lines = match.group(1).strip().split('\n')
        discussions = []
        for line in lines:
            # "- " 제거
            item = re.sub(r'^\s*-\s*', '', line.strip())
            if item:
                discussions.append(item)
        return '\n'.join(discussions)
    
    return ""

def extract_decisions(content: str) -> List[str]:
    """
    결정사항 리스트 추출
    입력: 전체 회의록 내용
    출력: ["시장 데이터 컷 기준 08-05", "예외 위원회 명단 07-23 확정"]
    """
    decisions = []
    # '결정사항' 섹션의 '- ' 항목들
    pattern = r'결정사항\s*\n((?:\s*-\s*.+\n?)+)'
    match = re.search(pattern, content)
    
    if match:
        lines = match.group(1).strip().split('\n')
        for line in lines:
            item = re.sub(r'^\s*-\s*', '', line.strip())
            if item:
                decisions.append(item)
    
    return decisions

def extract_action_items(content: str) -> List[Dict[str, str]]:
    """
    액션아이템 추출
    입력: 전체 회의록 내용
    출력: [
        {'작업': '벤더 비교표 제출', '기한': '2024-07-22', '담당자': '김민수'},
        {'작업': '위원회 구성안 회람', '기한': '2024-07-22', '담당자': '박서연'}
    ]
    """
    action_items = []
    
    # '액션아이템' 섹션 찾기
    section_pattern = r'액션아이템\s*\n((?:\d+\..*\n?)+)'
    section_match = re.search(section_pattern, content)
    
    if section_match:
        section_text = section_match.group(1)
        
        # 각 액션아이템 파싱: "1. 작업 — 날짜 — 담당자"
        item_pattern = r'(\d+\.\s*.+?)\s*—\s*(\d{4}-\d{2}-\d{2})\s*—\s*(.+)'
        matches = re.findall(item_pattern, section_text)
        
        for match in matches:
            # "1. " 제거
            task = re.sub(r'^\d+\.\s*', '', match[0]).strip()
            action_items.append({
                '작업': task,
                '기한': match[1].strip(),
                '담당자': match[2].strip()
            })
    
    return action_items
    
#개인기록 파트
@dataclass
class PersonalNote:
    """개인 기록 데이터 클래스"""
    date: str
    title: str
    content: str
    tags: List[str]
    
    def to_dict(self) -> Dict:
        return {
            '타입': 'personal',
            '날짜': self.date,
            '제목': self.title,
            '내용': self.content,
            '태그': self.tags
        }

def parse_personal_note(content: str, filename: str = "") -> Optional[Dict]:
    """
    개인기록 전체 파싱
    """
    try:
        title = extract_personal_title(content)
        author = extract_author_info(content)
        date = extract_personal_date(content, filename)
        project = extract_project_name(content)
        
        related_mails = extract_related_mails(content)
        goals = extract_goals(content)
        references = extract_references(content)
        progress = extract_progress_status(content)
        memo = extract_memo(content)
        next_actions = extract_next_actions(content)
        tags = extract_tags(content)
        
        return {
            '타입': 'personal',
            '제목': title,
            '작성자': author,
            '날짜': date,
            '프로젝트': project,
            '관련메일': related_mails,
            '목표': goals,
            '참고자료': references,
            '진행상태': progress,
            '메모': memo,
            '다음액션': next_actions,
            '태그': tags
        }
        
    except Exception as e:
        print(f"개인기록 파싱 오류: {e}")
        return None
    
def extract_personal_title(content: str) -> str:
    """
    개인기록 제목 추출
    입력: 전체 개인기록 내용
    출력: "시장 데이터 벤더 비교표 작성 노트"
    """
    title_match = re.search(r'제목:\s*(.+)', content)
    if title_match:
        return title_match.group(1).strip()
    
    # 제목이 없으면 첫 줄을 제목으로
    lines = content.strip().split('\n')
    return lines[0].strip() if lines else ""


def extract_author_info(content: str) -> str:
    """
    작성자 정보 추출 (이름만)
    입력: "작성자: 김민수(인사팀 대리)"
    출력: "김민수"
    """
    author_match = re.search(r'작성자:\s*(.+)', content)
    if author_match:
        full_author = author_match.group(1).strip()
        # 괄호 앞의 이름만 추출
        name_match = re.match(r'([^(\s]+)', full_author)
        return name_match.group(1) if name_match else full_author
    return ""


def extract_personal_date(content: str, filename: str = "") -> str:
    """
    개인기록 날짜 추출
    입력: "일시: 2024-07-19 09:20 KST" 또는 파일명
    출력: "2024-07-19 09:20"
    """
    # 내용에서 일시 추출
    date_match = re.search(r'일시:\s*(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})', content)
    if date_match:
        return date_match.group(1).strip()
    
    # 날짜만 있는 경우
    date_only = re.search(r'일시:\s*(\d{4}-\d{2}-\d{2})', content)
    if date_only:
        return date_only.group(1).strip()
    
    # 파일명에서 날짜 추출
    if filename:
        file_date = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if file_date:
            return file_date.group(1)
    
    # 기본값: 현재 날짜
    return datetime.now().strftime('%Y-%m-%d')


def extract_project_name(content: str) -> str:
    """
    프로젝트명 추출
    입력: "프로젝트: 보상"
    출력: "보상"
    """
    project_match = re.search(r'프로젝트:\s*(.+)', content)
    return project_match.group(1).strip() if project_match else ""


def extract_related_mails(content: str) -> List[str]:
    """
    관련 메일 리스트 추출
    입력: 전체 개인기록 내용
    출력: ["2024-07-18 보상_킥오프 (데이터 소싱/규칙 재확인/예외 프로세스)"]
    """
    mails = []
    # '관련 메일' 섹션 찾기
    pattern = r'관련 메일\s*\n((?:\s*-\s*.+\n?)+)'
    match = re.search(pattern, content)
    
    if match:
        lines = match.group(1).strip().split('\n')
        for line in lines:
            # "- " 제거
            mail = re.sub(r'^\s*-\s*', '', line.strip())
            if mail:
                mails.append(mail)
    
    return mails


def extract_goals(content: str) -> List[str]:
    """
    목표 리스트 추출
    입력: 전체 개인기록 내용
    출력: ["벤더 비교표 제출 및 07-25 계약 선택 지원"]
    """
    goals = []
    # '목표' 섹션
    pattern = r'목표\s*\n((?:\s*-\s*.+\n?)+)'
    match = re.search(pattern, content)
    
    if match:
        lines = match.group(1).strip().split('\n')
        for line in lines:
            goal = re.sub(r'^\s*-\s*', '', line.strip())
            if goal:
                goals.append(goal)
    
    return goals


def extract_references(content: str) -> List[str]:
    """
    참고 자료 리스트 추출
    입력: 전체 개인기록 내용
    출력: ["Vendor A, Vendor B 제안서", "샘플 포지션 매칭 결과", "레벨/밴드 규칙 문서"]
    """
    references = []
    # '참고 자료' 섹션
    pattern = r'참고 자료\s*\n((?:\s*-\s*.+\n?)+)'
    match = re.search(pattern, content)
    
    if match:
        lines = match.group(1).strip().split('\n')
        for line in lines:
            ref = re.sub(r'^\s*-\s*', '', line.strip())
            if ref:
                references.append(ref)
    
    return references


def extract_progress_status(content: str) -> Dict[str, List[str]]:
    """
    진행 상태 추출 (TODO, DOING, DONE)
    입력: 전체 개인기록 내용
    출력: {
        'TODO': ['로컬 보정 지표 비교'],
        'DOING': ['포지션 커버리지 표 정리'],
        'DONE': ['비용/납기/지원 채널 비교']
    }
    """
    status = {'TODO': [], 'DOING': [], 'DONE': []}
    
    # '진행 상태' 섹션 찾기
    pattern = r'진행 상태\s*\n((?:\s*-\s*(?:TODO|DOING|DONE):.+\n?)+)'
    match = re.search(pattern, content)
    
    if match:
        lines = match.group(1).strip().split('\n')
        for line in lines:
            # "- TODO: 작업" 형식 파싱
            status_match = re.match(r'\s*-\s*(TODO|DOING|DONE):\s*(.+)', line)
            if status_match:
                status_type = status_match.group(1)
                task = status_match.group(2).strip()
                status[status_type].append(task)
    
    return status


def extract_memo(content: str) -> str:
    """
    메모 섹션 추출
    입력: 전체 개인기록 내용
    출력: "커버리지 차이는 기술 직군에서 뚜렷\nAPI 제공 여부가 추후 자동화에 영향"
    """
    # '메모' 섹션
    pattern = r'메모\s*\n((?:\s*-\s*.+\n?)+)'
    match = re.search(pattern, content)
    
    if match:
        lines = match.group(1).strip().split('\n')
        memos = []
        for line in lines:
            memo = re.sub(r'^\s*-\s*', '', line.strip())
            if memo:
                memos.append(memo)
        return '\n'.join(memos)
    
    return ""


def extract_next_actions(content: str) -> List[Dict[str, str]]:
    """
    다음 액션 리스트 추출
    입력: 전체 개인기록 내용
    출력: [
        {'작업': '비교표 초안 회람', '기한': '2024-07-19'},
        {'작업': '질의응답 정리', '기한': '2024-07-22'}
    ]
    """
    actions = []
    
    # '다음 액션' 섹션
    pattern = r'다음 액션\s*\n((?:\d+\..*\n?)+)'
    match = re.search(pattern, content)
    
    if match:
        lines = match.group(1).strip().split('\n')
        for line in lines:
            # "1. 작업 — 날짜" 형식
            action_match = re.match(r'\d+\.\s*(.+?)\s*—\s*(\d{4}-\d{2}-\d{2})', line)
            if action_match:
                actions.append({
                    '작업': action_match.group(1).strip(),
                    '기한': action_match.group(2).strip()
                })
            else:
                # 날짜 없이 작업만 있는 경우
                task_match = re.match(r'\d+\.\s*(.+)', line)
                if task_match:
                    actions.append({
                        '작업': task_match.group(1).strip(),
                        '기한': ''
                    })
    
    return actions


def extract_tags(content: str) -> List[str]:
    """
    해시태그 추출
    입력: 전체 개인기록 내용
    출력: ['보상', '벤더비교', '데이터']
    """
    # #태그 형식 찾기
    tags = re.findall(r'#(\w+)', content)
    
    # 프로젝트명도 태그로 추가
    project = extract_project_name(content)
    if project and project not in tags:
        tags.insert(0, project)
    
    return list(set(tags))

#입력 데이터 타입(메일, 회의록, 개인기록) 확인하고 타입에 따라 맞는 파싱 함수로 보내기
def process_all_files(files_dict):
    """모든 파일을 타입별로 분류하고 파싱"""
    print(f"🔍 {len(files_dict)}개 파일 처리 시작")
    
    result = {
        'emails': [],
        'meetings': [],
        'personal_notes': []
    }
    
    for filename, content in files_dict.items():
        try:
            print(f"📄 파일 처리 중: {filename}")
            print(f"📏 내용 길이: {len(content)} 문자")
            
            # 1. 각 파일의 타입 감지
            file_type = detect_file_type(content)
            print(f"🏷️ 감지된 타입: {file_type}")
            
            # 2. 타입에 맞는 파서 실행
            if file_type == FileType.EMAIL:
                parsed = parse_email(content)
                result['emails'].extend(parsed)
                print(f"📧 이메일 {len(parsed)}개 파싱 완료")
                
            elif file_type == FileType.MEETING:
                parsed = parse_meeting_minutes(content)
                result['meetings'].append(parsed)
                print(f"🤝 회의록 1개 파싱 완료")
                
            elif file_type == FileType.PERSONAL:
                parsed = parse_personal_note(content, filename)
                result['personal_notes'].append(parsed)
                print(f"📝 개인노트 1개 파싱 완료")
            else:
                print(f"❓ 알 수 없는 타입: {file_type}")
                
        except Exception as e:
            print(f"❌ 파일 처리 오류 ({filename}): {e}")
            import traceback
            traceback.print_exc()
    
    print(f"✅ 처리 완료 - 이메일: {len(result['emails'])}, 회의록: {len(result['meetings'])}, 개인노트: {len(result['personal_notes'])}")
    return result
def convert_to_json(data: dict, output_file: str = None) -> str:
    def custom_serializer(obj):
        # Email 객체처럼 dict로 변환 가능한 것은 __dict__ 사용
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        # datetime → ISO 포맷 문자열
        if isinstance(obj, datetime):
            return obj.isoformat()
        # 그 외는 문자열로
        return str(obj)
    json_str = json.dumps(data, ensure_ascii=False, indent=2, default=custom_serializer)

    return json_str

if __name__ == "__main__":
    files = read_multiple_txt_files("C:/Users/Administrator/SK_AX_Bootcamp/Staff-Handover-Agent/data/compensation/Test", "*.txt")
    processed_files = process_all_files(files)
    json_output = convert_to_json(processed_files)
    print(json_output)