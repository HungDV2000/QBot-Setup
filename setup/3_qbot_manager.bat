@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
REM ============================================================================
REM QBot v2.0 - Main Manager (Interactive Menu)
REM Quản lý tất cả chức năng của bot từ 1 cửa sổ duy nhất
REM ============================================================================

title QBot v2.0 - Manager

REM ============================================================================
REM KHỞI TẠO BIẾN
REM ============================================================================
set "CONFIG_FILE=config.ini"
set "STATUS_FILE=_bot_status.tmp"
set "RUNNING_PIDS=_running_pids.tmp"

REM Tạo file tracking nếu chưa có
if not exist "%STATUS_FILE%" (
    echo. > "%STATUS_FILE%"
)

REM ============================================================================
REM MAIN MENU LOOP
REM ============================================================================
:MAIN_MENU
cls
call :CHECK_ENVIRONMENT_QUICK

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                    QBot v2.0 - MANAGER CONSOLE                         ║
echo ║                    Quản Lý Bot Giao Dịch Tự Động                       ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM Hiển thị trạng thái hệ thống
echo ┌────────────────────────────────────────────────────────────────────────┐
echo │ 📊 TRẠNG THÁI HỆ THỐNG                                                 │
echo ├────────────────────────────────────────────────────────────────────────┤
echo │                                                                        │
echo │  Python:           !ENV_PYTHON!
echo │  Libraries:        !ENV_LIBS!
echo │  Config File:      !ENV_CONFIG!
echo │  Source Files:     !ENV_FILES!
echo │                                                                        │
echo │  Bot Status:       !BOT_STATUS!
echo │                                                                        │
echo └────────────────────────────────────────────────────────────────────────┘
echo.

REM Menu chính
echo ┌────────────────────────────────────────────────────────────────────────┐
echo │ 🎛️  MENU CHÍNH                                                          │
echo ├────────────────────────────────────────────────────────────────────────┤
echo │                                                                        │
echo │  [1] 🔍 Kiểm Tra Môi Trường Đầy Đủ                                     │
echo │  [2] 📊 Xem Trạng Thái Bot Chi Tiết                                    │
echo │                                                                        │
echo │  [3] 🚀 Khởi Động Tất Cả Modules                                       │
echo │  [4] 📋 Chọn Module Để Chạy                                            │
echo │  [5] 🔄 Refresh/Restart Module                                         │
echo │                                                                        │
echo │  [6] 🛑 Dừng Tất Cả Modules                                            │
echo │  [7] 🛑 Dừng Module Cụ Thể                                             │
echo │                                                                        │
echo │  [8] 📝 Mở File Config                                                 │
echo │  [9] 📂 Mở Thư Mục Log                                                 │
echo │                                                                        │
echo │  [0] ❌ Thoát                                                           │
echo │                                                                        │
echo └────────────────────────────────────────────────────────────────────────┘
echo.

set /p CHOICE="👉 Chọn chức năng [0-9]: "

if "%CHOICE%"=="1" goto :CHECK_ENV
if "%CHOICE%"=="2" goto :CHECK_STATUS
if "%CHOICE%"=="3" goto :START_ALL
if "%CHOICE%"=="4" goto :START_SELECT
if "%CHOICE%"=="5" goto :REFRESH_MODULE
if "%CHOICE%"=="6" goto :STOP_ALL
if "%CHOICE%"=="7" goto :STOP_SELECT
if "%CHOICE%"=="8" goto :OPEN_CONFIG
if "%CHOICE%"=="9" goto :OPEN_LOGS
if "%CHOICE%"=="0" goto :EXIT

echo.
echo ⚠️  Lựa chọn không hợp lệ!
timeout /t 2 >nul
goto :MAIN_MENU

REM ============================================================================
REM [1] KIỂM TRA MÔI TRƯỜNG ĐẦY ĐỦ
REM ============================================================================
:CHECK_ENV
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                    [1] KIỂM TRA MÔI TRƯỜNG                             ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

if not exist "2_check_environment.bat" (
    echo ⚠️  File 2_check_environment.bat không tồn tại!
    echo.
    pause
    goto :MAIN_MENU
)

echo 🔍 Đang chạy kiểm tra đầy đủ...
echo.
call "2_check_environment.bat"

goto :MAIN_MENU

REM ============================================================================
REM [2] XEM TRẠNG THÁI BOT CHI TIẾT
REM ============================================================================
:CHECK_STATUS
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                    [2] TRẠNG THÁI BOT CHI TIẾT                         ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

if exist check_status.py (
    echo 🔍 Đang kiểm tra trạng thái các module...
    echo.
    python check_status.py
) else (
    echo 🔍 Đang kiểm tra các process đang chạy...
    echo.
    call :SHOW_DETAILED_STATUS
)

echo.
pause
goto :MAIN_MENU

REM ============================================================================
REM [3] KHỞI ĐỘNG TẤT CẢ MODULES
REM ============================================================================
:START_ALL
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                    [3] KHỞI ĐỘNG TẤT CẢ MODULES                        ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM Kiểm tra môi trường trước
if "!ENV_STATUS!"=="NOT_READY" (
    echo ❌ MÔI TRƯỜNG CHƯA SẴN SÀNG!
    echo.
    echo 💡 Vui lòng chạy [1] Kiểm tra môi trường để xem chi tiết.
    echo.
    pause
    goto :MAIN_MENU
)

echo 🚀 Đang khởi động tất cả modules...
echo.

REM Clear error log
if exist error.log del error.log

REM Module 1: Order Handler (CRITICAL)
call :START_MODULE "hd_order.py" "QBot - Order Handler"

REM Module 2: SL/TP Handler (CRITICAL)
call :START_MODULE "hd_order_123.py" "QBot - SL/TP Handler"

REM Module 3: Market Data Updater
call :START_MODULE "hd_update_all.py" "QBot - Market Data"

REM Module 4: Price Updater
call :START_MODULE "hd_update_price.py" "QBot - Price Updater"

REM Module 5: Status Updater
call :START_MODULE "hd_update_cho_va_khop.py" "QBot - Status Updater"

REM Module 6: Alert Handler
call :START_MODULE "hd_alert_possition_and_open_order.py" "QBot - Alerts"

REM Module 7: Cancel Scheduler
call :START_MODULE "hd_cancel_orders_schedule.py" "QBot - Cancel Scheduler"

REM Module 8: 30 Prices Tracker
if exist "hd_track_30_prices.py" (
    call :START_MODULE "hd_track_30_prices.py" "QBot - 30 Prices Tracker"
)

REM Module 9: Periodic Report
if exist "hd_periodic_report.py" (
    call :START_MODULE "hd_periodic_report.py" "QBot - Periodic Report"
)

echo.
echo ═══════════════════════════════════════════════════════════════════════
echo ✅ Đã khởi động tất cả modules!
echo ═══════════════════════════════════════════════════════════════════════
echo.
echo 💡 TIP: Các module đang chạy trong các cửa sổ CMD riêng biệt
echo    Không đóng các cửa sổ đó!
echo.
pause
goto :MAIN_MENU

REM ============================================================================
REM [4] CHỌN MODULE ĐỂ CHẠY
REM ============================================================================
:START_SELECT
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                    [4] CHỌN MODULE ĐỂ CHẠY                             ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

echo Chọn module cần khởi động:
echo.
echo  [1] hd_order.py                      (Order Handler - CRITICAL)
echo  [2] hd_order_123.py                  (SL/TP Handler - CRITICAL)
echo  [3] hd_update_all.py                 (Market Data Updater)
echo  [4] hd_update_price.py               (Price Updater)
echo  [5] hd_update_cho_va_khop.py         (Status Updater)
echo  [6] hd_alert_possition_and_open_order.py (Alert Handler)
echo  [7] hd_cancel_orders_schedule.py     (Cancel Scheduler)
echo  [8] hd_track_30_prices.py            (30 Prices Tracker)
echo  [9] hd_periodic_report.py            (Periodic Report)
echo.
echo  [0] Quay lại menu chính
echo.

set /p MODULE_CHOICE="👉 Chọn module [0-9]: "

if "%MODULE_CHOICE%"=="0" goto :MAIN_MENU
if "%MODULE_CHOICE%"=="1" call :START_MODULE_WITH_CHECK "hd_order.py" "QBot - Order Handler"
if "%MODULE_CHOICE%"=="2" call :START_MODULE_WITH_CHECK "hd_order_123.py" "QBot - SL/TP Handler"
if "%MODULE_CHOICE%"=="3" call :START_MODULE_WITH_CHECK "hd_update_all.py" "QBot - Market Data"
if "%MODULE_CHOICE%"=="4" call :START_MODULE_WITH_CHECK "hd_update_price.py" "QBot - Price Updater"
if "%MODULE_CHOICE%"=="5" call :START_MODULE_WITH_CHECK "hd_update_cho_va_khop.py" "QBot - Status Updater"
if "%MODULE_CHOICE%"=="6" call :START_MODULE_WITH_CHECK "hd_alert_possition_and_open_order.py" "QBot - Alerts"
if "%MODULE_CHOICE%"=="7" call :START_MODULE_WITH_CHECK "hd_cancel_orders_schedule.py" "QBot - Cancel Scheduler"
if "%MODULE_CHOICE%"=="8" call :START_MODULE_WITH_CHECK "hd_track_30_prices.py" "QBot - 30 Prices Tracker"
if "%MODULE_CHOICE%"=="9" call :START_MODULE_WITH_CHECK "hd_periodic_report.py" "QBot - Periodic Report"

goto :MAIN_MENU

REM ============================================================================
REM [5] REFRESH/RESTART MODULE
REM ============================================================================
:REFRESH_MODULE
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                    [5] REFRESH/RESTART MODULE                          ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

echo Chọn module cần refresh:
echo.
echo  [1] hd_order.py
echo  [2] hd_order_123.py
echo  [3] hd_update_all.py
echo  [4] hd_update_price.py
echo  [5] hd_update_cho_va_khop.py
echo  [6] hd_alert_possition_and_open_order.py
echo  [7] hd_cancel_orders_schedule.py
echo  [8] hd_track_30_prices.py
echo  [9] hd_periodic_report.py
echo.
echo  [0] Quay lại menu chính
echo.

set /p REFRESH_CHOICE="👉 Chọn module [0-9]: "

if "%REFRESH_CHOICE%"=="0" goto :MAIN_MENU

set MODULE_FILE=
if "%REFRESH_CHOICE%"=="1" set "MODULE_FILE=hd_order.py" & set "MODULE_TITLE=QBot - Order Handler"
if "%REFRESH_CHOICE%"=="2" set "MODULE_FILE=hd_order_123.py" & set "MODULE_TITLE=QBot - SL/TP Handler"
if "%REFRESH_CHOICE%"=="3" set "MODULE_FILE=hd_update_all.py" & set "MODULE_TITLE=QBot - Market Data"
if "%REFRESH_CHOICE%"=="4" set "MODULE_FILE=hd_update_price.py" & set "MODULE_TITLE=QBot - Price Updater"
if "%REFRESH_CHOICE%"=="5" set "MODULE_FILE=hd_update_cho_va_khop.py" & set "MODULE_TITLE=QBot - Status Updater"
if "%REFRESH_CHOICE%"=="6" set "MODULE_FILE=hd_alert_possition_and_open_order.py" & set "MODULE_TITLE=QBot - Alerts"
if "%REFRESH_CHOICE%"=="7" set "MODULE_FILE=hd_cancel_orders_schedule.py" & set "MODULE_TITLE=QBot - Cancel Scheduler"
if "%REFRESH_CHOICE%"=="8" set "MODULE_FILE=hd_track_30_prices.py" & set "MODULE_TITLE=QBot - 30 Prices Tracker"
if "%REFRESH_CHOICE%"=="9" set "MODULE_FILE=hd_periodic_report.py" & set "MODULE_TITLE=QBot - Periodic Report"

if "%MODULE_FILE%"=="" (
    echo ⚠️  Lựa chọn không hợp lệ!
    timeout /t 2 >nul
    goto :REFRESH_MODULE
)

echo.
echo 🔍 Đang kiểm tra !MODULE_FILE!...

REM Check if running
tasklist /FI "IMAGENAME eq python.exe" /V 2>nul | findstr /C:"!MODULE_FILE!" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️  Module này chưa chạy!
    echo.
    set /p START_IT="   Bạn có muốn khởi động module này không? (Y/N): "
    if /i "!START_IT!"=="Y" (
        call :START_MODULE "!MODULE_FILE!" "!MODULE_TITLE!"
        echo ✅ Đã khởi động !MODULE_FILE!
    )
) else (
    echo.
    echo ⚠️  Module này đang chạy!
    echo.
    echo Lựa chọn:
    echo  [1] Dừng và khởi động lại (Restart)
    echo  [2] Chỉ dừng
    echo  [0] Không làm gì
    echo.
    set /p REFRESH_ACTION="👉 Chọn hành động: "
    
    if "!REFRESH_ACTION!"=="1" (
        echo.
        echo 🛑 Đang dừng !MODULE_FILE!...
        call :STOP_MODULE_BY_NAME "!MODULE_FILE!"
        timeout /t 2 >nul
        echo 🚀 Đang khởi động lại...
        call :START_MODULE "!MODULE_FILE!" "!MODULE_TITLE!"
        echo ✅ Đã restart !MODULE_FILE!
    ) else if "!REFRESH_ACTION!"=="2" (
        echo.
        echo 🛑 Đang dừng !MODULE_FILE!...
        call :STOP_MODULE_BY_NAME "!MODULE_FILE!"
        echo ✅ Đã dừng !MODULE_FILE!
    )
)

echo.
pause
goto :MAIN_MENU

REM ============================================================================
REM [6] DỪNG TẤT CẢ MODULES
REM ============================================================================
:STOP_ALL
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                    [6] DỪNG TẤT CẢ MODULES                             ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

echo ⚠️  CẢNH BÁO: Bạn sắp dừng TẤT CẢ modules của bot!
echo.
set /p CONFIRM_STOP="   Bạn có chắc chắn không? (YES để xác nhận): "

if /i not "%CONFIRM_STOP%"=="YES" (
    echo.
    echo ❌ Đã hủy!
    timeout /t 2 >nul
    goto :MAIN_MENU
)

echo.
echo 🛑 Đang dừng tất cả modules...
echo.

REM Stop by closing all QBot windows
taskkill /FI "WINDOWTITLE eq QBot*" /F >nul 2>&1

echo ✅ Đã dừng tất cả modules!
echo.
pause
goto :MAIN_MENU

REM ============================================================================
REM [7] DỪNG MODULE CỤ THỂ
REM ============================================================================
:STOP_SELECT
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                    [7] DỪNG MODULE CỤ THỂ                              ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

echo Chọn module cần dừng:
echo.
echo  [1] hd_order.py
echo  [2] hd_order_123.py
echo  [3] hd_update_all.py
echo  [4] hd_update_price.py
echo  [5] hd_update_cho_va_khop.py
echo  [6] hd_alert_possition_and_open_order.py
echo  [7] hd_cancel_orders_schedule.py
echo  [8] hd_track_30_prices.py
echo  [9] hd_periodic_report.py
echo.
echo  [0] Quay lại menu chính
echo.

set /p STOP_CHOICE="👉 Chọn module [0-9]: "

if "%STOP_CHOICE%"=="0" goto :MAIN_MENU

set STOP_MODULE=
if "%STOP_CHOICE%"=="1" set "STOP_MODULE=hd_order.py"
if "%STOP_CHOICE%"=="2" set "STOP_MODULE=hd_order_123.py"
if "%STOP_CHOICE%"=="3" set "STOP_MODULE=hd_update_all.py"
if "%STOP_CHOICE%"=="4" set "STOP_MODULE=hd_update_price.py"
if "%STOP_CHOICE%"=="5" set "STOP_MODULE=hd_update_cho_va_khop.py"
if "%STOP_CHOICE%"=="6" set "STOP_MODULE=hd_alert_possition_and_open_order.py"
if "%STOP_CHOICE%"=="7" set "STOP_MODULE=hd_cancel_orders_schedule.py"
if "%STOP_CHOICE%"=="8" set "STOP_MODULE=hd_track_30_prices.py"
if "%STOP_CHOICE%"=="9" set "STOP_MODULE=hd_periodic_report.py"

if "%STOP_MODULE%"=="" (
    echo ⚠️  Lựa chọn không hợp lệ!
    timeout /t 2 >nul
    goto :STOP_SELECT
)

echo.
echo 🛑 Đang dừng !STOP_MODULE!...
call :STOP_MODULE_BY_NAME "!STOP_MODULE!"
echo ✅ Đã dừng !STOP_MODULE!
echo.
pause
goto :MAIN_MENU

REM ============================================================================
REM [8] MỞ FILE CONFIG
REM ============================================================================
:OPEN_CONFIG
if exist config.ini (
    notepad config.ini
) else (
    echo ⚠️  File config.ini không tồn tại!
    pause
)
goto :MAIN_MENU

REM ============================================================================
REM [9] MỞ THƯ MỤC LOG
REM ============================================================================
:OPEN_LOGS
if exist logs (
    explorer logs
) else (
    explorer .
)
goto :MAIN_MENU

REM ============================================================================
REM [0] EXIT
REM ============================================================================
:EXIT
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                         THOÁT QBOT MANAGER                             ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo 👋 Cảm ơn bạn đã sử dụng QBot v2.0!
echo.
echo 💡 Lưu ý: Các module vẫn đang chạy trong background
echo    Sử dụng [6] Dừng tất cả modules nếu muốn tắt bot
echo.

REM Cleanup temp files
if exist "%STATUS_FILE%" del "%STATUS_FILE%"
if exist "%RUNNING_PIDS%" del "%RUNNING_PIDS%"

timeout /t 3 >nul
exit /b 0

REM ============================================================================
REM HELPER FUNCTIONS
REM ============================================================================

:CHECK_ENVIRONMENT_QUICK
REM Quick environment check for status display
set "ENV_PYTHON=❌ Not Installed"
set "ENV_LIBS=❌ Not Ready"
set "ENV_CONFIG=❌ Missing"
set "ENV_FILES=❌ Incomplete"
set "BOT_STATUS=⚪ Unknown"
set "ENV_STATUS=NOT_READY"

REM Check Python
python --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "ENV_PYTHON=✅ %%i"
)

REM Check Libraries (quick check - just ccxt)
python -c "import ccxt" 2>nul
if not errorlevel 1 (
    set "ENV_LIBS=✅ Installed"
)

REM Check Config
if exist config.ini (
    findstr /C:"YOUR_BINANCE_API_KEY" config.ini >nul 2>&1
    if errorlevel 1 (
        set "ENV_CONFIG=✅ Configured"
    ) else (
        set "ENV_CONFIG=⚠️  Not Filled"
    )
)

REM Check Files (just check critical ones)
if exist hd_order.py (
    if exist hd_order_123.py (
        set "ENV_FILES=✅ Complete"
    )
)

REM Check Bot Status
tasklist /FI "IMAGENAME eq python.exe" 2>nul | findstr "python.exe" >nul 2>&1
if not errorlevel 1 (
    set "BOT_STATUS=🟢 Running"
) else (
    set "BOT_STATUS=🔴 Stopped"
)

REM Overall status
if "!ENV_PYTHON!"=="✅*" if "!ENV_LIBS!"=="✅*" if "!ENV_FILES!"=="✅*" (
    set "ENV_STATUS=READY"
)

goto :eof

:START_MODULE
REM Start a module in a new window
if not exist "%~1" (
    echo    ⚠️  File không tồn tại: %~1
    goto :eof
)
echo    🚀 Starting: %~1
start "%~2" cmd /c "python %~1 2>> error.log"
timeout /t 1 >nul
goto :eof

:START_MODULE_WITH_CHECK
REM Start module but check if already running
tasklist /FI "IMAGENAME eq python.exe" /V 2>nul | findstr /C:"%~1" >nul 2>&1
if not errorlevel 1 (
    echo.
    echo ⚠️  Module này đã đang chạy!
    echo.
    set /p RESTART="   Bạn có muốn restart không? (Y/N): "
    if /i "!RESTART!"=="Y" (
        call :STOP_MODULE_BY_NAME "%~1"
        timeout /t 2 >nul
        call :START_MODULE "%~1" "%~2"
        echo ✅ Đã restart %~1
    )
) else (
    call :START_MODULE "%~1" "%~2"
    echo ✅ Đã khởi động %~1
)
echo.
pause
goto :eof

:STOP_MODULE_BY_NAME
REM Stop a specific module by searching for its filename in command line
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /V /FO CSV ^| findstr /C:"%~1"') do (
    taskkill /PID %%i /F >nul 2>&1
)
goto :eof

:SHOW_DETAILED_STATUS
REM Show detailed status of all modules
echo ┌────────────────────────────────────────────────────────────────────────┐
echo │ MODULE                                          STATUS      PRIORITY   │
echo ├────────────────────────────────────────────────────────────────────────┤

call :CHECK_MODULE_STATUS "hd_order.py" "CRITICAL"
call :CHECK_MODULE_STATUS "hd_order_123.py" "CRITICAL"
call :CHECK_MODULE_STATUS "hd_update_all.py" "IMPORTANT"
call :CHECK_MODULE_STATUS "hd_update_price.py" "IMPORTANT"
call :CHECK_MODULE_STATUS "hd_update_cho_va_khop.py" "IMPORTANT"
call :CHECK_MODULE_STATUS "hd_alert_possition_and_open_order.py" "NORMAL"
call :CHECK_MODULE_STATUS "hd_cancel_orders_schedule.py" "NORMAL"
call :CHECK_MODULE_STATUS "hd_track_30_prices.py" "NORMAL"
call :CHECK_MODULE_STATUS "hd_periodic_report.py" "NORMAL"

echo └────────────────────────────────────────────────────────────────────────┘
goto :eof

:CHECK_MODULE_STATUS
set "MODULE_NAME=%~1                                                  "
set "MODULE_NAME=!MODULE_NAME:~0,45!"

tasklist /FI "IMAGENAME eq python.exe" /V 2>nul | findstr /C:"%~1" >nul 2>&1
if errorlevel 1 (
    echo │ !MODULE_NAME! ❌ STOPPED   %~2     │
) else (
    echo │ !MODULE_NAME! ✅ RUNNING   %~2     │
)
goto :eof

