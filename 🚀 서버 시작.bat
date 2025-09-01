@echo off
chcp 65001 >nul
color 0A
title 🎯 Two Very Auto - 페어 정보 시스템

echo.
echo ===============================================================
echo                🎯 Two Very Auto 서버 시작 중...
echo ===============================================================
echo.
echo 🎰 실시간 바카라 페어 감지 및 알림 시스템
echo 📊 패턴 분석 · 🔔 즉시 알림 · 📈 상세 통계
echo.
echo ===============================================================
echo.

:: 현재 디렉토리를 FastAPI 앱 폴더로 변경
cd /d "%~dp0python\fastapi_app"

:: Python이 설치되어 있는지 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo    https://python.org 에서 Python을 설치해주세요.
    echo.
    pause
    exit /b 1
)

:: 필요한 패키지 설치 확인
echo 🔍 필요한 패키지 확인 중...
pip install -q fastapi uvicorn

:: 서버 시작
echo.
echo 🚀 서버 시작 중... (잠시만 기다려주세요)
echo.
echo ✨ 서버가 시작되면 자동으로 브라우저가 열립니다.
echo ✨ 종료하려면 이 창에서 Ctrl+C 를 누르세요.
echo.

:: 3초 후 브라우저 열기 (백그라운드)
start "" /b timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000

:: Python 서버 실행
python main.py

echo.
echo 📱 서버가 종료되었습니다.
pause