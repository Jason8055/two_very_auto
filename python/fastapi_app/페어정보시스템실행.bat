@echo off
chcp 65001 > nul
title Two Very Auto - 페어 정보 시스템

echo.
echo ==========================================
echo 🎯 Two Very Auto - 페어 정보 시스템
echo ==========================================
echo 🎰 실시간 바카라 페어 감지 및 알림 시스템
echo 📊 패턴 분석 · 🔔 즉시 알림 · 📈 상세 통계
echo ==========================================
echo.

:: 현재 디렉토리로 이동
cd /d "%~dp0"

:: Python 경로 확인
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되지 않았거나 PATH에 추가되지 않았습니다.
    echo    Python을 설치하고 PATH에 추가한 후 다시 시도해주세요.
    pause
    exit /b 1
)

:: 파일 존재 확인
if not exist "main.py" (
    echo ❌ main.py 파일을 찾을 수 없습니다.
    echo    현재 디렉토리: %CD%
    pause
    exit /b 1
)

echo 🚀 페어 정보 시스템 시작 중...
echo.

:: 새로운 시작 스크립트 사용 (있는 경우)
if exist "start_pair_system.py" (
    echo 🎯 향상된 시작 스크립트 사용
    python start_pair_system.py
) else (
    echo 🎯 기본 서버 시작
    python main.py
)

:: 실행 결과에 따른 메시지
if %errorlevel% neq 0 (
    echo.
    echo ❌ 서버 실행 중 오류가 발생했습니다.
    echo.
    echo 🔧 문제 해결 방법:
    echo 1. 다른 프로그램이 포트를 사용 중인지 확인
    echo 2. 방화벽 설정 확인
    echo 3. 관리자 권한으로 실행 시도
    echo 4. Python 환경 설정 확인
    echo.
    pause
    exit /b %errorlevel%
)

echo.
echo 🎯 서버가 정상적으로 종료되었습니다.
pause