@echo off
REM QBot v2.0 - Start All Bots Script (Windows)
REM Chạy tất cả 11 modules

echo ========================================
echo QBot v2.0 - Starting All Modules (Windows)
echo ========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found!
    echo Please install Python 3.9+
    pause
    exit /b 1
)

REM Check if in correct directory
if not exist config.ini (
    echo Error: config.ini not found!
    echo Are you in the source04062025 directory?
    pause
    exit /b 1
)

echo Starting modules...
echo.

REM Clear old error log
if exist error.log del error.log
echo Error log cleared. All errors will be logged to error.log
echo.

REM Module 1: Order Handler (Critical)
echo Starting hd_order.py...
start "QBot - Order Handler" cmd /c "python hd_order.py 2>> error.log"
timeout /t 2 >nul

REM Module 2: Order 123 Handler (Critical)
echo Starting hd_order_123.py...
start "QBot - SL/TP Handler" cmd /c "python hd_order_123.py 2>> error.log"
timeout /t 2 >nul

REM Module 3: Market Data Updater
echo Starting hd_update_all.py...
start "QBot - Market Data" cmd /c "python hd_update_all.py 2>> error.log"
timeout /t 2 >nul

REM Module 4: Price Updater
echo Starting hd_update_price.py...
start "QBot - Price Updater" cmd /c "python hd_update_price.py 2>> error.log"
timeout /t 2 >nul

REM Module 5: Status Updater
echo Starting hd_update_cho_va_khop.py...
start "QBot - Status Updater" cmd /c "python hd_update_cho_va_khop.py 2>> error.log"
timeout /t 2 >nul

REM Module 6: Alert Handler
echo Starting hd_alert_possition_and_open_order.py...
start "QBot - Alerts" cmd /c "python hd_alert_possition_and_open_order.py 2>> error.log"
timeout /t 2 >nul

REM Module 7: Cancel Scheduler
echo Starting hd_cancel_orders_schedule.py...
start "QBot - Cancel Scheduler" cmd /c "python hd_cancel_orders_schedule.py 2>> error.log"
timeout /t 2 >nul

REM Module 8: 30 Prices Tracker (NEW in v2.0)
echo Starting hd_track_30_prices.py...
start "QBot - 30 Prices Tracker" cmd /c "python hd_track_30_prices.py 2>> error.log"
timeout /t 2 >nul

REM Module 9: Periodic Report (NEW in v2.0)
echo Starting hd_periodic_report.py...
start "QBot - Periodic Report" cmd /c "python hd_periodic_report.py 2>> error.log"

echo.
echo ========================================
echo All 9 modules started!
echo ========================================
echo.
echo Check running processes in Task Manager
echo Look for "python.exe" processes
echo.
echo View error log:
echo   type error.log
echo.
echo To stop all: Close all CMD windows with "QBot" in title
echo Or use: taskkill /F /FI "WINDOWTITLE eq QBot*"
echo ========================================
pause

