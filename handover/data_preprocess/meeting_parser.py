"""
회의록 파싱 관련 모듈
"""
import re
from typing import List, Dict, Optional
from dataclasses import dataclass


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
