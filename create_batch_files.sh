#!/bin/bash
# Script tạo các file batch cho Windows

cd "$(dirname "$0")"

mkdir -p dist_windows

# Tạo start_all_bots.bat
cat > dist_windows/start_all_bots.bat << 'EOF'
@echo off
chcp 65001 >nul
echo ========================================
echo   QBot - Khoi Dong Tat Ca Modules
echo ========================================
echo.

if not exist config.ini (
    echo Loi: Khong tim thay config.ini!
    echo Vui long copy config.ini.example thanh config.ini
    pause
    exit /b 1
)

echo Dang khoi dong cac modules...
echo.

if exist hd_order.exe (
    echo [1/9] Khoi dong hd_order.exe...
    start "QBot - Order Handler" hd_order.exe
    timeout /t 2 >nul
)

if exist hd_order_123.exe (
    echo [2/9] Khoi dong hd_order_123.exe...
    start "QBot - SL/TP Handler" hd_order_123.exe
    timeout /t 2 >nul
)

if exist hd_update_all.exe (
    echo [3/9] Khoi dong hd_update_all.exe...
    start "QBot - Market Data" hd_update_all.exe
    timeout /t 2 >nul
)

if exist hd_update_price.exe (
    echo [4/9] Khoi dong hd_update_price.exe...
    start "QBot - Price Update" hd_update_price.exe
    timeout /t 2 >nul
)

if exist hd_update_cho_va_khop.exe (
    echo [5/9] Khoi dong hd_update_cho_va_khop.exe...
    start "QBot - Status Update" hd_update_cho_va_khop.exe
    timeout /t 2 >nul
)

if exist hd_update_danhmuc.exe (
    echo [6/9] Khoi dong hd_update_danhmuc.exe...
    start "QBot - Category Update" hd_update_danhmuc.exe
    timeout /t 2 >nul
)

if exist hd_alert_possition_and_open_order.exe (
    echo [7/9] Khoi dong hd_alert_possition_and_open_order.exe...
    start "QBot - Alerts" hd_alert_possition_and_open_order.exe
    timeout /t 2 >nul
)

if exist hd_cancel_orders_schedule.exe (
    echo [8/9] Khoi dong hd_cancel_orders_schedule.exe...
    start "QBot - Cancel Scheduler" hd_cancel_orders_schedule.exe
    timeout /t 2 >nul
)

if exist hd_isolated_crossed_converter.exe (
    echo [9/9] Khoi dong hd_isolated_crossed_converter.exe...
    start "QBot - Margin Converter" hd_isolated_crossed_converter.exe
    timeout /t 1 >nul
)

echo.
echo ========================================
echo   Da khoi dong tat ca modules!
echo ========================================
echo.
echo De dung: Chay stop_all_bots.bat
echo.
pause
EOF

# Tạo stop_all_bots.bat
cat > dist_windows/stop_all_bots.bat << 'EOF'
@echo off
chcp 65001 >nul
echo ========================================
echo   QBot - Dung Tat Ca Modules
echo ========================================
echo.

taskkill /F /IM hd_order.exe 2>nul
taskkill /F /IM hd_order_123.exe 2>nul
taskkill /F /IM hd_update_all.exe 2>nul
taskkill /F /IM hd_update_price.exe 2>nul
taskkill /F /IM hd_update_cho_va_khop.exe 2>nul
taskkill /F /IM hd_update_danhmuc.exe 2>nul
taskkill /F /IM hd_alert_possition_and_open_order.exe 2>nul
taskkill /F /IM hd_cancel_orders_schedule.exe 2>nul
taskkill /F /IM hd_isolated_crossed_converter.exe 2>nul
taskkill /F /IM check_status.exe 2>nul

echo.
echo ========================================
echo   Da dung tat ca modules!
echo ========================================
echo.
pause
EOF

echo "✅ Đã tạo các file batch trong dist_windows/"
ls -la dist_windows/*.bat
