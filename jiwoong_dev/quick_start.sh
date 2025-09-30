#!/bin/bash

echo "🏃‍♂️ BATON 빠른 시작"
echo "=================="

# 프로젝트 디렉토리로 이동
cd "$(dirname "$0")"

# 가상환경 활성화
echo "🔧 가상환경 활성화 중..."
source venv/Scripts/activate

# handover 디렉토리로 이동
cd handover

echo "🚀 BATON 애플리케이션 시작..."
echo "브라우저에서 http://localhost:8501 로 접속하세요."
echo ""

# streamlit 실행
streamlit run main.py
