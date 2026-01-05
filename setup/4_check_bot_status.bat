@echo off
chcp 65001 >nul
REM ============================================================================
REM QBot v2.0 - Bot Status Checker
REM Kiểm tra trạng thái các module đang chạy
REM ============================================================================

title QBot - Kiểm Tra Trạng Thái Bot

cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║              QBot v2.0 - Kiểm Tra Trạng Thái Bot                       ║
echo ║              Bot Status Checker                                        ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM ============================================================================
REM KIỂM TRA PYTHON
REM ============================================================================
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ LỖI: Python không được cài đặt!
    echo.
    pause
    exit /b 1
)

REM ============================================================================
REM SỬ DỤNG check_status.py
REM ============================================================================
if not exist check_status.py (
    echo ⚠️  File check_status.py không tồn tại!
    echo Đang sử dụng kiểm tra đơn giản...
    echo.
    goto :simple_check
)

echo 🔍 Đang kiểm tra trạng thái các module...
echo.

python check_status.py
set STATUS_CODE=%errorlevel%

echo.
echo ═══════════════════════════════════════════════════════════════════════

if %STATUS_CODE% equ 0 (
    echo.
    echo ✅ TẤT CẢ MODULE ĐANG HOẠT ĐỘNG BÌNH THƯỜNG!
    echo.
) else if %STATUS_CODE% equ 1 (
    echo.
    echo ⚠️  MỘT SỐ MODULE BỊ DỪNG ^(Nhưng module CRITICAL vẫn OK^)
    echo.
) else (
    echo.
    echo ❌ CÓ MODULE CRITICAL BỊ DỪNG! Bot có thể không hoạt động!
    echo.
    echo 💡 Cần khởi động lại bot
    echo.
)

echo ═══════════════════════════════════════════════════════════════════════
echo.
pause
exit /b %STATUS_CODE%

REM ============================================================================
REM SIMPLE CHECK (Fallback nếu không có check_status.py)
REM ============================================================================
:simple_check

set RUNNING_COUNT=0
set TOTAL_COUNT=7

echo Đang kiểm tra các process Python...
echo.

REM Check for each module
call :check_process "hd_order.py" "Order Handler (CRITICAL)"
call :check_process "hd_order_123.py" "SL/TP Handler (CRITICAL)"
call :check_process "hd_update_all.py" "Market Data Updater"
call :check_process "hd_update_price.py" "Price Updater"
call :check_process "hd_update_cho_va_khop.py" "Status Updater"
call :check_process "hd_alert_possition_and_open_order.py" "Alert Handler"
call :check_process "hd_cancel_orders_schedule.py" "Cancel Scheduler"

echo.
echo ═══════════════════════════════════════════════════════════════════════
echo 📊 KẾT QUẢ: %RUNNING_COUNT%/%TOTAL_COUNT% modules đang chạy
echo ═══════════════════════════════════════════════════════════════════════
echo.

if %RUNNING_COUNT% equ %TOTAL_COUNT% (
    echo ✅ Tất cả modules đang hoạt động!
) else (
    echo ⚠️  Một số modules không chạy!
)

echo.
pause
exit /b 0

REM ============================================================================
REM HELPER FUNCTION
REM ============================================================================
:check_process
tasklist /FI "IMAGENAME eq python.exe" /V 2>nul | findstr /C:"%~1" >nul 2>&1
if errorlevel 1 (
    echo    ❌ STOPPED - %~2
) else (
    echo    ✅ RUNNING - %~2
    set /a RUNNING_COUNT+=1
)
goto :eof

