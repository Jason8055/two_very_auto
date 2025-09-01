@echo off
chcp 65001 >nul
color 0E
title 🔨 Two Very Auto EXE 파일 생성기

echo.
echo ===============================================================
echo                🔨 Two Very Auto EXE 파일 생성기
echo ===============================================================
echo.
echo 🎯 BAT 파일을 EXE 파일로 변환합니다
echo 📦 PyInstaller를 사용하여 전문적인 실행 파일을 만듭니다
echo.
echo ===============================================================
echo.

:: Python 설치 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo    https://python.org 에서 Python을 설치해주세요.
    echo.
    pause
    exit /b 1
)

echo ✅ Python 설치 확인됨

:: 필요한 패키지 설치
echo.
echo 📦 필요한 패키지 설치 중...
pip install pyinstaller >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ PyInstaller 설치 완료
) else (
    echo ❌ PyInstaller 설치 실패
    echo    인터넷 연결을 확인하고 다시 시도해주세요.
    pause
    exit /b 1
)

:: 작업 디렉토리 이동
cd /d "%~dp0python\fastapi_app"

echo.
echo 🔨 EXE 파일 생성 중...
echo.

:: GUI 버전 EXE 생성
echo 📱 GUI 버전 EXE 생성 중...
pyinstaller --onefile --windowed --name "TwoVeryAuto_런처" --distpath "..\..\dist" exe_launcher.py

if %errorlevel% equ 0 (
    echo ✅ GUI 버전 EXE 생성 완료!
) else (
    echo ❌ GUI 버전 EXE 생성 실패
)

:: 간단한 콘솔 버전도 생성
echo.
echo 📟 간단한 콘솔 버전 EXE 생성 중...

:: 임시 간단 스크립트 생성
echo import os, sys, subprocess > temp_simple.py
echo from pathlib import Path >> temp_simple.py
echo exe_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent >> temp_simple.py
echo bat_file = exe_dir / '🚀 서버 시작.bat' >> temp_simple.py
echo if bat_file.exists(): >> temp_simple.py
echo     subprocess.run([str(bat_file)], shell=True) >> temp_simple.py
echo else: >> temp_simple.py
echo     print(f"BAT 파일을 찾을 수 없습니다: {bat_file}") >> temp_simple.py
echo     input("계속하려면 Enter를 누르세요...") >> temp_simple.py

pyinstaller --onefile --console --name "TwoVeryAuto_간단실행" --distpath "..\..\dist" temp_simple.py

:: 임시 파일 정리
del temp_simple.py >nul 2>&1
del temp_simple.spec >nul 2>&1

if %errorlevel% equ 0 (
    echo ✅ 간단한 콘솔 버전 EXE 생성 완료!
) else (
    echo ❌ 간단한 콘솔 버전 EXE 생성 실패
)

:: build 폴더 정리
rmdir /s /q build >nul 2>&1
del *.spec >nul 2>&1

echo.
echo ===============================================================
echo                    🎉 EXE 파일 생성 완료!
echo ===============================================================
echo.

:: 결과 확인
cd /d "%~dp0"
if exist "dist\TwoVeryAuto_런처.exe" (
    echo ✅ TwoVeryAuto_런처.exe (GUI 버전)
    echo    → 예쁜 그래픽 화면으로 서버 실행
)

if exist "dist\TwoVeryAuto_간단실행.exe" (
    echo ✅ TwoVeryAuto_간단실행.exe (콘솔 버전) 
    echo    → 바로 BAT 파일 실행
)

echo.
echo 📁 EXE 파일 위치: %~dp0dist\
echo.
echo 💡 사용법:
echo 1. dist 폴더의 EXE 파일을 바탕화면에 복사
echo 2. EXE 파일을 더블클릭하여 실행
echo 3. 자동으로 서버가 시작되고 브라우저가 열립니다!
echo.

:: EXE 파일들을 루트 디렉토리로 복사
if exist "dist\TwoVeryAuto_런처.exe" (
    copy "dist\TwoVeryAuto_런처.exe" "." >nul 2>&1
    echo 📋 TwoVeryAuto_런처.exe를 메인 폴더에 복사했습니다
)

if exist "dist\TwoVeryAuto_간단실행.exe" (
    copy "dist\TwoVeryAuto_간단실행.exe" "." >nul 2>&1  
    echo 📋 TwoVeryAuto_간단실행.exe를 메인 폴더에 복사했습니다
)

echo.
echo 🚀 이제 EXE 파일을 더블클릭하면 모든 서버가 자동 실행됩니다!
echo.
pause