#!/bin/bash

echo "🏃‍♂️ BATON - 통합 인수인계 관리 시스템 시작"
echo "================================================"

# 프로젝트 디렉토리로 이동
cd "$(dirname "$0")"

echo "📁 현재 디렉토리: $(pwd)"
echo ""

# Python 가상환경 확인 및 생성
if [ ! -d "venv" ]; then
    echo "🐍 Python 가상환경 생성 중..."
    python -m venv venv
fi

# 가상환경 활성화
echo "🔧 가상환경 활성화 중..."
source venv/Scripts/activate

# 필요한 패키지 설치
echo "📦 필요한 패키지 설치 중..."
pip install -r requirements.txt

echo ""
echo "⚙️  환경 설정 확인 중..."

# .env 파일 확인
if [ ! -f "handover/.env" ]; then
    echo "⚠️  .env 파일이 없습니다. 다음 내용으로 handover/.env 파일을 생성해주세요:"
    echo ""
    echo "AZURE_OPENAI_API_KEY=your_api_key_here"
    echo "AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/"
    echo "AZURE_OPENAI_API_VERSION=2024-02-01"
    echo "AZURE_OPENAI_CHAT_DEPLOYMENT=aicore-gpt4o"
    echo "AZURE_OPENAI_EMBEDDING_DEPLOYMENT=your_embedding_deployment_name"
    echo ""
    read -p "Enter 키를 눌러 계속하세요..."
fi

echo ""
echo "🚀 BATON 애플리케이션 시작..."
echo "브라우저에서 http://localhost:8501 로 접속하세요."
echo ""

# handover 디렉토리로 이동하여 streamlit 실행
cd handover
streamlit run main.py

echo ""
echo "👋 BATON 애플리케이션이 종료되었습니다."
