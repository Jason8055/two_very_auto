@echo off
chcp 65001 >nul
title 바탕화면 바로가기 생성

echo.
echo 🔗 Two Very Auto 바탕화면 바로가기 생성 중...
echo.

:: PowerShell을 사용해 바탕화면에 바로가기 생성
powershell -Command ^
"$WshShell = New-Object -comObject WScript.Shell; ^
$Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\🎯 Two Very Auto 서버.lnk'); ^
$Shortcut.TargetPath = '%~dp0🚀 서버 시작.bat'; ^
$Shortcut.WorkingDirectory = '%~dp0'; ^
$Shortcut.Description = 'Two Very Auto 바카라 페어 감지 시스템'; ^
$Shortcut.Save()"

:: GUI 런처 바로가기도 생성
powershell -Command ^
"$WshShell = New-Object -comObject WScript.Shell; ^
$Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\🎮 Two Very Auto GUI.lnk'); ^
$Shortcut.TargetPath = 'python'; ^
$Shortcut.Arguments = '%~dp0python\fastapi_app\launcher.py'; ^
$Shortcut.WorkingDirectory = '%~dp0python\fastapi_app'; ^
$Shortcut.Description = 'Two Very Auto GUI 런처'; ^
$Shortcut.Save()"

echo ✅ 바탕화면에 바로가기가 생성되었습니다!
echo.
echo 🎯 Two Very Auto 서버 - 간단한 배치 파일 실행
echo 🎮 Two Very Auto GUI - 그래픽 인터페이스 런처
echo.
pause