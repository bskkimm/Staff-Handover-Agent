"""
파일 타입 감지 관련 모듈
"""
import re
from enum import Enum


class FileType(Enum):
    EMAIL = "email"
    MEETING = "meeting"
    PERSONAL = "personal"
    UNKNOWN = "unknown"


def detect_file_type(content: str) -> FileType:
    """
    파일 내용을 분석하여 파일 타입을 감지
    
    Args:
        content: 파일 내용 문자열
    
    Returns:
        FileType: 감지된 파일 타입
    """
    # 이메일 헤더 패턴 확인
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
    
    # 회의록 패턴 확인
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
    
    # 개인기록 패턴 확인
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
    
    # 점수 계산
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
    
    # 타입 결정 로직
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
