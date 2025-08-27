@echo off
echo Two Very Auto - 백그라운드 서버 시작
echo =======================================

cd /d "F:\two very auto 25.08.23\python\fastapi_app"

echo 기존 Python 프로세스 종료 중...
wmic process where "name='python.exe'" delete >nul 2>&1

echo.
echo 서버 시작 중...
start "Two Very Auto Server" python fastapi_http_server.py

echo.
echo 서버가 백그라운드에서 실행 중입니다!
echo 브라우저에서 접속: http://127.0.0.1:8080
echo.

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8080"

echo 대시보드가 곧 브라우저에서 열립니다...
echo 서버를 중지하려면 작업 관리자에서 Python 프로세스를 종료하세요.
pause