@echo off
echo ========================================
echo Two Very Auto - Windows 스케줄러 설정
echo ========================================

echo 관리자 권한을 확인하는 중...
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ 관리자 권한 확인됨
    echo.
    
    echo Windows 작업 스케줄러에 백업 작업을 등록합니다...
    python windows_task_scheduler.py
    
    echo.
    echo 등록된 작업 확인:
    schtasks /query /fo TABLE /tn "\TwoVeryAuto\*" 2>nul
    
    if %errorLevel% == 0 (
        echo ✅ 백업 작업이 성공적으로 등록되었습니다!
    ) else (
        echo ⚠️ 작업 등록을 확인할 수 없습니다.
        echo 수동 설정이 필요할 수 있습니다.
    )
    
) else (
    echo ❌ 관리자 권한이 필요합니다!
    echo.
    echo 이 배치 파일을 마우스 우클릭 → "관리자 권한으로 실행"을 선택하세요.
    echo.
    echo 또는 수동 설정 가이드를 확인하세요:
    echo python windows_task_scheduler.py
)

echo.
echo 완료되면 작업 스케줄러(taskschd.msc)에서 
echo TwoVeryAuto 폴더의 작업들을 확인할 수 있습니다.

pause