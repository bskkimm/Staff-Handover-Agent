# integrated_modules.py - 통합된 BATON 앱을 위한 모듈 함수들
import os
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# ==================== 데이터 전처리 모듈 ====================
def run_data_preprocessing(files_data: Dict[str, str]) -> Dict[str, Any]:
    """업로드된 파일들을 전처리"""
    try:
        from data_preprocess.preprocessor_test import process_all_files
        
        with st.spinner("📝 파일들을 분석하고 전처리 중..."):
            st.info(f"📁 {len(files_data)}개 파일을 처리합니다...")
            
            # 파일 타입별로 분류하고 파싱
            processed_data = process_all_files(files_data)
            
            st.success("✅ 파일 전처리 완료!")
            
            # 결과 요약
            summary = {
                'total_files': len(files_data),
                'emails': len(processed_data.get('emails', [])),
                'meetings': len(processed_data.get('meetings', [])),
                'personal_notes': len(processed_data.get('personal_notes', []))
            }
            
            return {
                'success': True,
                'data': processed_data,
                'summary': summary
            }
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"데이터 전처리 오류: {e}")
        st.error(f"상세 오류: {error_details}")
        return {
            'success': False,
            'error': str(e),
            'error_details': error_details,
            'data': {},
            'summary': {}
        }

# ==================== 요약 리포트 모듈 ====================
def run_summary_generation(processed_data: Dict[str, Any]) -> Dict[str, Any]:
    """전처리된 데이터로 요약 리포트 생성"""
    try:
        from summary_report.summarizer import test_llm_markdown_output
        from openai import AzureOpenAI
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Azure OpenAI 클라이언트 설정
        client = AzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version="2024-02-01",
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
        )
        
        with st.spinner("📊 AI가 인수인계 요약 리포트를 생성 중..."):
            # 전처리된 데이터를 텍스트로 변환
            content_text = ""
            
            # 이메일 데이터 추가
            for email in processed_data.get('emails', []):
                if hasattr(email, 'subject'):
                    content_text += f"Subject: {email.subject}\n"
                if hasattr(email, 'body'):
                    content_text += f"Content: {email.body}\n\n"
            
            # 회의록 데이터 추가
            for meeting in processed_data.get('meetings', []):
                if hasattr(meeting, 'title'):
                    content_text += f"Meeting: {meeting.title}\n"
                if hasattr(meeting, 'content'):
                    content_text += f"Content: {meeting.content}\n\n"
            
            # 개인 노트 데이터 추가
            for note in processed_data.get('personal_notes', []):
                if hasattr(note, 'title'):
                    content_text += f"Note: {note.title}\n"
                if hasattr(note, 'content'):
                    content_text += f"Content: {note.content}\n\n"
            
            # AI 요약 생성
            prompt = f"""
            다음 인수인계 관련 문서들을 바탕으로 체계적인 마크다운 요약 보고서를 작성해주세요.
            
            **요구사항:**
            1. 제목은 # 으로 시작
            2. 섹션별로 ## 사용
            3. 리스트는 - 또는 1. 사용
            4. 중요한 내용은 **굵게** 표시
            5. 날짜는 `백틱`으로 감싸기
            6. 테이블 형식도 포함
            
            **문서 내용:**
            {content_text}
            
            다음 구조로 작성해주세요:
            - 프로젝트 개요
            - 진행 현황
            - 주요 일정
            - 미해결 과제
            - 인수인계 체크리스트
            """
            
            response = client.chat.completions.create(
                model="aicore-gpt4o",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 HR 업무 전문가입니다. 전임자로서 후임자에게 인수인계를 하기 위한 명확하고 체계적인 마크다운 보고서를 작성합니다."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.2
            )
            
            markdown_report = response.choices[0].message.content
            
            return {
                'success': True,
                'report': markdown_report,
                'content_length': len(content_text)
            }
    
    except Exception as e:
        st.error(f"요약 생성 오류: {e}")
        return {
            'success': False,
            'error': str(e),
            'report': ""
        }

# ==================== 스케줄링 모듈 ====================
def run_schedule_extraction(files_data: Dict[str, str]) -> Dict[str, Any]:
    """업로드된 파일들에서 스케줄 추출 및 시각화"""
    try:
        from scheduling.scheduling_main import (
            aggregate_all, build_markdown, save_markdown, 
            visualize_calendar, write_ics
        )
        from scheduling.desk_calendar_bar_viz import render_all_months_bars
        import tempfile
        import shutil
        
        with st.spinner("📅 스케줄을 추출하고 시각화 중..."):
            # 임시 디렉토리에 txt 파일들 생성
            temp_dir = tempfile.mkdtemp()
            
            try:
                # 파일들을 임시 디렉토리에 저장
                files_with_text = []
                for filename, content in files_data.items():
                    base_name = Path(filename).stem
                    txt_filename = f"{base_name}.txt"
                    txt_path = os.path.join(temp_dir, txt_filename)
                    
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    files_with_text.append((txt_filename, content))
                
                if not files_with_text:
                    return {
                        'success': False,
                        'error': '처리할 파일이 없습니다.',
                        'outputs': {}
                    }
                
                # 스케줄 추출 및 처리
                groups = aggregate_all(files_with_text)
                md_content = build_markdown(groups)
                
                # 출력 디렉토리 설정
                output_dir = "scheduling/output"
                os.makedirs(output_dir, exist_ok=True)
                
                # 결과 파일들 저장
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_md = os.path.join(output_dir, f"combined_schedule_{timestamp}.md")
                out_png = os.path.join(output_dir, f"combined_schedule_timeline_{timestamp}.png")
                out_ics = os.path.join(output_dir, f"combined_schedule_{timestamp}.ics")
                
                save_markdown(md_content, out_md)
                visualize_calendar(md_content, out_png)
                write_ics(md_content, out_ics)
                
                # 캘린더 바 시각화
                viz_dir = os.path.join(output_dir, f"out_cal_bars_{timestamp}")
                os.makedirs(viz_dir, exist_ok=True)
                render_all_months_bars(out_md, viz_dir)
                
                return {
                    'success': True,
                    'outputs': {
                        'markdown': out_md,
                        'timeline_png': out_png,
                        'ics_calendar': out_ics,
                        'calendar_bars': viz_dir
                    },
                    'schedule_count': len(groups)
                }
            
            finally:
                # 임시 디렉토리 정리
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"스케줄 추출 오류: {e}")
        st.error(f"상세 오류: {error_details}")
        return {
            'success': False,
            'error': str(e),
            'error_details': error_details,
            'outputs': {}
        }

# ==================== 챗봇 모듈 ====================
def run_chatbot_integration() -> Dict[str, Any]:
    """챗봇 모듈 통합"""
    try:
        from chatbot import run_chat
        
        # FAISS 인덱스 존재 여부 확인
        index_path = "./chatbot/rag_store/index.faiss"
        meta_path = "./chatbot/rag_store/meta.jsonl"
        
        if not os.path.exists(index_path) or not os.path.exists(meta_path):
            st.info("🔍 챗봇 인덱스가 없습니다. 업로드된 파일들로 인덱스를 생성합니다...")
            
            # 업로드된 파일 데이터 가져오기
            files_data = get_uploaded_files_data()
            if not files_data:
                return {
                    'success': False,
                    'error': '챗봇 인덱스 생성에 필요한 파일이 없습니다.',
                    'chatbot_available': False
                }
            
            # 인덱스 생성
            with st.spinner("🔄 챗봇 인덱스를 생성 중..."):
                from chatbot.rag_app import build_index_from_files
                build_index_from_files(files_data, index_path, meta_path)
            
            st.success("✅ 챗봇 인덱스가 성공적으로 생성되었습니다!")
        
        return {
            'success': True,
            'chatbot_available': True
        }
    
    except Exception as e:
        st.error(f"챗봇 모듈 로드 오류: {e}")
        return {
            'success': False,
            'error': str(e),
            'chatbot_available': False
        }

# ==================== 통합 실행 함수 ====================
def run_full_pipeline() -> Dict[str, Any]:
    """전체 파이프라인 실행"""
    try:
        from utils import get_uploaded_files_data
        
        # 1. 업로드된 파일 데이터 가져오기
        files_data = get_uploaded_files_data()
        if not files_data:
            return {
                'success': False,
                'error': '업로드된 파일이 없습니다.',
                'results': {}
            }
        
        results = {
            'files_count': len(files_data),
            'preprocessing': {},
            'summary': {},
            'scheduling': {},
            'chatbot': {}
        }
        
        # 2. 데이터 전처리
        preprocessing_result = run_data_preprocessing(files_data)
        results['preprocessing'] = preprocessing_result
        
        if not preprocessing_result['success']:
            return {
                'success': False,
                'error': '데이터 전처리 실패',
                'results': results
            }
        
        # 3. 요약 리포트 생성
        summary_result = run_summary_generation(preprocessing_result['data'])
        results['summary'] = summary_result
        
        # 4. 스케줄 추출
        schedule_result = run_schedule_extraction(files_data)
        results['scheduling'] = schedule_result
        
        # 5. 챗봇 통합 확인
        chatbot_result = run_chatbot_integration()
        results['chatbot'] = chatbot_result
        
        return {
            'success': True,
            'results': results
        }
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"전체 파이프라인 실행 오류: {e}")
        st.error(f"상세 오류: {error_details}")
        return {
            'success': False,
            'error': str(e),
            'error_details': error_details,
            'results': {}
        }
