#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QBot - Windows Build Script (Rebuild Version)
Build tất cả modules thành .exe files sử dụng PyInstaller
Chạy trên macOS/Linux để build cho Windows
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# ========================================
# FORCE UNBUFFERED OUTPUT (Real-time logs)
# ========================================
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ========================================
# CẤU HÌNH BUILD
# ========================================

# Danh sách các module cần build
MODULES = [
    # Core Trading Modules
    "hd_order.py",                              # Entry orders với system commands
    "hd_order_123.py",                          # Auto SL/TP với cascade logic
    "hd_alert_possition_and_open_order.py",    # Monitor positions
    "hd_cancel_orders_schedule.py",            # Cancel scheduler
    
    # Data Collection Modules (NEW in v2.0)
    "hd_update_all.py",                         # Market data 47+ columns
    "hd_update_price.py",                       # Price updates
    "hd_update_cho_va_khop.py",                # Status updates
    "hd_update_danhmuc.py",                     # Category updates
    "hd_track_30_prices.py",                    # NEW: 30 price tracking
    
    # Reporting & Monitoring (NEW in v2.0)
    "hd_periodic_report.py",                    # NEW: Periodic balance reports
    
    # Utilities
    "hd_isolated_crossed_converter.py",        # Margin mode converter
    "check_status.py",                          # Status checker
]

# Hidden imports - các module Python cần include
HIDDEN_IMPORTS = [
    # Local modules (Core)
    'cst',
    'utils',
    'gg_sheet_factory',
    'telegram_factory',
    'binance_utils',
    'binance_order',
    
    # NEW Helper Modules (v2.0)
    'binance_order_helper',      # Algo Order API handler
    'cascade_manager',            # Multi-layer cascade logic
    'order_state_tracker',        # State tracking to sheets
    'notification_manager',       # 8 Telegram notifications
    'data_collector',             # Market data collection
    'error_handler',              # Centralized error handling
    
    # Google API
    'google.auth.transport.requests',
    'google.oauth2.credentials',
    'google_auth_oauthlib.flow',
    'googleapiclient.discovery',
    'googleapiclient.errors',
    
    # Trading & Telegram
    'telegram',
    'telegram.ext',
    'ccxt',
    'ccxt.base.errors',
    
    # Data processing
    'pandas',
    'numpy',
    'asyncio',
    'aiohttp',
    'requests',
    'datetime',
    'json',
    'time',
    'logging',
]

# Files cần copy vào distribution
CONFIG_FILES = [
    'config.ini.example',
    'start_all_bots.bat',
    'stop_all_bots.bat',
    'QUICK_START.md',  # Hướng dẫn nhanh tổng hợp (CẤU TRÚC + LOGIC + SETUP)
]

# Note: credentials.json không copy vì user cần tạo riêng

# ========================================
# HELPER FUNCTIONS
# ========================================

def print_header(text):
    """In header đẹp"""
    print("\n" + "=" * 70, flush=True)
    print(f"  {text}", flush=True)
    print("=" * 70, flush=True)

def print_step(text):
    """In bước đang thực hiện"""
    print(f"\n🔹 {text}", flush=True)

def print_success(text):
    """In thông báo thành công"""
    print(f"✅ {text}", flush=True)

def print_error(text):
    """In thông báo lỗi"""
    print(f"❌ {text}", flush=True)

def print_warning(text):
    """In cảnh báo"""
    print(f"⚠️  {text}", flush=True)

def check_requirements():
    """Kiểm tra yêu cầu hệ thống"""
    print_step("Kiểm tra yêu cầu hệ thống...")
    
    # Check Python version
    py_version = sys.version_info
    print(f"Python version: {py_version.major}.{py_version.minor}.{py_version.micro}", flush=True)
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 9):
        print_error("Cần Python 3.9 trở lên!")
        return False
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}", flush=True)
        print_success("PyInstaller đã cài đặt")
    except ImportError:
        print_error("PyInstaller chưa được cài đặt!")
        print("\nCài đặt PyInstaller:", flush=True)
        print("  python3 -m pip install pyinstaller", flush=True)
        print("\nHoặc chạy:", flush=True)
        print("  ./install_dependencies.sh", flush=True)
        return False
    
    # Check modules exist
    print_step("Kiểm tra các module...")
    missing_modules = []
    for module in MODULES:
        if not Path(module).exists():
            missing_modules.append(module)
            print_warning(f"Module không tồn tại: {module}")
        else:
            print(f"  ✓ {module}", flush=True)
    
    if missing_modules:
        print_warning(f"Thiếu {len(missing_modules)} modules, sẽ bỏ qua chúng")
    
    print_success("Kiểm tra yêu cầu hoàn tất")
    return True

def clean_previous_builds():
    """Xóa các file build trước đó"""
    print_step("Dọn dẹp các file build cũ...")
    
    dirs_to_remove = ['build', 'dist', '__pycache__', 'dist_windows']
    for dir_name in dirs_to_remove:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"  Đã xóa: {dir_name}/", flush=True)
    
    # Remove .spec files
    for spec_file in Path(".").glob("*.spec"):
        spec_file.unlink()
        print(f"  Đã xóa: {spec_file.name}", flush=True)
    
    print_success("Dọn dẹp hoàn tất")

def build_single_module(module_name):
    """Build một module thành .exe"""
    print_header(f"BUILD: {module_name}")
    
    # Kiểm tra file tồn tại
    if not Path(module_name).exists():
        print_error(f"File không tồn tại: {module_name}")
        return False
    
    # Tạo command PyInstaller
    exe_name = module_name.replace('.py', '')
    
    cmd = [
        sys.executable,  # python3 executable
        '-m', 'PyInstaller',
        '--onefile',       # Tạo 1 file .exe duy nhất
        '--console',       # Console app (để xem logs)
        '--name', exe_name,
        '--clean',         # Clean cache
    ]
    
    # Add hidden imports
    for hidden_import in HIDDEN_IMPORTS:
        cmd.extend(['--hidden-import', hidden_import])
    
    # Add config file nếu tồn tại
    if Path('config.ini.example').exists():
        if sys.platform == 'win32':
            cmd.extend(['--add-data', 'config.ini.example;.'])
        else:
            cmd.extend(['--add-data', 'config.ini.example:.'])
    
    # Add module
    cmd.append(module_name)
    
    # Print command
    print(f"\nCommand: {' '.join(cmd)}\n", flush=True)
    
    # Run PyInstaller với UNBUFFERED OUTPUT
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        # Print output REAL-TIME
        for line in process.stdout:
            line = line.rstrip()
            if "ERROR" in line or "Error" in line:
                print(f"  ⚠️  {line}", flush=True)
            elif "WARNING" in line or "Warning" in line:
                print(f"  ⚠️  {line}", flush=True)
            elif "Successfully" in line or "completed" in line:
                print(f"  ✓ {line}", flush=True)
            elif line.strip():
                print(f"  {line}", flush=True)
        
        # Wait for completion
        return_code = process.wait()
        
        # Check result
        if return_code == 0:
            exe_path = Path('dist') / exe_name
            if exe_path.exists() or Path(f'dist/{exe_name}.exe').exists():
                print_success(f"Build thành công: {module_name}")
                return True
            else:
                print_error(f"Build failed - không tìm thấy file output")
                return False
        else:
            print_error(f"Build failed với exit code: {return_code}")
            return False
            
    except Exception as e:
        print_error(f"Exception khi build: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_distribution_package():
    """Tạo package distribution với tất cả files cần thiết"""
    print_header("TẠO DISTRIBUTION PACKAGE")
    
    # Tạo thư mục dist_windows
    dist_dir = Path("dist_windows")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()
    print_step(f"Đã tạo thư mục: {dist_dir}")
    
    # Copy .exe files
    print_step("Copy các file .exe...")
    build_dir = Path("dist")
    exe_count = 0
    if build_dir.exists():
        for exe_file in build_dir.glob("*"):
            if exe_file.is_file():
                print(f"  Copying: {exe_file.name}", flush=True)
                shutil.copy(exe_file, dist_dir / exe_file.name)
                exe_count += 1
    
    if exe_count == 0:
        print_error("Không tìm thấy file .exe nào!")
        return None
    
    print_success(f"Đã copy {exe_count} file .exe")
    
    # Copy config files
    print_step("Copy các file config...")
    for config_file in CONFIG_FILES:
        if Path(config_file).exists():
            shutil.copy(config_file, dist_dir / config_file)
            print(f"  ✓ {config_file}", flush=True)
    
    # Create README
    print_step("Tạo README.txt...")
    create_readme(dist_dir)
    
    # Create updated batch scripts
    print_step("Tạo batch scripts...")
    create_batch_scripts(dist_dir)
    
    print_success(f"Distribution package hoàn tất: {dist_dir.absolute()}")
    return dist_dir

def create_readme(dist_dir):
    """Tạo file README cho distribution"""
    readme_content = """
================================================================================
                    QBOT V2.0 - BINANCE FUTURES TRADING BOT
================================================================================

⭐ BUILD: Production Ready
📅 DATE: """ + str(Path(__file__).stat().st_mtime) + """

📋 YÊU CẦU
----------
- Windows 10/11 (64-bit)
- Kết nối Internet
- Không cần Python (đã đóng gói)

🚀 SETUP
--------
1. Copy: config.ini.example → config.ini
2. Điền: API keys, Telegram, Google Sheets ID
3. Đặt credentials.json vào folder này
4. Lần đầu chạy sẽ mở browser để authenticate Google

🎮 CHẠY BOT
-----------
▶ Tất cả:    start_all_bots.bat
▶ Từng cái:  Double-click file .exe
▶ Dừng:      stop_all_bots.bat

📂 CÁC MODULE
-------------
✅ hd_order.exe                    → Entry orders (Lệnh 1a)
✅ hd_order_123.exe                → Auto SL/TP (Lệnh 1b, 1c)
✅ hd_alert_possition_and_open_order.exe → Monitor
✅ hd_update_all.exe               → Market data (47+ columns)
✅ hd_update_price.exe             → Price updates
✅ hd_update_cho_va_khop.exe       → Status updates
✅ hd_update_danhmuc.exe           → Category updates
✅ hd_track_30_prices.exe          → Track 30 prices
✅ hd_periodic_report.exe          → Periodic reports
✅ hd_cancel_orders_schedule.exe   → Cancel scheduler
✅ hd_isolated_crossed_converter.exe → Margin converter
✅ check_status.exe                → Status checker

📚 TÀI LIỆU
-----------
⭐ QUICK_START.md  ← ĐỌC FILE NÀY (Cấu trúc + Logic + Setup)

📝 LOGS
-------
Tất cả logs trong folder: logs/
- hd_order_{timestamp}.log
- cascade_manager.txt (chi tiết tính toán SL/TP)
- order.log (tất cả orders)

⚠️ QUAN TRỌNG
-------------
✅ SL/TP tính từ ENTRY PRICE (giá khớp thực tế)
❌ KHÔNG tính từ Activation Price hoặc Current Price
✅ Bot tự động skip symbol không hợp lệ
✅ Bot validate tránh trigger ngay

🔐 BẢO MẬT
----------
- Binance API: Enable IP Whitelist
- Binance API: CHỈ enable Futures Trading
- Binance API: KHÔNG enable Withdraw
- KHÔNG chia sẻ config.ini, credentials.json

📞 HỖ TRỢ
---------
1. Đọc QUICK_START.md (hướng dẫn đầy đủ)
2. Xem logs trong logs/ folder
3. Chạy test scripts để debug

================================================================================
QBot v2.0 - Production Ready ✅
================================================================================
"""
    
    with open(dist_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("  ✓ README.txt", flush=True)

def create_batch_scripts(dist_dir):
    """Tạo các batch scripts để chạy .exe"""
    
    # Start script
    start_script = """@echo off
chcp 65001 >nul
REM QBot v2.0 - Start All Trading Bots

echo ========================================
echo   QBot v2.0 - Khởi Động 11 Modules
echo ========================================
echo.

REM Check config.ini
if not exist config.ini (
    echo ❌ KHÔNG TÌM THẤY config.ini!
    echo.
    echo Vui lòng:
    echo 1. Copy config.ini.example thành config.ini
    echo 2. Mở config.ini và điền thông tin của bạn
    echo.
    pause
    exit /b 1
)

echo ✅ Tìm thấy config.ini
echo.
echo 🚀 Đang khởi động các modules...
echo.

REM Module 1: Order Handler (CRITICAL)
if exist hd_order.exe (
    echo [1/11] Khởi động hd_order.exe (Entry Orders)...
    start "QBot - Order Handler" hd_order.exe
    timeout /t 2 >nul
)

REM Module 2: SL/TP Handler (CRITICAL)
if exist hd_order_123.exe (
    echo [2/11] Khởi động hd_order_123.exe (Auto SL/TP)...
    start "QBot - SL/TP Handler" hd_order_123.exe
    timeout /t 2 >nul
)

REM Module 3: Position Monitor (IMPORTANT)
if exist hd_alert_possition_and_open_order.exe (
    echo [3/11] Khởi động hd_alert_possition_and_open_order.exe...
    start "QBot - Alerts" hd_alert_possition_and_open_order.exe
    timeout /t 2 >nul
)

REM Module 4: Market Data Updater (IMPORTANT)
if exist hd_update_all.exe (
    echo [4/11] Khởi động hd_update_all.exe (47+ columns)...
    start "QBot - Market Data" hd_update_all.exe
    timeout /t 2 >nul
)

REM Module 5: Price Updater
if exist hd_update_price.exe (
    echo [5/11] Khởi động hd_update_price.exe...
    start "QBot - Price Update" hd_update_price.exe
    timeout /t 2 >nul
)

REM Module 6: Status Updater
if exist hd_update_cho_va_khop.exe (
    echo [6/11] Khởi động hd_update_cho_va_khop.exe...
    start "QBot - Status Update" hd_update_cho_va_khop.exe
    timeout /t 2 >nul
)

REM Module 7: Category Updater
if exist hd_update_danhmuc.exe (
    echo [7/11] Khởi động hd_update_danhmuc.exe...
    start "QBot - Category Update" hd_update_danhmuc.exe
    timeout /t 2 >nul
)

REM Module 8: 30 Prices Tracker (NEW in v2.0)
if exist hd_track_30_prices.exe (
    echo [8/11] Khởi động hd_track_30_prices.exe (NEW v2.0)...
    start "QBot - 30 Prices Tracker" hd_track_30_prices.exe
    timeout /t 2 >nul
)

REM Module 9: Periodic Report (NEW in v2.0)
if exist hd_periodic_report.exe (
    echo [9/11] Khởi động hd_periodic_report.exe (NEW v2.0)...
    start "QBot - Periodic Report" hd_periodic_report.exe
    timeout /t 2 >nul
)

REM Module 10: Cancel Orders Scheduler
if exist hd_cancel_orders_schedule.exe (
    echo [10/11] Khởi động hd_cancel_orders_schedule.exe...
    start "QBot - Cancel Scheduler" hd_cancel_orders_schedule.exe
    timeout /t 2 >nul
)

REM Module 11: Isolated/Crossed Converter
if exist hd_isolated_crossed_converter.exe (
    echo [11/11] Khởi động hd_isolated_crossed_converter.exe...
    start "QBot - Margin Converter" hd_isolated_crossed_converter.exe
    timeout /t 1 >nul
)

echo.
echo ========================================
echo   ✅ Đã khởi động 11 modules!
echo ========================================
echo.
echo 📌 Kiểm tra:
echo    - Mở Task Manager để xem 11 processes
echo    - Xem 11 cửa sổ CMD đã mở
echo    - Kiểm tra file .log để xem hoạt động
echo    - Kiểm tra Telegram nhận thông báo
echo.
echo 📊 Modules v2.0:
echo    ✅ Core: hd_order, hd_order_123, hd_alert
echo    ✅ Data: hd_update_all, hd_track_30_prices (NEW)
echo    ✅ Report: hd_periodic_report (NEW)
echo.
echo 🛑 Để dừng: Chạy stop_all_bots.bat
echo    hoặc đóng tất cả cửa sổ CMD
echo.
echo ========================================
pause
"""
    
    with open(dist_dir / "start_all_bots.bat", "w", encoding="utf-8") as f:
        f.write(start_script)
    print("  ✓ start_all_bots.bat", flush=True)
    
    # Stop script
    stop_script = """@echo off
chcp 65001 >nul
REM QBot v2.0 - Stop All Trading Bots

echo ========================================
echo   QBot v2.0 - Dừng 11 Modules
echo ========================================
echo.

echo 🛑 Đang dừng 11 modules...
echo.

taskkill /F /IM hd_order.exe 2>nul
taskkill /F /IM hd_order_123.exe 2>nul
taskkill /F /IM hd_alert_possition_and_open_order.exe 2>nul
taskkill /F /IM hd_update_all.exe 2>nul
taskkill /F /IM hd_update_price.exe 2>nul
taskkill /F /IM hd_update_cho_va_khop.exe 2>nul
taskkill /F /IM hd_update_danhmuc.exe 2>nul
taskkill /F /IM hd_track_30_prices.exe 2>nul
taskkill /F /IM hd_periodic_report.exe 2>nul
taskkill /F /IM hd_cancel_orders_schedule.exe 2>nul
taskkill /F /IM hd_isolated_crossed_converter.exe 2>nul
taskkill /F /IM check_status.exe 2>nul

echo.
echo ========================================
echo   ✅ Đã dừng tất cả modules!
echo ========================================
echo.
pause
"""
    
    with open(dist_dir / "stop_all_bots.bat", "w", encoding="utf-8") as f:
        f.write(stop_script)
    print("  ✓ stop_all_bots.bat", flush=True)

def main():
    """Main function"""
    print_header("QBOT V2.0 - WINDOWS BUILD SCRIPT")
    print("Build 12 modules thành .exe files cho Windows", flush=True)
    print("Chạy trên: Mac/Linux → Build cho Windows VPS", flush=True)
    print(f"Platform: {sys.platform}", flush=True)
    print(f"Python: {sys.version}", flush=True)
    
    # Kiểm tra yêu cầu
    if not check_requirements():
        print_error("Không đáp ứng yêu cầu hệ thống!")
        sys.exit(1)
    
    # Dọn dẹp
    clean_previous_builds()
    
    # Build từng module
    print_header("BẮT ĐẦU BUILD MODULES")
    
    success_count = 0
    failed_modules = []
    skipped_modules = []
    
    for i, module in enumerate(MODULES, 1):
        print(f"\n[{i}/{len(MODULES)}] Building {module}...", flush=True)
        
        if not Path(module).exists():
            print_warning(f"Module không tồn tại, bỏ qua: {module}")
            skipped_modules.append(module)
            continue
        
        if build_single_module(module):
            success_count += 1
        else:
            failed_modules.append(module)
    
    # Summary
    print_header("KẾT QUẢ BUILD")
    print(f"\n✅ Thành công: {success_count}/{len(MODULES)}", flush=True)
    
    if skipped_modules:
        print(f"⏭️  Bỏ qua: {len(skipped_modules)}", flush=True)
        for mod in skipped_modules:
            print(f"   - {mod}", flush=True)
    
    if failed_modules:
        print(f"\n❌ Thất bại: {len(failed_modules)}", flush=True)
        for mod in failed_modules:
            print(f"   - {mod}", flush=True)
    
    # Tạo distribution package
    if success_count > 0:
        dist_dir = create_distribution_package()
        
        if dist_dir:
            print_header("✅ BUILD HOÀN TẤT!")
            print(f"\n📦 Package: {dist_dir.absolute()}", flush=True)
            print("\n📋 Các bước tiếp theo:", flush=True)
            print("   1. Copy folder 'dist_windows' sang máy Windows", flush=True)
            print("   2. Đọc README.txt trong folder", flush=True)
            print("   3. Cấu hình config.ini", flush=True)
            print("   4. Chạy start_all_bots.bat", flush=True)
            print("\n" + "=" * 70, flush=True)
            return 0
        else:
            print_error("Không thể tạo distribution package!")
            return 1
    else:
        print_error("\nKhông có module nào được build thành công!")
        print("\nKiểm tra:", flush=True)
        print("  - PyInstaller đã cài đúng chưa: python3 -m pip install pyinstaller", flush=True)
        print("  - Các module .py có tồn tại không", flush=True)
        print("  - Xem log chi tiết ở trên", flush=True)
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Build bị hủy bởi user", flush=True)
        sys.exit(130)
    except Exception as e:
        print_error(f"\nLỗi không mong đợi: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
