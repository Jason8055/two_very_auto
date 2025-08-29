@echo off
chcp 65001 >nul
echo ========================================
echo 🎯 Two Very Auto - 페어 정보 시스템 서버
echo ========================================
echo.

REM 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  관리자 권한이 필요할 수 있습니다.
    echo    문제가 발생하면 "관리자로 실행"을 선택하세요.
    echo.
)

REM 현재 디렉토리를 fastapi_app으로 이동
cd /d "%~dp0"
echo 📂 현재 디렉토리: %CD%

REM Python 가상환경 확인
if exist "..\..\.venv\Scripts\activate.bat" (
    echo ✅ 가상환경 발견 - 활성화 중...
    call ..\..\.venv\Scripts\activate.bat
) else (
    echo ℹ️  가상환경이 없습니다. 전역 Python을 사용합니다.
)

REM Python 버전 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python을 찾을 수 없습니다.
    echo    Python이 설치되어 있고 PATH에 추가되어 있는지 확인하세요.
    pause
    exit /b 1
)

echo ✅ Python 버전: 
python --version

REM 필수 파일 확인
if not exist "main.py" (
    echo ❌ main.py 파일을 찾을 수 없습니다.
    echo    fastapi_app 폴더에서 실행했는지 확인하세요.
    pause
    exit /b 1
)

if not exist "start_server_simple.py" (
    echo ❌ start_server_simple.py 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)

echo ✅ 필수 파일 확인 완료

REM 기존 Python 프로세스 종료 (선택적)
echo.
echo 🔄 기존 서버 프로세스 정리 중...
taskkill /f /im "python.exe" /fi "WINDOWTITLE eq Two*" 2>nul
taskkill /f /im "python.exe" /fi "IMAGENAME eq python.exe" /fi "MEMUSAGE gt 50000" 2>nul

REM 포트 8080 사용 프로세스 확인 및 종료
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080') do (
    echo 🔍 포트 8080 사용 중인 프로세스 ID: %%a
    taskkill /f /pid %%a 2>nul
)

echo ✅ 프로세스 정리 완료
echo.

REM 필수 패키지 설치 확인
echo 📦 필수 패키지 확인 중...
python -c "import fastapi, uvicorn" 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  필수 패키지가 설치되지 않았습니다.
    echo    설치를 시도합니다...
    pip install fastapi uvicorn python-multipart
    if %errorlevel% neq 0 (
        echo ❌ 패키지 설치 실패
        pause
        exit /b 1
    )
)

echo ✅ 필수 패키지 확인 완료

REM 서버 시작
echo.
echo ========================================
echo 🚀 서버 시작 중...
echo ========================================

REM 서버 시작 방법 선택
echo 🎯 서버 시작 방법:
echo    1. 간단한 서버 시작 (권장)
echo    2. 직접 main.py 실행
echo    3. uvicorn 직접 실행
echo.
set /p choice="선택하세요 (1-3, 기본값: 1): "
if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    echo 📡 간단한 서버 시작 스크립트 실행 중...
    python start_server_simple.py
) else if "%choice%"=="2" (
    echo 📡 main.py 직접 실행 중...
    python main.py
) else if "%choice%"=="3" (
    echo 📡 uvicorn 직접 실행 중...
    uvicorn main:app --host 127.0.0.1 --port 8080 --reload
) else (
    echo ❌ 잘못된 선택입니다.
    pause
    exit /b 1
)

echo.
echo ========================================
echo 서버가 종료되었습니다.
echo ========================================
pause