"""
개인기록 파싱 관련 모듈
"""
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


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
