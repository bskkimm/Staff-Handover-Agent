@echo off
echo 🏃‍♂️ BATON 빠른 시작
echo ==================

cd handover

echo 🔧 가상환경 활성화 중...
call ..\venv\Scripts\activate.bat

echo 🚀 BATON 애플리케이션 시작...
echo 브라우저에서 http://localhost:8501 로 접속하세요.
echo.

streamlit run main.py

pause
