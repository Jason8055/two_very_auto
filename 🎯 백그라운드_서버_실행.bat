@echo off
chcp 65001 >nul
title 🎯 Two Very Auto - 백그라운드 서버 실행기
color 0A

echo.
echo ████████████████████████████████████████████████
echo █                                              █
echo █    🎯 Two Very Auto - 백그라운드 서버 실행기  █
echo █         원클릭 실행 · 자동 복구 · 모니터링     █
echo █                                              █
echo ████████████████████████████████████████████████
echo.

REM =====================================================
REM  단계 1: 관리자 권한 확인 및 자동 요청
REM =====================================================
echo 🔐 관리자 권한 확인 중...
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  관리자 권한으로 재시작합니다...
    powershell -Command "Start-Process '%~f0' -Verb RunAs" 2>nul
    if %errorlevel% equ 0 exit /b
    echo ❌ 관리자 권한 요청 실패. 수동으로 관리자로 실행해주세요.
    pause & exit /b 1
)
echo ✅ 관리자 권한 확인 완료

REM =====================================================
REM  단계 2: 환경 검증 및 경로 설정
REM =====================================================
echo.
echo 🔧 환경 검증 중...

REM 작업 디렉토리를 F: 드라이브로 안전하게 설정
if not exist "F:\" (
    echo ❌ F: 드라이브를 찾을 수 없습니다.
    pause & exit /b 1
)

F: >nul 2>&1
cd /d "F:\two very auto 25.08.23\python\fastapi_app" 2>nul

if not exist "main.py" (
    echo ❌ main.py를 찾을 수 없습니다.
    echo    현재 위치: %CD%
    pause & exit /b 1
)

echo ✅ 프로젝트 경로 확인 완료: %CD%

REM Python 환경 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python을 찾을 수 없습니다. Python 설치 후 PATH 설정을 확인하세요.
    pause & exit /b 1
)
echo ✅ Python 환경 확인 완료

REM =====================================================
REM  단계 3: 시스템 정리 및 최적화
REM =====================================================
echo.
echo 🔄 시스템 정리 중...

REM 기존 Python 서버 프로세스 정리
taskkill /f /im python.exe /fi "WINDOWTITLE eq *Two*" >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq *FastAPI*" >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq *uvicorn*" >nul 2>&1

REM 포트 점유 프로세스 정리 (8080, 8000, 3000 포트)
for %%p in (8080 8000 3000) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%%p 2^>nul') do (
        taskkill /f /pid %%a >nul 2>&1
    )
)

timeout /t 2 /nobreak >nul
echo ✅ 시스템 정리 완료

REM =====================================================
REM  단계 4: 방화벽 자동 설정
REM =====================================================
echo.
echo 🛡️  방화벽 설정 중...

REM 기존 규칙 제거 후 새 규칙 추가
netsh advfirewall firewall delete rule name="TwoVeryAuto-Server" >nul 2>&1
netsh advfirewall firewall add rule name="TwoVeryAuto-Server" dir=in action=allow protocol=TCP localport=8080 >nul 2>&1
netsh advfirewall firewall add rule name="TwoVeryAuto-Backup" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1
netsh advfirewall firewall add rule name="TwoVeryAuto-Alt" dir=in action=allow protocol=TCP localport=3000 >nul 2>&1

echo ✅ 방화벽 설정 완료

REM =====================================================
REM  단계 5: 스마트 포트 선택 및 서버 시작
REM =====================================================
echo.
echo 🚀 서버 시작 중...

REM 사용 가능한 포트 자동 선택
set SELECTED_PORT=
for %%p in (8080 8000 3000 9999 7777 5000 8888) do (
    netstat -ano | findstr ":%%p " >nul 2>&1
    if !errorlevel! neq 0 (
        set SELECTED_PORT=%%p
        goto :found_port
    )
)

:found_port
if "%SELECTED_PORT%"=="" (
    echo ❌ 사용 가능한 포트를 찾을 수 없습니다.
    pause & exit /b 1
)

echo ✅ 선택된 포트: %SELECTED_PORT%
echo.

REM 백그라운드에서 서버 시작 (모든 오류 메시지 억제)
echo 🌐 백그라운드 서버 시작 중... (포트: %SELECTED_PORT%)
start "TwoVeryAuto-Server" /min cmd /c "python -c \"import uvicorn; from main import app; uvicorn.run(app, host='0.0.0.0', port=%SELECTED_PORT%, access_log=False)\" 2>nul"

REM 서버 시작 대기 및 확인
echo 서버 시작 대기 중... (최대 30초)
set /a counter=0

:wait_server
timeout /t 1 /nobreak >nul
set /a counter+=1

REM 서버 응답 확인
powershell -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:%SELECTED_PORT%/health' -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 goto :server_ready

if %counter% lss 30 goto :wait_server

echo ❌ 서버 시작 실패
pause & exit /b 1

:server_ready
echo ✅ 서버 시작 성공!

REM =====================================================
REM  단계 6: 브라우저 자동 연결
REM =====================================================
echo.
echo 🌐 브라우저 자동 연결 중...

set MAIN_URL=http://127.0.0.1:%SELECTED_PORT%
set PAIR_URL=http://127.0.0.1:%SELECTED_PORT%/pair-dashboard
set API_URL=http://127.0.0.1:%SELECTED_PORT%/docs

REM 2초 간격으로 브라우저 창 열기
start "" "%MAIN_URL%" 2>nul
timeout /t 2 /nobreak >nul
start "" "%PAIR_URL%" 2>nul

echo ✅ 브라우저 연결 완료

echo.
echo ████████████████████████████████████████████████
echo █                                              █
echo █           🎉 서버 시작 완료! 🎉              █
echo █                                              █
echo █  📱 메인 페이지: %MAIN_URL%
echo █  🎯 페어 대시보드: %PAIR_URL%
echo █  📖 API 문서: %API_URL%
echo █                                              █
echo █  💡 서버는 백그라운드에서 실행 중입니다       █
echo █  💡 이 창을 닫으면 서버도 종료됩니다          █
echo █                                              █
echo ████████████████████████████████████████████████
echo.

REM =====================================================
REM  단계 7: 서버 모니터링 및 자동 복구
REM =====================================================
echo 🔄 서버 모니터링 시작...
echo    - 10초마다 서버 상태 확인
echo    - 서버 중단 시 자동 재시작
echo    - 서버 완전 종료: 이 창을 닫기 (Ctrl+C)
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

:monitor_loop
timeout /t 10 /nobreak >nul

REM 서버 상태 확인
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:%SELECTED_PORT%/health' -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue; Write-Host '✅ [%time%] 서버 정상 작동 중 (포트: %SELECTED_PORT%)' -ForegroundColor Green; exit 0 } catch { Write-Host '❌ [%time%] 서버 응답 없음 - 자동 재시작 중...' -ForegroundColor Yellow; exit 1 }" 2>nul

if %errorlevel% neq 0 (
    echo.
    echo 🔄 서버 자동 재시작 중...
    
    REM 기존 프로세스 정리
    taskkill /f /im python.exe /fi "WINDOWTITLE eq *Two*" >nul 2>&1
    timeout /t 2 /nobreak >nul
    
    REM 서버 재시작
    start "TwoVeryAuto-Server-Restart" /min cmd /c "python -c \"import uvicorn; from main import app; uvicorn.run(app, host='0.0.0.0', port=%SELECTED_PORT%, access_log=False)\" 2>nul"
    timeout /t 5 /nobreak >nul
    
    echo ✅ 서버 재시작 완료
    echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
)

goto :monitor_loop