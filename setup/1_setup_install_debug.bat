@echo off
REM ============================================================================
REM QBot v2.1 - Setup DEBUG Version
REM Kiểm tra lỗi khi chạy script
REM ============================================================================

title QBot Setup - DEBUG MODE

echo ========================================
echo DEBUG MODE - Checking script errors
echo ========================================
echo.

REM Test 1: Check current directory
echo [TEST 1] Current directory:
cd
echo.

REM Test 2: Check parent directory
echo [TEST 2] Parent directory contents:
dir .. /b
echo.

REM Test 3: Check if requirements.txt exists
echo [TEST 3] Checking requirements.txt:
if exist ../requirements.txt (
    echo    ✅ ../requirements.txt EXISTS
) else (
    echo    ❌ ../requirements.txt NOT FOUND
)
echo.

REM Test 4: Check if config.ini exists
echo [TEST 4] Checking config.ini:
if exist ../config.ini (
    echo    ✅ ../config.ini EXISTS
) else (
    echo    ℹ️  ../config.ini NOT FOUND (OK, will create)
)
echo.

REM Test 5: Check Python
echo [TEST 5] Checking Python:
python --version 2>&1
if errorlevel 1 (
    echo    ❌ Python NOT FOUND
) else (
    echo    ✅ Python FOUND
)
echo.

REM Test 6: Check pip
echo [TEST 6] Checking pip:
python -m pip --version 2>&1
if errorlevel 1 (
    echo    ❌ pip NOT FOUND
) else (
    echo    ✅ pip FOUND
)
echo.

REM Test 7: Try to create log file
echo [TEST 7] Creating test log file:
echo Test log > debug_test.txt 2>&1
if exist debug_test.txt (
    echo    ✅ Can create files in current directory
    del debug_test.txt
) else (
    echo    ❌ Cannot create files (permission issue?)
)
echo.

REM Test 8: Check UTF-8 encoding
echo [TEST 8] Testing UTF-8 characters:
echo    Testing: ✅ ❌ 🔄 📝 ⚠️
echo.

echo ========================================
echo DEBUG COMPLETED
echo ========================================
echo.
echo 💡 Vui lòng gửi kết quả này để được hỗ trợ
echo.
pause

