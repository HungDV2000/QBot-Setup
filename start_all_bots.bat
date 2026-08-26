@echo off
REM ==============================================================================
REM QBot - Khoi dong bot (HO TRO DA TAI KHOAN)
REM   start_all_bots.bat            -> chay TAT CA tai khoan trong config
REM   start_all_bots.bat kh_a       -> chi chay tai khoan kh_a
REM ==============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

if "%QBOT_CONFIG%"=="" set QBOT_CONFIG=config.ini

echo ========================================
echo QBot - Khoi dong
echo ========================================

python --version >nul 2>&1
if errorlevel 1 ( echo Error: Khong tim thay Python! & pause & exit /b 1 )
if not exist "%QBOT_CONFIG%" ( echo Error: Khong tim thay %QBOT_CONFIG% & pause & exit /b 1 )

REM ── Chon bot dat lenh: trailing / limit / multi ──────────────────────────────
if "%ORDER_BOT_MODE%"=="" set ORDER_BOT_MODE=limit
if /i "%ORDER_BOT_MODE%"=="trailing" ( set ORDER_BOT_FILE=hd_order.py
) else if /i "%ORDER_BOT_MODE%"=="limit" ( set ORDER_BOT_FILE=hd_order_limit.py
) else if /i "%ORDER_BOT_MODE%"=="multi" ( set ORDER_BOT_FILE=hd_order_multi.py
) else ( echo Error: ORDER_BOT_MODE='%ORDER_BOT_MODE%' khong hop le & pause & exit /b 1 )

REM ── Danh sach tai khoan ─────────────────────────────────────────────────────
if not "%~1"=="" (
    set ACCOUNTS=%*
) else (
    for /f "delims=" %%A in ('python -c "import configparser,os;c=configparser.ConfigParser();c.read(os.environ.get('QBOT_CONFIG','config.ini'),encoding='utf-8');print(' '.join(a.strip() for a in c.get('global','accounts',fallback='').split(',') if a.strip()))"') do set ACCOUNTS=%%A
)

if "%ACCOUNTS%"=="" (
    echo Config khong khai 'accounts' -^> che do 1 tai khoan
    call :start_account ""
) else (
    echo Tai khoan se chay: %ACCOUNTS%
    for %%A in (%ACCOUNTS%) do call :start_account "%%A"
)

echo.
echo ========================================
echo Da khoi dong xong
echo ========================================
echo Xem log:  logs\^<tai_khoan^>\
echo Dung:     dong cac cua so CMD co chu "QBot"
echo ========================================
pause
exit /b 0

REM ── Ham khoi dong 1 tai khoan ───────────────────────────────────────────────
:start_account
set ACC=%~1
if "%ACC%"=="" (
    set QBOT_ACCOUNT=
    set LABEL=(1 tai khoan)
) else (
    set QBOT_ACCOUNT=%ACC%
    set LABEL=[%ACC%]
)
echo.
echo -------------------------------------
echo Khoi dong %LABEL%  (mode=%ORDER_BOT_MODE%)
echo -------------------------------------

start "QBot %LABEL% - Dat lenh" cmd /c "set QBOT_ACCOUNT=%ACC%&& python %ORDER_BOT_FILE%"
timeout /t 2 >nul

if /i "%ORDER_BOT_MODE%"=="multi" (
    echo   Bo qua hd_order_123.py ^(mode=multi da tu lo SL/TP^)
) else (
    start "QBot %LABEL% - SL/TP" cmd /c "set QBOT_ACCOUNT=%ACC%&& python hd_order_123.py"
    timeout /t 2 >nul
)

start "QBot %LABEL% - Market Data" cmd /c "set QBOT_ACCOUNT=%ACC%&& python hd_update_all.py"
timeout /t 2 >nul
start "QBot %LABEL% - Price" cmd /c "set QBOT_ACCOUNT=%ACC%&& python hd_update_price.py"
timeout /t 2 >nul
start "QBot %LABEL% - Cho va khop" cmd /c "set QBOT_ACCOUNT=%ACC%&& python hd_update_cho_va_khop.py"
timeout /t 2 >nul
start "QBot %LABEL% - Alerts" cmd /c "set QBOT_ACCOUNT=%ACC%&& python hd_alert_possition_and_open_order.py"
timeout /t 2 >nul
start "QBot %LABEL% - Cancel" cmd /c "set QBOT_ACCOUNT=%ACC%&& python hd_cancel_orders_schedule.py"
timeout /t 2 >nul
start "QBot %LABEL% - 30 Prices" cmd /c "set QBOT_ACCOUNT=%ACC%&& python hd_track_30_prices.py"
timeout /t 2 >nul
start "QBot %LABEL% - Report" cmd /c "set QBOT_ACCOUNT=%ACC%&& python hd_periodic_report.py"
timeout /t 2 >nul
exit /b 0
