@echo off
title 즉시 해결 - Two Very Auto 서버 연결 문제
chcp 65001 >nul

echo.
echo ████████████████████████████████████████
echo █     🚨 즉시 해결 스크립트 🚨        █
echo █   Two Very Auto 연결 문제 해결     █
echo ████████████████████████████████████████
echo.

REM 관리자 권한으로 자동 실행
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚡ 관리자 권한으로 재시작합니다...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ✅ 관리자 권한 확인 완료

REM 1단계: 완전 정리
echo.
echo 🔄 1단계: 시스템 완전 정리
echo =====================================

REM 모든 Python 프로세스 강제 종료
echo Python 프로세스 정리 중...
taskkill /f /im python.exe >nul 2>&1

REM 포트 점유 프로세스 강제 종료
for %%p in (8080 8000 3000 9999 7777 5000) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%%p 2^>nul') do (
        echo 포트 %%p 사용 프로세스 %%a 종료 중...
        taskkill /f /pid %%a >nul 2>&1
    )
)

timeout /t 3 /nobreak >nul
echo ✅ 시스템 정리 완료

REM 2단계: 방화벽 긴급 설정
echo.
echo 🛡️  2단계: 방화벽 긴급 설정
echo =====================================

netsh advfirewall firewall delete rule name="TwoVeryAutoEmergency" >nul 2>&1
netsh advfirewall firewall add rule name="TwoVeryAutoEmergency" dir=in action=allow protocol=TCP localport=8080 >nul 2>&1
netsh advfirewall firewall add rule name="TwoVeryAutoEmergency8000" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1

echo ✅ 방화벽 설정 완료

REM 3단계: 디렉토리 이동 및 환경 확인
echo.
echo 📁 3단계: 환경 확인
echo =====================================

cd /d "%~dp0python\fastapi_app"
if not exist "main.py" (
    echo ❌ main.py를 찾을 수 없습니다!
    echo 현재 디렉토리: %CD%
    pause
    exit /b 1
)

echo ✅ main.py 확인 완료
echo 현재 위치: %CD%

REM 4단계: 간단한 서버 즉시 시작
echo.
echo 🚀 4단계: 서버 즉시 시작
echo =====================================

REM 포트 8080 시도
echo 포트 8080으로 서버 시작 중...
start "TwoVeryAuto-Emergency" /min cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload"

echo 서버 시작 대기 중... (최대 15초)
set /a counter=0

:wait_8080
timeout /t 1 /nobreak >nul
set /a counter+=1

REM 서버 응답 테스트
python -c "import requests; requests.get('http://127.0.0.1:8080/health', timeout=2)" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 포트 8080 서버 시작 성공!
    set SERVER_PORT=8080
    goto :server_ready
)

if %counter% lss 15 goto :wait_8080

REM 포트 8080 실패 시 8000 시도
echo ⚠️  포트 8080 실패, 8000 시도 중...
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

start "TwoVeryAuto-Emergency" /min cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 5 /nobreak >nul

python -c "import requests; requests.get('http://127.0.0.1:8000/health', timeout=2)" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 포트 8000 서버 시작 성공!
    set SERVER_PORT=8000
    goto :server_ready
)

echo ❌ 서버 시작 실패
echo.
echo 수동 해결 방법:
echo 1. 안티바이러스 소프트웨어 일시 비활성화
echo 2. Windows 방화벽 일시 비활성화
echo 3. 컴퓨터 재시작 후 다시 시도
pause
exit /b 1

:server_ready
echo.
echo ████████████████████████████████████████
echo █        🎉 해결 완료! 🎉           █
echo █                                   █
echo █  📱 메인: http://127.0.0.1:%SERVER_PORT%    █
echo █  🎯 페어: http://127.0.0.1:%SERVER_PORT%/pair-dashboard █
echo █                                   █
echo ████████████████████████████████████████
echo.

REM 5단계: 브라우저 자동 열기
echo 🌐 브라우저 자동 연결 중...

REM 잠시 대기 후 브라우저 열기
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:%SERVER_PORT%"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:%SERVER_PORT%/pair-dashboard"

echo.
echo ✅ 브라우저에서 페이지를 확인하세요!
echo.
echo 🔄 서버 모니터링 중... (이 창을 닫으면 서버도 종료됩니다)
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

:monitor
timeout /t 10 /nobreak >nul

python -c "import requests; r=requests.get('http://127.0.0.1:%SERVER_PORT%/health', timeout=3); print('✅ [%s] 서버 정상 작동 중' % r.json().get('timestamp', 'N/A'))" 2>nul
if %errorlevel% neq 0 (
    echo ❌ [%time%] 서버 응답 없음 - 재시작 시도 중...
    taskkill /f /im python.exe >nul 2>&1
    timeout /t 2 /nobreak >nul
    start "TwoVeryAuto-Emergency-Restart" /min cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port %SERVER_PORT% --reload"
    timeout /t 3 /nobreak >nul
)

goto :monitor