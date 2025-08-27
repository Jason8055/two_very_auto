@echo off
echo =====================================
echo 연결 안정성 테스트 시작
echo =====================================
echo.

set SUCCESS=0
set TOTAL=0

for /l %%i in (1,1,10) do (
    set /a TOTAL+=1
    echo [%%i/10] 연결 테스트 중...
    
    curl -s --max-time 5 http://127.0.0.1:8005/health >nul 2>&1
    if !errorlevel! equ 0 (
        echo   Simple Server: OK
        set /a SUCCESS+=1
    ) else (
        echo   Simple Server: FAILED
    )
    
    curl -s --max-time 5 http://127.0.0.1:8006/health >nul 2>&1
    if !errorlevel! equ 0 (
        echo   Main Server: OK
        set /a SUCCESS+=1
    ) else (
        echo   Main Server: FAILED
    )
    
    set /a TOTAL+=1
    echo.
    timeout /t 2 /nobreak >nul
)

echo =====================================
echo 테스트 완료
echo =====================================
echo 총 테스트: %TOTAL%
echo 성공: %SUCCESS%
set /a RATE=%SUCCESS%*100/%TOTAL%
echo 성공률: %RATE%%%
echo =====================================