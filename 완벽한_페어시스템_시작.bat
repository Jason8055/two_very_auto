@echo off
chcp 65001 >nul
title Two Very Auto - 완벽한 페어 시스템 시작

echo.
echo ████████████████████████████████████████████████
echo █                                              █
echo █    🎯 Two Very Auto - 완벽한 페어 시스템      █
echo █         원클릭 시작 솔루션                    █
echo █                                              █
echo ████████████████████████████████████████████████
echo.

REM 관리자 권한 확인 및 자동 요청
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  관리자 권한이 필요합니다. 자동으로 관리자 모드로 재시작합니다...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ✅ 관리자 권한 확인 완료
echo.

REM 1단계: 모든 기존 Python 서버 프로세스 완전 정리
echo 🔄 1단계: 기존 서버 프로세스 완전 정리
echo ────────────────────────────────────────────────

REM 포트 점유 프로세스 강제 종료
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080 "') do (
    echo 🔍 포트 8080 점유 프로세스 %%a 종료 중...
    taskkill /f /pid %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 "') do (
    echo 🔍 포트 8000 점유 프로세스 %%a 종료 중...
    taskkill /f /pid %%a >nul 2>&1
)

REM FastAPI 관련 Python 프로세스 종료
taskkill /f /im python.exe /fi "WINDOWTITLE eq *FastAPI*" >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq *uvicorn*" >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq *Two Very Auto*" >nul 2>&1

REM 메모리 사용량이 높은 Python 프로세스 종료 (서버로 추정)
for /f "tokens=1,2" %%a in ('tasklist /fi "imagename eq python.exe" /fo csv ^| findstr /v "ImageName"') do (
    set processname=%%a
    set pid=%%b
    set processname=!processname:"=!
    set pid=!pid:"=!
    taskkill /f /pid !pid! >nul 2>&1
)

timeout /t 2 /nobreak >nul
echo ✅ 기존 프로세스 정리 완료
echo.

REM 2단계: 방화벽 자동 설정
echo 🛡️  2단계: 방화벽 자동 설정
echo ────────────────────────────────────────────────

REM Windows 방화벽에서 Python 허용 규칙 추가
netsh advfirewall firewall delete rule name="Two Very Auto Python" >nul 2>&1
netsh advfirewall firewall add rule name="Two Very Auto Python" dir=in action=allow program="%SystemRoot%\System32\python.exe" >nul 2>&1
netsh advfirewall firewall add rule name="Two Very Auto Python Local" dir=in action=allow program="C:\Python*\python.exe" >nul 2>&1

REM 포트 기반 방화벽 규칙 추가
netsh advfirewall firewall delete rule name="Two Very Auto Port 8080" >nul 2>&1
netsh advfirewall firewall add rule name="Two Very Auto Port 8080" dir=in action=allow protocol=TCP localport=8080 >nul 2>&1

netsh advfirewall firewall delete rule name="Two Very Auto Port 8000" >nul 2>&1
netsh advfirewall firewall add rule name="Two Very Auto Port 8000" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1

echo ✅ 방화벽 설정 완료
echo.

REM 3단계: 환경 검증 및 준비
echo 🔧 3단계: 환경 검증 및 준비
echo ────────────────────────────────────────────────

cd /d "%~dp0python\fastapi_app"
if not exist "main.py" (
    echo ❌ main.py를 찾을 수 없습니다. 올바른 폴더에서 실행해주세요.
    pause
    exit /b 1
)

REM Python 및 필수 패키지 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python을 찾을 수 없습니다.
    pause
    exit /b 1
)

echo ✅ 환경 검증 완료
echo.

REM 4단계: 스마트 포트 선택 및 서버 시작
echo 🚀 4단계: 스마트 서버 시작
echo ────────────────────────────────────────────────

REM 사용 가능한 포트 찾기
set SELECTED_PORT=
for %%p in (8080 8000 3000 9999 7777 5000 8888 7000) do (
    netstat -ano | findstr ":%%p " >nul 2>&1
    if !errorlevel! neq 0 (
        set SELECTED_PORT=%%p
        goto :found_port
    )
)

:found_port
if "%SELECTED_PORT%"=="" (
    echo ❌ 사용 가능한 포트를 찾을 수 없습니다.
    pause
    exit /b 1
)

echo ✅ 선택된 포트: %SELECTED_PORT%
echo.

REM 5단계: 서버 시작 및 브라우저 자동 열기
echo 🌐 5단계: 서버 시작 및 브라우저 연결
echo ────────────────────────────────────────────────

echo 서버를 시작합니다...

REM 백그라운드에서 서버 시작
start "Two Very Auto Server" /min cmd /c "python -c \"import uvicorn; from main import app; uvicorn.run(app, host='0.0.0.0', port=%SELECTED_PORT%, access_log=False)\""

REM 서버 시작 대기 (최대 30초)
echo 서버 시작을 기다리는 중...
set /a counter=0
:wait_server
timeout /t 1 /nobreak >nul
set /a counter+=1

REM 서버 응답 확인
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:%SELECTED_PORT%/health' -TimeoutSec 2 -UseBasicParsing; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 goto :server_ready

if %counter% lss 30 goto :wait_server

echo ❌ 서버 시작에 실패했습니다.
pause
exit /b 1

:server_ready
echo ✅ 서버가 성공적으로 시작되었습니다!
echo.

REM 6단계: 브라우저 자동 열기
echo 🎯 6단계: 자동 브라우저 접속
echo ────────────────────────────────────────────────

set MAIN_URL=http://127.0.0.1:%SELECTED_PORT%
set PAIR_URL=http://127.0.0.1:%SELECTED_PORT%/pair-dashboard
set API_URL=http://127.0.0.1:%SELECTED_PORT%/docs

echo 📱 자동으로 브라우저가 열립니다...

REM 메인 페이지 열기
start "" "%MAIN_URL%"
timeout /t 2 /nobreak >nul

REM 페어 대시보드 열기
start "" "%PAIR_URL%"

echo.
echo ████████████████████████████████████████████████
echo █                                              █
echo █           🎉 시작 완료! 🎉                   █
echo █                                              █
echo █  📱 메인 페이지: %MAIN_URL%
echo █  🎯 페어 대시보드: %PAIR_URL%
echo █  📖 API 문서: %API_URL%
echo █                                              █
echo █  ✨ 이제 완벽하게 접속할 수 있습니다! ✨      █
echo █                                              █
echo ████████████████████████████████████████████████
echo.

echo 🔄 서버 상태 모니터링 시작...
echo    - 서버 중단 시 자동 재시작
echo    - 브라우저 새로고침으로 페이지 확인
echo    - 서버 완전 종료: 이 창을 닫기
echo.

REM 7단계: 서버 모니터링 및 자동 복구
:monitor_loop
timeout /t 10 /nobreak >nul

REM 서버 상태 확인
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:%SELECTED_PORT%/health' -TimeoutSec 3 -UseBasicParsing; Write-Host '✅ [%time%] 서버 정상 작동 중'; exit 0 } catch { Write-Host '❌ [%time%] 서버 응답 없음 - 재시작 중...'; exit 1 }"

if %errorlevel% neq 0 (
    echo 🔄 서버 자동 재시작 중...
    start "Two Very Auto Server Restart" /min cmd /c "python -c \"import uvicorn; from main import app; uvicorn.run(app, host='0.0.0.0', port=%SELECTED_PORT%, access_log=False)\""
    timeout /t 5 /nobreak >nul
)

goto :monitor_loop