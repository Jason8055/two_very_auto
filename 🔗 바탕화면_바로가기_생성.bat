@echo off
chcp 65001 >nul
color 0A
title 🔗 Two Very Auto - 바탕화면 바로가기 생성

echo.
echo ===============================================================
echo           🔗 Two Very Auto 바탕화면 바로가기 생성기
echo ===============================================================
echo.
echo 🎯 바탕화면에 Two Very Auto 바로가기를 생성합니다
echo 📱 더 쉽고 빠른 접근을 위해 바로가기를 만들어보세요
echo.
echo ===============================================================
echo.

:: 현재 폴더에 EXE 파일이 있는지 확인
if not exist "TwoVeryAuto_프로런처.exe" (
    echo ❌ TwoVeryAuto_프로런처.exe 파일을 찾을 수 없습니다.
    echo    먼저 EXE 파일을 생성해주세요.
    echo.
    pause
    exit /b 1
)

echo ✅ EXE 파일 확인됨
echo.

:: PowerShell을 사용하여 바로가기 생성
echo 🔗 바탕화면 바로가기 생성 중...

powershell -Command "
    $WshShell = New-Object -comObject WScript.Shell;
    $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\🎯 Two Very Auto.lnk');
    $Shortcut.TargetPath = '%~dp0TwoVeryAuto_프로런처.exe';
    $Shortcut.WorkingDirectory = '%~dp0';
    $Shortcut.Description = 'Two Very Auto 바카라 페어 감지 시스템';
    $Shortcut.IconLocation = '%~dp0TwoVeryAuto_프로런처.exe,0';
    $Shortcut.Save()
" >nul 2>&1

if %errorlevel% equ 0 (
    echo ✅ 바탕화면에 '🎯 Two Very Auto' 바로가기가 생성되었습니다!
) else (
    echo ❌ 바로가기 생성에 실패했습니다.
    echo    관리자 권한으로 다시 실행해보세요.
)

echo.
echo ===============================================================
echo                     🎉 작업 완료!
echo ===============================================================
echo.
echo 💡 사용법:
echo 1. 바탕화면의 '🎯 Two Very Auto' 바로가기를 더블클릭
echo 2. GUI 화면에서 원하는 실행 방법 선택
echo 3. 자동으로 서버가 시작되고 브라우저가 열립니다
echo.
echo 🌐 서버 주소: http://127.0.0.1:8000
echo 📊 페어 대시보드: http://127.0.0.1:8000/pair-dashboard
echo.

pause