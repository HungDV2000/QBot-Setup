@echo off
chcp 65001 >nul
REM ============================================================================
REM QBot v2.0 - Environment Checker
REM Kiểm tra đầy đủ môi trường: Python, Libraries, Files
REM ============================================================================

title QBot - Kiểm Tra Môi Trường

cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║              QBot v2.0 - Kiểm Tra Môi Trường                           ║
echo ║              Environment Verification                                  ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

set TOTAL_CHECKS=0
set PASSED_CHECKS=0
set WARNING_CHECKS=0
set FAILED_CHECKS=0

REM ============================================================================
REM 1. KIỂM TRA PYTHON
REM ============================================================================
echo [1] KIỂM TRA PYTHON
echo ═══════════════════════════════════════════════════════════════════════
set /a TOTAL_CHECKS+=1

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ FAIL: Python không được cài đặt
    echo    💡 Tải từ: https://www.python.org/downloads/
    set /a FAILED_CHECKS+=1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo ✅ PASS: Python %PYTHON_VERSION% đã cài đặt
    set /a PASSED_CHECKS+=1
)
echo.

REM ============================================================================
REM 2. KIỂM TRA PIP
REM ============================================================================
echo [2] KIỂM TRA PIP (Package Manager)
echo ═══════════════════════════════════════════════════════════════════════
set /a TOTAL_CHECKS+=1

python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ FAIL: pip không có sẵn
    set /a FAILED_CHECKS+=1
) else (
    for /f "tokens=2" %%i in ('python -m pip --version 2^>^&1') do set PIP_VERSION=%%i
    echo ✅ PASS: pip %PIP_VERSION% đã cài đặt
    set /a PASSED_CHECKS+=1
)
echo.

REM ============================================================================
REM 3. KIỂM TRA THƯ VIỆN PYTHON
REM ============================================================================
echo [3] KIỂM TRA THƯ VIỆN PYTHON
echo ═══════════════════════════════════════════════════════════════════════
echo Đang kiểm tra 15 thư viện cần thiết...
echo.

REM Create temp Python script for library checking
(
    echo import sys
    echo.
    echo libraries = [
    echo     ^('ccxt', 'Binance API'^),
    echo     ^('google.auth', 'Google Auth'^),
    echo     ^('google_auth_httplib2', 'Google Auth HTTP'^),
    echo     ^('google_auth_oauthlib', 'Google OAuth'^),
    echo     ^('googleapiclient', 'Google API Client'^),
    echo     ^('gspread', 'Google Sheets'^),
    echo     ^('oauth2client', 'OAuth2 Client'^),
    echo     ^('pandas', 'Pandas'^),
    echo     ^('numpy', 'NumPy'^),
    echo     ^('telegram', 'Telegram Bot'^),
    echo     ^('requests', 'Requests'^),
    echo     ^('pytz', 'PyTZ'^),
    echo     ^('dateutil', 'Python DateUtil'^),
    echo     ^('PyInstaller', 'PyInstaller - Build Tools'^),
    echo ]
    echo.
    echo passed = 0
    echo failed = 0
    echo.
    echo for module, name in libraries:
    echo     try:
    echo         __import__^(module^)
    echo         print^(f'   ✅ {name}'^)
    echo         passed += 1
    echo     except ImportError:
    echo         print^(f'   ❌ {name}'^)
    echo         failed += 1
    echo.
    echo print^(^)
    echo print^(f'Kết quả: {passed}/{len^(libraries^)} thư viện đã cài đặt'^)
    echo sys.exit^(failed^)
) > _check_libs.py

python _check_libs.py
set LIB_EXIT_CODE=%errorlevel%

del _check_libs.py

if %LIB_EXIT_CODE% equ 0 (
    echo ✅ PASS: Tất cả thư viện đã được cài đặt
    set /a TOTAL_CHECKS+=1
    set /a PASSED_CHECKS+=1
) else (
    echo ❌ FAIL: Một số thư viện chưa được cài đặt
    echo    💡 Chạy: pip install -r requirements.txt
    set /a TOTAL_CHECKS+=1
    set /a FAILED_CHECKS+=1
)
echo.

REM ============================================================================
REM 4. KIỂM TRA FILE SOURCE CODE
REM ============================================================================
echo [4] KIỂM TRA FILE SOURCE CODE
echo ═══════════════════════════════════════════════════════════════════════
echo Đang kiểm tra các file Python cần thiết...
echo.

set SOURCE_FILES=0
set MISSING_FILES=0

REM Critical files
call :check_file "hd_order.py" "Order Handler" "CRITICAL"
call :check_file "hd_order_123.py" "SL/TP Handler" "CRITICAL"

REM Important files
call :check_file "hd_update_all.py" "Market Data Updater"
call :check_file "hd_update_price.py" "Price Updater"
call :check_file "hd_update_cho_va_khop.py" "Status Updater"

REM Support files
call :check_file "gg_sheet_factory.py" "Google Sheets Factory"
call :check_file "telegram_factory.py" "Telegram Factory"
call :check_file "cascade_manager.py" "Cascade Manager"
call :check_file "binance_order_helper.py" "Binance Helper"

REM Alert & Cancel
call :check_file "hd_alert_possition_and_open_order.py" "Alert Handler"
call :check_file "hd_cancel_orders_schedule.py" "Cancel Scheduler"

REM Additional modules
call :check_file "hd_track_30_prices.py" "30 Prices Tracker"
call :check_file "hd_periodic_report.py" "Periodic Report"

echo.
set /a TOTAL_CHECKS+=1
if %MISSING_FILES% equ 0 (
    echo ✅ PASS: Tất cả %SOURCE_FILES% file source code đã sẵn sàng
    set /a PASSED_CHECKS+=1
) else (
    echo ❌ FAIL: %MISSING_FILES% file bị thiếu
    echo    💡 Đảm bảo copy đầy đủ source code
    set /a FAILED_CHECKS+=1
)
echo.

REM ============================================================================
REM 5. KIỂM TRA FILE CONFIG
REM ============================================================================
echo [5] KIỂM TRA FILE CẤU HÌNH
echo ═══════════════════════════════════════════════════════════════════════
set /a TOTAL_CHECKS+=1

if not exist config.ini (
    echo ❌ FAIL: config.ini không tồn tại
    echo    💡 Chạy: 1_setup_install.bat để tạo file mẫu
    set /a FAILED_CHECKS+=1
) else (
    echo ✅ PASS: config.ini tồn tại
    
    REM Check if config has been filled
    findstr /C:"YOUR_BINANCE_API_KEY" config.ini >nul 2>&1
    if errorlevel 1 (
        echo    ✅ Config đã được điền thông tin
    ) else (
        echo    ⚠️  WARNING: Config chưa được điền đầy đủ
        echo       💡 Cần điền: API keys, Telegram, Google Sheets ID
        set /a WARNING_CHECKS+=1
    )
    set /a PASSED_CHECKS+=1
)
echo.

REM ============================================================================
REM 6. KIỂM TRA GOOGLE CREDENTIALS
REM ============================================================================
echo [6] KIỂM TRA GOOGLE CREDENTIALS
echo ═══════════════════════════════════════════════════════════════════════
set /a TOTAL_CHECKS+=1

if not exist credentials.json (
    echo ⚠️  WARNING: credentials.json không tồn tại
    echo    💡 Tải từ Google Cloud Console và copy vào đây
    set /a WARNING_CHECKS+=1
) else (
    echo ✅ PASS: credentials.json tồn tại
    set /a PASSED_CHECKS+=1
)
echo.

REM ============================================================================
REM 7. KIỂM TRA FILE REQUIREMENTS.TXT
REM ============================================================================
echo [7] KIỂM TRA FILE REQUIREMENTS.TXT
echo ═══════════════════════════════════════════════════════════════════════
set /a TOTAL_CHECKS+=1

if not exist requirements.txt (
    echo ❌ FAIL: requirements.txt không tồn tại
    set /a FAILED_CHECKS+=1
) else (
    echo ✅ PASS: requirements.txt tồn tại
    set /a PASSED_CHECKS+=1
)
echo.

REM ============================================================================
REM 8. KIỂM TRA BUILD TOOLS (OPTIONAL)
REM ============================================================================
echo [8] KIỂM TRA BUILD TOOLS (Tùy chọn)
echo ═══════════════════════════════════════════════════════════════════════

python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ⚠️  INFO: PyInstaller chưa cài (chỉ cần khi build .exe)
) else (
    echo ✅ INFO: PyInstaller đã cài đặt (có thể build .exe)
)
echo.

REM ============================================================================
REM TÓM TẮT KẾT QUẢ
REM ============================================================================
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                        KẾT QUẢ KIỂM TRA                               ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo 📊 TỔNG QUAN:
echo.
echo    ✅ PASSED:   %PASSED_CHECKS%/%TOTAL_CHECKS% kiểm tra
if %WARNING_CHECKS% gtr 0 (
    echo    ⚠️  WARNING: %WARNING_CHECKS% cảnh báo
)
if %FAILED_CHECKS% gtr 0 (
    echo    ❌ FAILED:  %FAILED_CHECKS% lỗi
)
echo.
echo ═══════════════════════════════════════════════════════════════════════

if %FAILED_CHECKS% equ 0 (
    if %WARNING_CHECKS% equ 0 (
        echo.
        echo ✅ HOÀN HẢO! Môi trường đã sẵn sàng để chạy bot!
        echo.
        echo 📌 BƯỚC TIẾP THEO:
        echo    - Chạy file: 4_qbot_manager.bat
        echo    - Hoặc: start_all_bots.bat
        echo.
    ) else (
        echo.
        echo ⚠️  MÔI TRƯỜNG GẦN HOÀN CHỈNH (có một số cảnh báo)
        echo.
        echo 📌 NÊN KHẮC PHỤC:
        if not exist credentials.json (
            echo    - Thêm credentials.json
        )
        findstr /C:"YOUR_BINANCE_API_KEY" config.ini >nul 2>&1
        if not errorlevel 1 (
            echo    - Điền đầy đủ config.ini
        )
        echo.
        echo 💡 Bot có thể chạy được nhưng một số tính năng có thể bị lỗi
        echo.
    )
) else (
    echo.
    echo ❌ MÔI TRƯỜNG CHƯA SẴN SÀNG!
    echo.
    echo 📌 CẦN KHẮC PHỤC:
    echo.
    if %LIB_EXIT_CODE% neq 0 (
        echo    1. Cài đặt thư viện: pip install -r requirements.txt
    )
    if %MISSING_FILES% gtr 0 (
        echo    2. Bổ sung file source code bị thiếu
    )
    if not exist config.ini (
        echo    3. Tạo file config.ini: chạy 1_setup_install.bat
    )
    echo.
    echo 💡 Chạy lại file này sau khi khắc phục
    echo.
)

echo ═══════════════════════════════════════════════════════════════════════
echo.
pause
exit /b %FAILED_CHECKS%

REM ============================================================================
REM HELPER FUNCTION
REM ============================================================================
:check_file
if exist %~1 (
    echo    ✅ %~2 ^(%~1^)
    set /a SOURCE_FILES+=1
) else (
    if "%~3"=="CRITICAL" (
        echo    ❌ %~2 ^(%~1^) - CRITICAL
    ) else (
        echo    ⚠️  %~2 ^(%~1^)
    )
    set /a MISSING_FILES+=1
)
goto :eof

