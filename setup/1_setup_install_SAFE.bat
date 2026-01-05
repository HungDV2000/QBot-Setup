@echo off
REM ============================================================================
REM QBot v2.1 - SAFE MODE - Không bao giờ tự tắt
REM ============================================================================

title QBot Setup - SAFE MODE

echo.
echo ============================================
echo QBot v2.1 - Setup Installation (SAFE MODE)
echo ============================================
echo.
echo Script se KHONG BAO GIO tu dong tat!
echo.
pause

REM Test chcp
echo [1/10] Testing chcp UTF-8...
chcp 65001 >nul 2>&1
if errorlevel 1 (
    echo WARNING: Cannot set UTF-8, continuing anyway...
) else (
    echo OK: UTF-8 enabled
)
echo.
pause

REM Test current directory
echo [2/10] Current directory:
cd
echo.
pause

REM Test parent directory
echo [3/10] Parent directory files:
dir .. /b 2>&1
echo.
pause

REM Test requirements.txt
echo [4/10] Checking requirements.txt...
if exist ../requirements.txt (
    echo OK: requirements.txt found
) else (
    echo ERROR: requirements.txt NOT FOUND!
    echo Current dir: %CD%
    echo.
    pause
    exit /b 1
)
echo.
pause

REM Test log file creation
echo [5/10] Creating log files...
echo Test > info.txt 2>&1
if exist info.txt (
    echo OK: Can create info.txt
) else (
    echo ERROR: Cannot create info.txt
    pause
    exit /b 1
)
echo Test > error.txt 2>&1
if exist error.txt (
    echo OK: Can create error.txt
) else (
    echo ERROR: Cannot create error.txt
    pause
    exit /b 1
)
echo.
pause

REM Test Python
echo [6/10] Checking Python...
python --version 2>&1
if errorlevel 1 (
    echo.
    echo Python NOT FOUND - Will install automatically
    echo.
    set /p INSTALL_PY="Do you want to install Python? (Y/N): "
    if /i not "!INSTALL_PY!"=="Y" (
        echo Skipping Python installation
        pause
        exit /b 0
    )
) else (
    echo.
    echo Python FOUND - Good!
)
echo.
pause

REM Test pip
echo [7/10] Checking pip...
python -m pip --version 2>&1
if errorlevel 1 (
    echo pip NOT FOUND
) else (
    echo pip FOUND - Good!
)
echo.
pause

REM Ask to continue
echo [8/10] Ready to install libraries?
set /p CONTINUE="Continue with installation? (Y/N): "
if /i not "%CONTINUE%"=="Y" (
    echo Installation cancelled by user
    pause
    exit /b 0
)
echo.

REM Upgrade pip
echo [9/10] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo WARNING: pip upgrade failed, continuing...
)
echo.
pause

REM Install packages
echo [10/10] Installing packages...
echo This may take 2-5 minutes...
echo.
python -m pip install -r ../requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install packages
    echo.
    echo Please check:
    echo 1. Internet connection
    echo 2. Run as Administrator
    echo 3. Check requirements.txt exists
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo INSTALLATION COMPLETED SUCCESSFULLY!
echo ============================================
echo.
echo Next steps:
echo 1. Configure config.ini
echo 2. Run 2_check_environment.bat
echo 3. Run 3_qbot_manager.bat
echo.
pause
exit /b 0

