@echo off
title 지금 바로 해결 - Two Very Auto

echo 🚨 Two Very Auto 연결 문제 즉시 해결 🚨
echo =========================================

REM 관리자 권한으로 재시작
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

REM 모든 정리
echo 🔄 시스템 정리 중...
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM 방화벽 설정
netsh advfirewall firewall add rule name="Fix" dir=in action=allow protocol=TCP localport=8080 >nul 2>&1

REM 디렉토리 이동
cd /d "%~dp0python\fastapi_app"

REM 서버 시작
echo 🚀 서버 시작 중...
start /min cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8080"

REM 대기
timeout /t 8 /nobreak >nul

REM 브라우저 열기
start "" "http://127.0.0.1:8080"
start "" "http://127.0.0.1:8080/pair-dashboard"

echo ✅ 완료! 브라우저를 확인하세요!
pause