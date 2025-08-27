@echo off
chcp 65001 >nul
title Two Very Auto v3.2 - 통합 런처
cd /d "%~dp0"

echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    Two Very Auto v3.2                       ║
echo ║                   통합 런처 시스템                            ║
echo ╠══════════════════════════════════════════════════════════════╣
echo ║  🎯 실시간 바카라 모니터링 시스템                             ║
echo ║  📊 현대적 대시보드 인터페이스                                ║
echo ║  🔔 스마트 알림 시스템                                        ║
echo ║  📱 PWA 지원 모바일 친화적                                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Python 설치 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo 📥 https://python.org 에서 Python을 다운로드하고 설치하세요.
    echo.
    pause
    exit /b 1
)

REM 가상환경 확인 및 활성화
if exist "venv\Scripts\activate.bat" (
    echo 🔧 가상환경 활성화 중...
    call venv\Scripts\activate.bat
    echo ✅ 가상환경 활성화 완료
    echo.
) else (
    echo ℹ️  가상환경이 없습니다. 전역 Python 환경 사용
    echo.
)

REM 필수 모듈 설치 확인
echo 📦 필수 모듈 확인 중...
python -c "import flask, flask_cors" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  필수 모듈이 설치되어 있지 않습니다.
    echo 📥 설치를 시작합니다...
    pip install flask flask-cors
    if errorlevel 1 (
        echo ❌ 모듈 설치 실패
        echo.
        pause
        exit /b 1
    )
    echo ✅ 모듈 설치 완료
)

REM 런처 스크립트 존재 확인
if not exist "two_very_auto_launcher.py" (
    echo ❌ two_very_auto_launcher.py 파일을 찾을 수 없습니다.
    echo 📁 현재 디렉토리: %CD%
    echo.
    pause
    exit /b 1
)

echo ✅ 모든 준비가 완료되었습니다.
echo 🚀 런처를 시작합니다...
echo.

REM Python 런처 스크립트 실행
python two_very_auto_launcher.py

REM 실행 결과 확인
if errorlevel 1 (
    echo.
    echo ❌ 런처 실행 중 오류가 발생했습니다.
    echo 📋 오류 코드: %errorlevel%
) else (
    echo.
    echo ✅ 런처가 정상적으로 종료되었습니다.
)

echo.
echo ========================================
echo 런처 종료됨
echo ========================================
pause