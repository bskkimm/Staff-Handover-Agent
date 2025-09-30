@echo off
echo BATON - 통합 인수인계 관리 시스템 시작
echo.

cd handover

echo 필요한 패키지 설치 중...
pip install -r ../requirements.txt

echo.
echo BATON 애플리케이션 시작...
streamlit run main.py

pause
