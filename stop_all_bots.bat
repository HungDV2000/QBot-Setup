@echo off
REM QBot - Stop All Bots Script (Windows)

echo ========================================
echo QBot - Stopping All Modules (Windows)
echo ========================================

echo Searching for QBot python processes...
echo.

REM List all python processes with "hd_" in command line
tasklist /FI "IMAGENAME eq python.exe" /V | findstr /I "hd_"

echo.
set /p CONFIRM=Do you want to stop all QBot modules? (Y/N):

if /I "%CONFIRM%"=="Y" (
    echo.
    echo Stopping all python processes running hd_ scripts...
    
    REM Kill all python processes (be careful!)
    REM Better: Kill only specific windows
    for /F "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq QBot*" ^| findstr /I "python"') do (
        echo Killing PID %%i...
        taskkill /PID %%i /F
    )
    
    echo.
    echo All modules stopped!
) else (
    echo.
    echo Cancelled.
)

echo ========================================
pause

