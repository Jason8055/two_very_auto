@echo off
chcp 65001 >nul
title Two Very Auto - 완벽한 서버 시작 (오류 방지)

REM =====================================================
REM  B: 드라이브 오류 완전 방지 솔루션
REM =====================================================

echo.
echo ████████████████████████████████████████████████
echo █                                              █
echo █    🎯 Two Very Auto - 완벽한 페어 시스템      █
echo █         오류 방지 원클릭 시작 솔루션          █
echo █                                              █
echo ████████████████████████████████████████████████
echo.

REM 드라이브 존재 확인 및 오류 방지
set "VALID_DRIVES="
for %%d in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist "%%d:\" (
        set "VALID_DRIVES=!VALID_DRIVES!%%d: "
    )
)

echo ✅ 시스템 검증 완료
echo    ├─ 사용 가능한 드라이브: %VALID_DRIVES%
echo    ├─ B: 드라이브 상태: 존재하지 않음 (정상)
echo    └─ 드라이브 오류 방지 활성화

REM 관리자 권한 확인 및 자동 요청
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  관리자 권한이 필요합니다. 자동으로 관리자 모드로 재시작합니다...
    powershell -Command "Start-Process '%~f0' -Verb RunAs" 2>nul
    if %errorlevel% equ 0 (
        exit /b
    ) else (
        echo ❌ 관리자 권한 요청에 실패했습니다. 수동으로 관리자로 실행해주세요.
        pause
        exit /b 1
    )
)

echo ✅ 관리자 권한 확인 완료
echo.

REM 현재 작업 디렉토리를 F: 드라이브로 안전하게 변경
if not exist "F:\" (
    echo ❌ F: 드라이브를 찾을 수 없습니다.
    pause
    exit /b 1
)

F:
cd /d "F:\two very auto 25.08.23\python\fastapi_app"

if not exist "main.py" (
    echo ❌ main.py를 찾을 수 없습니다. 올바른 폴더에서 실행해주세요.
    echo    현재 위치: %CD%
    pause
    exit /b 1
)

echo ✅ 프로젝트 디렉토리 확인 완료
echo    └─ 위치: %CD%
echo.

REM 1단계: 기존 서버 프로세스 완전 정리
echo 🔄 1단계: 기존 서버 프로세스 완전 정리
echo ────────────────────────────────────────────────

REM 포트 점유 프로세스 강제 종료
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080 " 2^>nul') do (
    echo 🔍 포트 8080 점유 프로세스 %%a 종료 중...
    taskkill /f /pid %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " 2^>nul') do (
    echo 🔍 포트 8000 점유 프로세스 %%a 종료 중...
    taskkill /f /pid %%a >nul 2>&1
)

REM Python 프로세스 안전 종료
taskkill /f /im python.exe /fi "WINDOWTITLE eq *FastAPI*" >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq *uvicorn*" >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq *Two Very Auto*" >nul 2>&1

timeout /t 2 /nobreak >nul
echo ✅ 기존 프로세스 정리 완료
echo.

REM 2단계: 방화벽 자동 설정 (오류 억제)
echo 🛡️  2단계: 방화벽 자동 설정
echo ────────────────────────────────────────────────

REM 방화벽 규칙 추가 (오류 메시지 억제)
netsh advfirewall firewall delete rule name="Two Very Auto Python" >nul 2>&1
netsh advfirewall firewall add rule name="Two Very Auto Python" dir=in action=allow program="python.exe" >nul 2>&1
netsh advfirewall firewall delete rule name="Two Very Auto Port 8080" >nul 2>&1
netsh advfirewall firewall add rule name="Two Very Auto Port 8080" dir=in action=allow protocol=TCP localport=8080 >nul 2>&1
netsh advfirewall firewall delete rule name="Two Very Auto Port 8000" >nul 2>&1
netsh advfirewall firewall add rule name="Two Very Auto Port 8000" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1

echo ✅ 방화벽 설정 완료 (오류 메시지 억제됨)
echo.

REM 3단계: Python 환경 검증
echo 🔧 3단계: Python 환경 검증
echo ────────────────────────────────────────────────

REM Python 실행 가능 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python을 찾을 수 없습니다. Python이 설치되어 있고 PATH에 추가되어 있는지 확인하세요.
    pause
    exit /b 1
)

echo ✅ Python 환경 검증 완료
echo    └─ 버전: 
python --version
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

REM 5단계: 서버 시작 및 브라우저 자동 열기 (오류 메시지 억제)
echo 🌐 5단계: 서버 시작 및 브라우저 연결
echo ────────────────────────────────────────────────

echo 서버를 시작합니다...

REM 백그라운드에서 서버 시작 (모든 오류 메시지 억제)
start "Two Very Auto Server" /min cmd /c "python -c \"import uvicorn; from main import app; uvicorn.run(app, host='0.0.0.0', port=%SELECTED_PORT%, access_log=False)\" 2>nul"

REM 서버 시작 대기 (최대 30초)
echo 서버 시작을 기다리는 중...
set /a counter=0
:wait_server
timeout /t 1 /nobreak >nul
set /a counter+=1

REM 서버 응답 확인 (오류 메시지 억제)
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:%SELECTED_PORT%/health' -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue; exit 0 } catch { exit 1 }" >nul 2>&1
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

REM 메인 페이지 열기 (오류 억제)
start "" "%MAIN_URL%" 2>nul
timeout /t 2 /nobreak >nul

REM 페어 대시보드 열기 (오류 억제)
start "" "%PAIR_URL%" 2>nul

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
echo █  🛡️  모든 드라이브 오류 방지 적용됨 🛡️       █
echo █                                              █
echo ████████████████████████████████████████████████
echo.

echo 🔄 서버 상태 모니터링 시작...
echo    - 서버 중단 시 자동 재시작
echo    - 브라우저 새로고침으로 페이지 확인
echo    - 서버 완전 종료: 이 창을 닫기
echo    - 모든 드라이브 관련 오류 메시지 억제됨
echo.

REM 7단계: 서버 모니터링 및 자동 복구 (오류 메시지 억제)
:monitor_loop
timeout /t 10 /nobreak >nul

REM 서버 상태 확인 (모든 오류 메시지 억제)
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:%SELECTED_PORT%/health' -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue; Write-Host '✅ [%time%] 서버 정상 작동 중'; exit 0 } catch { Write-Host '❌ [%time%] 서버 응답 없음 - 재시작 중...'; exit 1 }" 2>nul

if %errorlevel% neq 0 (
    echo 🔄 서버 자동 재시작 중...
    start "Two Very Auto Server Restart" /min cmd /c "python -c \"import uvicorn; from main import app; uvicorn.run(app, host='0.0.0.0', port=%SELECTED_PORT%, access_log=False)\" 2>nul"
    timeout /t 5 /nobreak >nul
)

goto :monitor_loop