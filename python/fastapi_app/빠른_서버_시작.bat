@echo off
:: 간단한 버전 - 최소한의 메시지로 빠른 시작

chcp 65001 >nul
cd /d "%~dp0"

echo 🚀 Two Very Auto 서버 시작 중...

:: 3초 후 브라우저 자동 열기
start "" /b powershell -command "Start-Sleep 3; Start-Process 'http://127.0.0.1:8000'"

:: 서버 실행
python main.py