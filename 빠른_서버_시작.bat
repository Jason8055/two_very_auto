@echo off
title Two Very Auto - 빠른 서버 시작

echo 🎯 Two Very Auto - 빠른 서버 시작
echo ========================================

REM 관리자 권한으로 자동 재시작
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 관리자 권한으로 재시작 중...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

REM 기존 프로세스 정리
taskkill /f /im python.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080 "') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 "') do taskkill /f /pid %%a >nul 2>&1

REM 방화벽 규칙 추가
netsh advfirewall firewall add rule name="TwoVeryAuto" dir=in action=allow protocol=TCP localport=8080 >nul 2>&1
netsh advfirewall firewall add rule name="TwoVeryAuto8000" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1

cd /d "%~dp0python\fastapi_app"

REM 포트 8080 시도
echo 포트 8080 시도 중...
start "TwoVeryAuto" /min cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8080"
timeout /t 5 /nobreak >nul

powershell -Command "try { Invoke-WebRequest 'http://127.0.0.1:8080/health' -TimeoutSec 3 -UseBasicParsing | Out-Null; Write-Host '✅ 포트 8080 성공'; start 'http://127.0.0.1:8080'; start 'http://127.0.0.1:8080/pair-dashboard'; exit 0 } catch { Write-Host '❌ 포트 8080 실패, 8000 시도 중...'; exit 1 }"

if %errorlevel% equ 0 goto :success

REM 포트 8000 시도
echo 포트 8000 시도 중...
taskkill /f /im python.exe >nul 2>&1
start "TwoVeryAuto" /min cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8000"
timeout /t 5 /nobreak >nul

powershell -Command "try { Invoke-WebRequest 'http://127.0.0.1:8000/health' -TimeoutSec 3 -UseBasicParsing | Out-Null; Write-Host '✅ 포트 8000 성공'; start 'http://127.0.0.1:8000'; start 'http://127.0.0.1:8000/pair-dashboard'; exit 0 } catch { Write-Host '❌ 연결 실패'; exit 1 }"

if %errorlevel% equ 0 goto :success

echo ❌ 서버 시작 실패
pause
exit /b 1

:success
echo ✅ 서버 시작 성공! 브라우저가 자동으로 열렸습니다.
echo 서버를 종료하려면 이 창을 닫으세요.
pause