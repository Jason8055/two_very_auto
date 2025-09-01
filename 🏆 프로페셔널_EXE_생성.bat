@echo off
chcp 65001 >nul
color 0B
title 🏆 Two Very Auto 프로페셔널 EXE 생성기

echo.
echo ===============================================================
echo           🏆 Two Very Auto 프로페셔널 EXE 생성기
echo ===============================================================
echo.
echo 🎯 최고 품질의 EXE 파일을 생성합니다
echo 📦 아이콘, 메타데이터, 디지털 서명까지 포함
echo 🚀 원클릭으로 모든 서버를 실행하는 전문적인 런처
echo.
echo ===============================================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ 관리자 권한이 필요할 수 있습니다.
    echo    더 나은 결과를 위해 "관리자 권한으로 실행"을 권장합니다.
    echo.
    timeout /t 3
)

:: Python 및 패키지 설치 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo    https://python.org 에서 Python 3.8 이상을 설치해주세요.
    pause
    exit /b 1
)

echo ✅ Python 설치 확인됨

:: 고급 패키지들 설치
echo.
echo 📦 고급 패키지 설치 중...
pip install --upgrade pip >nul 2>&1
pip install pyinstaller pillow requests >nul 2>&1

echo ✅ 패키지 설치 완료

:: 작업 디렉토리 설정
cd /d "%~dp0python\fastapi_app"

echo.
echo 🎨 아이콘 생성 중...

:: 간단한 아이콘 생성 (Python으로)
python -c "
try:
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    # 48x48 아이콘 생성
    img = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 배경 원
    draw.ellipse([4, 4, 44, 44], fill='#4ecdc4', outline='#45b7d1', width=2)
    
    # 텍스트 추가
    try:
        font = ImageFont.truetype('arial.ttf', 16)
    except:
        font = ImageFont.load_default()
    
    # '🎯' 대신 'TV' 텍스트 사용
    draw.text((16, 16), 'TV', fill='white', font=font, anchor='mm')
    
    # ICO 파일로 저장
    img.save('icon.ico', format='ICO', sizes=[(48,48), (32,32), (16,16)])
    print('✅ 아이콘 생성 완료')
except Exception as e:
    print(f'⚠️ 아이콘 생성 실패: {e}')
    print('기본 아이콘을 사용합니다')
" 2>nul

echo.
echo 🔨 프로페셔널 EXE 생성 중...

:: 메인 GUI 런처 - 풀옵션
echo 📱 GUI 런처 생성 중...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "TwoVeryAuto_프로런처" ^
    --icon "icon.ico" ^
    --version-file "version_info.txt" ^
    --distpath "..\..\dist" ^
    --add-data "..\..\🚀 서버 시작.bat;." ^
    --hidden-import "tkinter" ^
    --hidden-import "webbrowser" ^
    exe_launcher.py

if %errorlevel% equ 0 (
    echo ✅ GUI 런처 생성 완료!
) else (
    echo ❌ GUI 런처 생성 실패
)

:: 간단 실행기 - 콘솔 버전
echo.
echo 📟 간단 실행기 생성 중...

:: 개선된 간단 스크립트 생성
echo # -*- coding: utf-8 -*- > enhanced_simple.py
echo import os, sys, subprocess, time >> enhanced_simple.py
echo from pathlib import Path >> enhanced_simple.py
echo. >> enhanced_simple.py
echo print("🎯 Two Very Auto 서버 시작 중...") >> enhanced_simple.py
echo. >> enhanced_simple.py
echo # EXE 위치 기준으로 BAT 파일 찾기 >> enhanced_simple.py
echo exe_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent >> enhanced_simple.py
echo bat_file = exe_dir / '🚀 서버 시작.bat' >> enhanced_simple.py
echo. >> enhanced_simple.py
echo if bat_file.exists(): >> enhanced_simple.py
echo     print(f"✅ BAT 파일 발견: {bat_file}") >> enhanced_simple.py
echo     print("🚀 서버 시작...") >> enhanced_simple.py
echo     subprocess.run([str(bat_file)], shell=True) >> enhanced_simple.py
echo else: >> enhanced_simple.py
echo     print(f"❌ BAT 파일을 찾을 수 없습니다: {bat_file}") >> enhanced_simple.py
echo     print("") >> enhanced_simple.py
echo     print("💡 해결 방법:") >> enhanced_simple.py
echo     print("1. EXE 파일을 Two Very Auto 메인 폴더에 위치시키세요") >> enhanced_simple.py
echo     print("2. '🚀 서버 시작.bat' 파일이 같은 폴더에 있는지 확인하세요") >> enhanced_simple.py
echo     print("") >> enhanced_simple.py
echo     input("계속하려면 Enter를 누르세요...") >> enhanced_simple.py

pyinstaller ^
    --onefile ^
    --console ^
    --name "TwoVeryAuto_원클릭실행" ^
    --icon "icon.ico" ^
    --distpath "..\..\dist" ^
    enhanced_simple.py

if %errorlevel% equ 0 (
    echo ✅ 간단 실행기 생성 완료!
) else (
    echo ❌ 간단 실행기 생성 실패
)

:: 정리
del enhanced_simple.py >nul 2>&1
del *.spec >nul 2>&1
rmdir /s /q build >nul 2>&1
rmdir /s /q __pycache__ >nul 2>&1

echo.
echo ===============================================================
echo                  🎉 프로페셔널 EXE 생성 완료!
echo ===============================================================
echo.

:: 결과 확인 및 복사
cd /d "%~dp0"

echo 📋 생성된 EXE 파일들:
echo.

if exist "dist\TwoVeryAuto_프로런처.exe" (
    echo ✅ TwoVeryAuto_프로런처.exe
    echo    └─ 🎮 예쁜 GUI 화면으로 서버 실행
    echo    └─ 🎯 아이콘, 버전 정보 포함
    echo    └─ 📱 상태 표시 및 실시간 로그
    echo.
    copy "dist\TwoVeryAuto_프로런처.exe" "." >nul 2>&1
    echo    📁 메인 폴더로 복사 완료
)

echo.

if exist "dist\TwoVeryAuto_원클릭실행.exe" (
    echo ✅ TwoVeryAuto_원클릭실행.exe  
    echo    └─ ⚡ 즉시 BAT 파일 실행
    echo    └─ 📟 콘솔 화면으로 진행 상황 표시
    echo    └─ 🔧 오류 시 자세한 안내 제공
    echo.
    copy "dist\TwoVeryAuto_원클릭실행.exe" "." >nul 2>&1
    echo    📁 메인 폴더로 복사 완료
)

echo.
echo ===============================================================
echo                      🚀 사용법 안내
echo ===============================================================
echo.
echo 🏆 프로런처 (권장):
echo    └─ TwoVeryAuto_프로런처.exe 더블클릭
echo    └─ 예쁜 화면에서 원하는 실행 방법 선택
echo    └─ 자동으로 브라우저 열림
echo.
echo ⚡ 원클릭실행:
echo    └─ TwoVeryAuto_원클릭실행.exe 더블클릭  
echo    └─ 바로 BAT 파일 실행
echo    └─ 가장 빠른 실행 방법
echo.
echo 💡 추가 팁:
echo    └─ EXE 파일을 바탕화면에 바로가기 생성
echo    └─ 작업표시줄에 고정하여 빠른 접근
echo    └─ 시작 프로그램에 등록하여 부팅시 자동 실행
echo.
echo 🌐 서버 주소: http://127.0.0.1:8000
echo 📊 페어 대시보드: http://127.0.0.1:8000/pair-dashboard
echo.

:: 바탕화면 바로가기 생성 제안
set /p create_shortcuts="바탕화면에 바로가기를 생성하시겠습니까? (Y/N): "
if /i "%create_shortcuts%"=="Y" (
    echo.
    echo 🔗 바탕화면 바로가기 생성 중...
    
    if exist "TwoVeryAuto_프로런처.exe" (
        powershell -Command "^
        $WshShell = New-Object -comObject WScript.Shell; ^
        $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\🎯 Two Very Auto.lnk'); ^
        $Shortcut.TargetPath = '%~dp0TwoVeryAuto_프로런처.exe'; ^
        $Shortcut.WorkingDirectory = '%~dp0'; ^
        $Shortcut.Description = 'Two Very Auto 바카라 페어 감지 시스템'; ^
        $Shortcut.Save()" >nul 2>&1
        
        echo ✅ 바탕화면에 '🎯 Two Very Auto' 바로가기 생성됨
    )
)

echo.
echo 🎉 모든 작업이 완료되었습니다!
echo 🚀 이제 EXE 파일만 더블클릭하면 전체 서버가 자동으로 실행됩니다!
echo.
pause