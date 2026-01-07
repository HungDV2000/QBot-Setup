@echo off
chcp 65001 >nul 2>&1
REM ============================================================================
REM QBot v2.1 - Setup & Installation Script with Logging
REM Tự động cài đặt Python libraries và tạo config file
REM Log: info.txt (thông tin), error.txt (lỗi)
REM ============================================================================

title QBot Setup - Cài Đặt Tự Động

REM ============================================================================
REM VERBOSE MODE - Hiển thị tất cả output
REM ============================================================================
REM Đặt VERBOSE=1 để xem tất cả output, VERBOSE=0 để ẩn
set "VERBOSE=1"

REM ============================================================================
REM KHỞI TẠO LOGGING
REM ============================================================================
REM Tạo log files trong thư mục cha (qbot_setup/) để tránh lỗi quyền
set "INFO_LOG=..\setup_info.txt"
set "ERROR_LOG=..\setup_error.txt"

REM Clear log files (với error handling)
if "%VERBOSE%"=="1" (
    echo [DEBUG] Creating log files in parent directory...
    echo [DEBUG] INFO_LOG: %INFO_LOG%
    echo [DEBUG] ERROR_LOG: %ERROR_LOG%
)

REM Try to create log files with better error handling
echo. > "%INFO_LOG%" 2>nul
if errorlevel 1 (
    echo ⚠️  CẢNH BÁO: Không thể tạo log file trong thư mục cha
    echo 💡 Thử tạo log trong thư mục hiện tại...
    set "INFO_LOG=setup_info.txt"
    set "ERROR_LOG=setup_error.txt"
    echo. > "%INFO_LOG%" 2>nul
    if errorlevel 1 (
        echo ⚠️  CẢNH BÁO: Không thể tạo log files!
        echo 📌 Script sẽ tiếp tục nhưng KHÔNG CÓ LOG.
        echo.
        set "LOGGING_DISABLED=1"
        REM Không exit, chỉ disable logging
    ) else (
        echo ✅ Log sẽ được lưu trong: %CD%
        set "LOGGING_DISABLED=0"
    )
) else (
    set "LOGGING_DISABLED=0"
)

if "%LOGGING_DISABLED%"=="0" (
    echo. > "%ERROR_LOG%" 2>nul
    if errorlevel 1 (
        echo ⚠️  Không thể tạo error.txt, chỉ dùng info.txt
    )
)

if "%VERBOSE%"=="1" (
    if "%LOGGING_DISABLED%"=="0" (
        echo [DEBUG] Log files created successfully
    ) else (
        echo [DEBUG] Logging disabled due to write permission error
    )
)

REM Helper function để ghi log với timestamp
call :LogInfo "=========================================="
call :LogInfo "QBot v2.1 - Setup Installation Started"
call :LogInfo "Current directory: %CD%"
call :LogInfo "Verbose mode: %VERBOSE%"
call :LogInfo "=========================================="

cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                   QBot v2.1 - Cài Đặt Tự Động                         ║
echo ║                   Setup ^& Installation Wizard                          ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM ============================================================================
REM MENU LỰA CHỌN CÀI ĐẶT
REM ============================================================================
:MainMenu
call :LogInfo "Displaying main menu"
echo.
echo ═══════════════════════════════════════════════════════════════════════
echo 📋 MENU CÀI ĐẶT - Vui lòng chọn tác vụ:
echo ═══════════════════════════════════════════════════════════════════════
echo.
echo    [1] 🚀 CÀI ĐẶT TOÀN BỘ (Khuyến nghị)
echo        └─ Cài Python + Thư viện + Config + Kiểm tra files
echo.
echo    [2] 🐍 CHỈ CÀI PYTHON
echo        └─ Tự động tải và cài đặt Python 3.11
echo.
echo    [3] 📦 CHỈ CÀI THƯ VIỆN PYTHON
echo        └─ Cài các thư viện từ requirements.txt
echo.
echo    [4] 📝 CHỈ TẠO FILE CONFIG
echo        └─ Tạo config.ini mẫu
echo.
echo    [5] 🔍 CHỈ KIỂM TRA FILES
echo        └─ Kiểm tra các file source code cần thiết
echo.
echo    [6] ✅ KIỂM TRA MÔI TRƯỜNG
echo        └─ Kiểm tra Python, pip, libraries đã cài chưa
echo.
echo    [0] ❌ THOÁT
echo.
echo ═══════════════════════════════════════════════════════════════════════
echo.
set /p MENU_CHOICE="👉 Nhập lựa chọn của bạn (0-6): "

call :LogInfo "User selected menu option: %MENU_CHOICE%"

if "%MENU_CHOICE%"=="1" goto :FullInstall
if "%MENU_CHOICE%"=="2" goto :InstallPythonOnly
if "%MENU_CHOICE%"=="3" goto :InstallLibrariesOnly
if "%MENU_CHOICE%"=="4" goto :CreateConfigOnly
if "%MENU_CHOICE%"=="5" goto :CheckFilesOnly
if "%MENU_CHOICE%"=="6" goto :CheckEnvironment
if "%MENU_CHOICE%"=="0" goto :ExitScript

echo.
echo ❌ Lựa chọn không hợp lệ! Vui lòng chọn từ 0-6.
echo.
pause
cls
goto :MainMenu

REM ============================================================================
REM OPTION 1: CÀI ĐẶT TOÀN BỘ
REM ============================================================================
:FullInstall
call :LogInfo "Starting full installation"
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                      CÀI ĐẶT TOÀN BỘ                                  ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo 📦 Các bước sẽ thực hiện:
echo    ✓ Kiểm tra và cài đặt Python 3.11
echo    ✓ Cài đặt pip và nâng cấp
echo    ✓ Cài đặt tất cả thư viện Python
echo    ✓ Tạo file config.ini mẫu
echo    ✓ Kiểm tra các file source code
echo.
set /p CONFIRM_FULL="👉 Bạn có chắc muốn tiếp tục? (Y/N): "
if /i not "%CONFIRM_FULL%"=="Y" (
    call :LogInfo "User cancelled full installation"
    goto :MainMenu
)
echo.

REM ============================================================================
REM KIỂM TRA PATH VÀ CẤU TRÚC THƯ MỤC
REM ============================================================================
call :LogInfo "Checking directory structure..."

REM Kiểm tra nếu file requirements.txt tồn tại
if not exist ../requirements.txt (
    call :LogError "CRITICAL: requirements.txt not found in parent directory"
    echo.
    echo ❌ LỖI NGHIÊM TRỌNG: Không tìm thấy requirements.txt!
    echo.
    echo 📁 Cấu trúc thư mục hiện tại:
    echo    Current: %CD%
    echo    Expected: qbot_setup\setup\
    echo.
    echo 💡 Vui lòng:
    echo    1. Đảm bảo bạn đang ở đúng thư mục qbot_setup\setup\
    echo    2. Kiểm tra file requirements.txt có trong qbot_setup\
    echo.
    pause
    exit /b 1
)

call :LogInfo "requirements.txt found"
echo ✅ Kiểm tra cấu trúc thư mục: OK
echo.

REM ============================================================================
REM BƯỚC 1: KIỂM TRA VÀ CÀI ĐẶT PYTHON TỰ ĐỘNG
REM ============================================================================
:Step1_CheckPython
echo [1/6] Đang kiểm tra Python...
call :LogInfo "[STEP 1/6] Checking Python installation"

python --version >nul 2>&1
if errorlevel 1 (
    call :LogInfo "Python not found. Starting auto-installation..."
    echo.
    echo ⚠️  Python chưa được cài đặt!
    echo.
    echo 🤖 Đang chuẩn bị CÀI ĐẶT TỰ ĐỘNG Python...
    echo    (Quá trình này sẽ mất 2-5 phút)
    echo.
    
    REM Ask user for confirmation
    set /p AUTO_INSTALL="   Bạn có muốn cài đặt Python TỰ ĐỘNG không? (Y/N): "
    if /i not "%AUTO_INSTALL%"=="Y" (
        call :LogError "User declined Python auto-installation"
        echo.
        echo ❌ Đã hủy cài đặt tự động.
        echo.
        echo 📌 Vui lòng cài đặt Python thủ công từ:
        echo    https://www.python.org/downloads/
        echo.
        echo 💡 Lưu ý: Tick chọn "Add Python to PATH" khi cài đặt!
        echo.
        pause
        exit /b 1
    )
    
    call :LogInfo "User confirmed Python auto-installation"
    echo.
    echo ═══════════════════════════════════════════════════════════════════════
    echo 🔄 BẮT ĐẦU CÀI ĐẶT PYTHON TỰ ĐỘNG...
    echo ═══════════════════════════════════════════════════════════════════════
    echo.
    
    REM Try Method 1: Winget (Windows Package Manager)
    echo [Phương pháp 1] Thử cài đặt bằng Winget...
    call :LogInfo "Trying Method 1: Winget installation"
    
    if "%VERBOSE%"=="1" (
        echo [DEBUG] Checking winget availability...
    )
    
    winget --version >nul 2>&1
    if not errorlevel 1 (
        call :LogInfo "Winget is available"
        echo ✅ Winget có sẵn! Đang cài đặt Python 3.11...
        echo.
        echo 💡 Cửa sổ UAC sẽ hiện ra, vui lòng click "Yes/Có"
        echo.
        
        if "%VERBOSE%"=="1" (
            echo [DEBUG] Running: winget install Python.Python.3.11 --silent...
            winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
        ) else (
            winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
        )
        
        if not errorlevel 1 (
            call :LogInfo "Python installed successfully via Winget"
            echo.
            echo ✅ Cài đặt Python qua Winget thành công!
            echo 🔄 Đang refresh PATH...
            
            REM Refresh environment variables
            call :RefreshPath
            
            REM Verify installation
            python --version >nul 2>&1
            if not errorlevel 1 (
                echo ✅ Xác nhận: Python đã sẵn sàng!
                goto :PythonInstalled
            )
        ) else (
            call :LogError "Winget installation failed"
        )
    ) else (
        call :LogInfo "Winget not available"
    )
    
    echo ⚠️  Winget không khả dụng hoặc cài đặt thất bại.
    echo.
    
    REM Try Method 2: Direct Download
    echo [Phương pháp 2] Tải trực tiếp từ Python.org...
    call :LogInfo "Trying Method 2: Direct download from Python.org"
    echo.
    echo 📥 Đang tải Python 3.11.9 installer...
    echo    (Kích thước: ~27 MB)
    echo.
    
    REM Download Python installer using PowerShell
    set PYTHON_INSTALLER=python-3.11.9-amd64.exe
    set PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    
    call :LogInfo "Downloading Python installer: %PYTHON_INSTALLER%"
    if "%VERBOSE%"=="1" (
        echo [DEBUG] Downloading from: %PYTHON_URL%
        powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'}"
    ) else (
        powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'}" >nul 2>&1
    )
    
    if errorlevel 1 (
        call :LogError "Failed to download Python installer"
        echo.
        echo ❌ LỖI: Không thể tải Python installer!
        echo.
        echo 💡 Vui lòng:
        echo    1. Kiểm tra kết nối internet
        echo    2. Hoặc tải thủ công từ: https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
    
    call :LogInfo "Python installer downloaded successfully"
    echo ✅ Tải xuống thành công!
    echo.
    echo 🔧 Đang cài đặt Python...
    echo    (Cửa sổ UAC sẽ hiện ra, vui lòng click "Yes/Có")
    echo.
    
    REM Install Python silently with PATH
    call :LogInfo "Installing Python silently..."
    if "%VERBOSE%"=="1" (
        echo [DEBUG] Running: %PYTHON_INSTALLER% /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        %PYTHON_INSTALLER% /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    ) else (
        %PYTHON_INSTALLER% /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 >nul 2>&1
    )
    
    if errorlevel 1 (
        call :LogError "Python installation failed"
        echo.
        echo ❌ LỖI: Cài đặt Python thất bại!
        echo.
        echo 💡 Vui lòng:
        echo    1. Chạy lại script với quyền Administrator
        echo    2. Hoặc cài thủ công bằng file: %PYTHON_INSTALLER%
        echo.
        pause
        exit /b 1
    )
    
    call :LogInfo "Python installed successfully via Direct Download"
    echo ✅ Cài đặt Python thành công!
    echo.
    echo 🔄 Đang refresh PATH...
    
    REM Cleanup installer
    if exist %PYTHON_INSTALLER% del %PYTHON_INSTALLER%
    
    REM Refresh environment variables
    call :RefreshPath
    
    REM Verify installation
    python --version >nul 2>&1
    if errorlevel 1 (
        call :LogError "Python installed but not found in PATH"
        echo.
        echo ⚠️  CẢNH BÁO: Python đã cài nhưng chưa thấy trong PATH
        echo.
        echo 💡 Vui lòng:
        echo    1. ĐÓNG cửa sổ CMD này
        echo    2. MỞ LẠI CMD mới
        echo    3. CHẠY LẠI file này: 1_setup_install.bat
        echo.
        pause
        exit /b 1
    )
    
    :PythonInstalled
    echo.
    echo ═══════════════════════════════════════════════════════════════════════
    echo ✅ PYTHON ĐÃ CÀI ĐẶT THÀNH CÔNG!
    echo ═══════════════════════════════════════════════════════════════════════
    echo.
) else (
    call :LogInfo "Python already installed"
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
call :LogInfo "Python version: %PYTHON_VERSION%"
echo ✅ Python version: %PYTHON_VERSION%
echo.

REM If called from Option 2 (Python only), return to menu
if "%MENU_CHOICE%"=="2" (
    echo.
    echo ═══════════════════════════════════════════════════════════════════════
    echo ✅ HOÀN TẤT CÀI ĐẶT PYTHON!
    echo ═══════════════════════════════════════════════════════════════════════
    echo.
    pause
    goto :MainMenu
)

REM ============================================================================
REM BƯỚC 2: KIỂM TRA PIP
REM ============================================================================
:Step2_CheckPip
echo [2/6] Đang kiểm tra pip (Python package manager)...
call :LogInfo "[STEP 2/6] Checking pip"

python -m pip --version >nul 2>&1
if errorlevel 1 (
    call :LogError "pip not found"
    echo ❌ LỖI: pip không có sẵn!
    echo 📌 Đang cố gắng cài đặt pip...
    call :LogInfo "Installing pip..."
    
    python -m ensurepip --default-pip
    if errorlevel 1 (
        call :LogError "Failed to install pip"
        echo ❌ Không thể cài đặt pip tự động!
        pause
        exit /b 1
    )
    call :LogInfo "pip installed successfully"
) else (
    call :LogInfo "pip is available"
)
echo ✅ pip sẵn sàng!
echo.

REM ============================================================================
REM BƯỚC 3: CÀI ĐẶT THƯ VIỆN
REM ============================================================================
:Step3_InstallLibraries
echo [3/6] Đang cài đặt thư viện Python...
call :LogInfo "[STEP 3/6] Installing Python libraries"
echo.
echo 📦 Danh sách thư viện sẽ được cài đặt:
echo    - ccxt (Binance API)
echo    - Google Sheets API (5 packages)
echo    - pandas, numpy (Data processing)
echo    - python-telegram-bot (Telegram)
echo    - requests (HTTP)
echo    - pytz, python-dateutil (Utilities)
echo    - pyinstaller (Build tools)
echo.
echo 💡 Quá trình này có thể mất 2-5 phút...
echo.
pause

echo 🔄 Đang cài đặt...
call :LogInfo "Upgrading pip..."
if "%VERBOSE%"=="1" (
    echo [DEBUG] Running: python -m pip install --upgrade pip
    python -m pip install --upgrade pip
) else (
    python -m pip install --upgrade pip >nul 2>&1
)

if errorlevel 1 (
    call :LogError "Failed to upgrade pip"
)

call :LogInfo "Installing packages from requirements.txt..."
if "%VERBOSE%"=="1" (
    echo [DEBUG] Running: python -m pip install -r ../requirements.txt
    python -m pip install -r ../requirements.txt
) else (
    python -m pip install -r ../requirements.txt >nul 2>&1
)

if errorlevel 1 (
    call :LogError "Failed to install Python libraries"
    echo.
    echo ❌ LỖI: Cài đặt thư viện thất bại!
    echo.
    echo 💡 Thử các cách sau:
    echo    1. Kiểm tra kết nối internet
    echo    2. Chạy CMD với quyền Administrator
    echo    3. Cài thủ công: pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

call :LogInfo "All Python libraries installed successfully"
echo.
echo ✅ Cài đặt thư viện thành công!
echo.

REM If called from Option 3 (Libraries only), return to menu
if "%MENU_CHOICE%"=="3" (
    echo.
    echo ═══════════════════════════════════════════════════════════════════════
    echo ✅ HOÀN TẤT CÀI ĐẶT THƯ VIỆN!
    echo ═══════════════════════════════════════════════════════════════════════
    echo.
    pause
    goto :MainMenu
)

REM ============================================================================
REM BƯỚC 4: TẠO CONFIG FILE (NẾU CHƯA CÓ)
REM ============================================================================
:Step4_CreateConfig
echo [4/6] Đang kiểm tra file config...
call :LogInfo "[STEP 4/6] Checking config.ini"
echo.

if exist ../config.ini (
    call :LogInfo "config.ini already exists"
    echo ⚠️  File config.ini đã tồn tại!
    echo.
    set /p OVERWRITE="   Bạn có muốn TẠO FILE MẪU MỚI (config.template.ini)? (Y/N): "
    if /i "%OVERWRITE%"=="Y" (
        copy ../config.ini ../config.template.ini >nul
        call :LogInfo "Created config.template.ini"
        echo ✅ Đã tạo config.template.ini
    )
) else (
    call :LogInfo "Creating config.ini template..."
    echo 📝 Đang tạo file config.ini mẫu...
    (
        echo [global]
        echo.
        echo max_increase_decrease_4h_day_count = 60
        echo.
        echo ; === TRADING PARAMETERS ===
        echo lenh2_rate_long = 0.3
        echo lenh2_rate_short = 0.3
        echo lenh3_rate_long = 0.6
        echo lenh3_rate_short = 0.6
        echo.
        echo ;thêm biến
        echo lenh3_callback_rate = 1
        echo cancel_orders_minutes = 1
        echo.
        echo ; === OPERATION MODE ===
        echo is_print_mode = false
        echo top_count = 50
        echo time_gap_do_it = 0
        echo test_mode = false
        echo.
        echo ; === TELEGRAM ===
        echo bot_token = YOUR_TELEGRAM_BOT_TOKEN
        echo chat_id = YOUR_TELEGRAM_CHAT_ID
        echo prefix_channel = TEST BOT
        echo.
        echo ; === BINANCE API ===
        echo key_name = YOUR_KEY_NAME
        echo key_binance = YOUR_BINANCE_API_KEY
        echo secret_binance = YOUR_BINANCE_SECRET_KEY
        echo.
        echo ; === GOOGLE SHEETS ===
        echo spreadsheet_id = YOUR_GOOGLE_SPREADSHEET_ID
        echo tab_dat_lenh = ĐẶT LỆNH ^(100 MÃ^)
        echo.
        echo ; === DELAY SETTINGS (seconds) ===
        echo delay_vao_lenh = 60
        echo delay_vao_lenh_123 = 300
        echo delay_cho_va_khop = 600
        echo delay_calert_possition_and_open_order = 120
        echo delay_update_price = 120
        echo delay_update_all = 120
        echo.
        echo ; === PHASE 3 ^& 4: DATA COLLECTION ^& NOTIFICATIONS ===
        echo delay_track_30_prices = 60
        echo delay_periodic_report = 300
    ) > ../config.ini
    call :LogInfo "config.ini created successfully"
    echo ✅ Đã tạo config.ini mẫu!
)

echo.

REM If called from Option 4 (Config only), return to menu
if "%MENU_CHOICE%"=="4" (
    echo.
    echo ═══════════════════════════════════════════════════════════════════════
    echo ✅ HOÀN TẤT TẠO CONFIG!
    echo ═══════════════════════════════════════════════════════════════════════
    echo.
    pause
    goto :MainMenu
)

REM ============================================================================
REM BƯỚC 5: KIỂM TRA CÁC FILE CẦN THIẾT
REM ============================================================================
:Step5_CheckFiles
echo [5/6] Đang kiểm tra các file cần thiết...
call :LogInfo "[STEP 5/6] Checking required files"
echo.

set MISSING_FILES=0

REM Core modules
if not exist ../hd_order.py (
    call :LogError "Missing CRITICAL file: hd_order.py"
    echo ❌ THIẾU: hd_order.py ^(CRITICAL^)
    set MISSING_FILES=1
)
if not exist ../hd_order_123.py (
    call :LogError "Missing CRITICAL file: hd_order_123.py"
    echo ❌ THIẾU: hd_order_123.py ^(CRITICAL^)
    set MISSING_FILES=1
)
if not exist ../hd_order_market_price.py (
    call :LogError "Missing file: hd_order_market_price.py"
    echo ❌ THIẾU: hd_order_market_price.py
    set MISSING_FILES=1
)

REM Helper modules (CRITICAL)
if not exist ../cst.py (
    call :LogError "Missing CRITICAL file: cst.py"
    echo ❌ THIẾU: cst.py ^(CRITICAL - Config loader^)
    set MISSING_FILES=1
)
if not exist ../binance_order_helper.py (
    call :LogError "Missing file: binance_order_helper.py"
    echo ❌ THIẾU: binance_order_helper.py
    set MISSING_FILES=1
)
if not exist ../utils.py (
    call :LogError "Missing file: utils.py"
    echo ❌ THIẾU: utils.py
    set MISSING_FILES=1
)
if not exist ../binance_utils.py (
    call :LogError "Missing file: binance_utils.py"
    echo ❌ THIẾU: binance_utils.py
    set MISSING_FILES=1
)

REM Update modules
if not exist ../hd_update_all.py (
    call :LogError "Missing file: hd_update_all.py"
    echo ❌ THIẾU: hd_update_all.py
    set MISSING_FILES=1
)
if not exist ../hd_update_price.py (
    call :LogError "Missing file: hd_update_price.py"
    echo ❌ THIẾU: hd_update_price.py
    set MISSING_FILES=1
)
if not exist ../hd_update_cho_va_khop.py (
    call :LogError "Missing file: hd_update_cho_va_khop.py"
    echo ❌ THIẾU: hd_update_cho_va_khop.py
    set MISSING_FILES=1
)

REM Support modules
if not exist ../gg_sheet_factory.py (
    call :LogError "Missing file: gg_sheet_factory.py"
    echo ❌ THIẾU: gg_sheet_factory.py
    set MISSING_FILES=1
)
if not exist ../telegram_factory.py (
    call :LogError "Missing file: telegram_factory.py"
    echo ❌ THIẾU: telegram_factory.py
    set MISSING_FILES=1
)
if not exist ../cascade_manager.py (
    call :LogError "Missing file: cascade_manager.py"
    echo ❌ THIẾU: cascade_manager.py
    set MISSING_FILES=1
)

REM Google credentials
if not exist ../credentials.json (
    call :LogInfo "WARNING: credentials.json not found"
    echo ⚠️  CẢNH BÁO: credentials.json không tồn tại
    echo    ^(Cần để kết nối Google Sheets^)
    set MISSING_FILES=1
)

if %MISSING_FILES%==1 (
    call :LogError "Some required files are missing"
    echo.
    echo ⚠️  Một số file quan trọng bị thiếu!
    echo 💡 Vui lòng đảm bảo bạn đã copy đầy đủ source code.
) else (
    call :LogInfo "All required files are present"
    echo ✅ Tất cả file cần thiết đã sẵn sàng!
)

echo.

REM If called from Option 5 (Check files only), return to menu
if "%MENU_CHOICE%"=="5" (
    echo.
    echo ═══════════════════════════════════════════════════════════════════════
    echo ✅ HOÀN TẤT KIỂM TRA FILES!
    echo ═══════════════════════════════════════════════════════════════════════
    echo.
    pause
    goto :MainMenu
)

REM ============================================================================
REM BƯỚC 6: TÓM TẮT VÀ HƯỚNG DẪN TIẾP THEO
REM ============================================================================
:Step6_Summary
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                        CÀI ĐẶT HOÀN TẤT!                              ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

call :LogInfo "[STEP 6/6] Installation summary"
call :LogInfo "Python: %PYTHON_VERSION%"
call :LogInfo "pip: Ready"
call :LogInfo "Libraries: Installed"
call :LogInfo "config.ini: Ready"
call :LogInfo "Missing files: %MISSING_FILES%"
call :LogInfo "=========================================="
call :LogInfo "Installation completed successfully"
call :LogInfo "=========================================="

echo 📊 TRẠNG THÁI CÀI ĐẶT:
echo.
echo    ✅ Python %PYTHON_VERSION%
echo    ✅ pip (Package Manager)
echo    ✅ 15+ Python Libraries

if exist ../config.ini (
    echo    ✅ config.ini
) else (
    echo    ⚠️  config.ini ^(CẦN CẤU HÌNH^)
)

if %MISSING_FILES%==0 (
    echo    ✅ Tất cả file source code
) else (
    echo    ⚠️  Một số file source code bị thiếu
)

echo.
echo ═══════════════════════════════════════════════════════════════════════
echo.
echo 📝 CÁC BƯỚC TIẾP THEO:
echo.
echo    1️⃣  CẤU HÌNH FILE config.ini
echo.
echo       📌 Mở file: ..\config.ini
echo       📌 Điền các thông tin:
echo.
echo          [TELEGRAM]
echo          • bot_token       - Token từ @BotFather
echo          • chat_id         - ID chat/group nhận thông báo
echo          • prefix_channel  - Prefix phân biệt bot (VD: "TEST BOT")
echo.
echo          [BINANCE]
echo          • key_binance     - API Key từ Binance
echo          • secret_binance  - Secret Key từ Binance
echo.
echo          [GOOGLE SHEETS]
echo          • spreadsheet_id  - ID của Google Sheet (trong URL)
echo.
echo    2️⃣  BỔ SUNG FILE credentials.json
echo.
echo       📌 Tải file credentials.json từ Google Cloud Console
echo       📌 Copy vào thư mục: %CD%\..
echo.
echo    3️⃣  CHẠY KIỂM TRA MÔI TRƯỜNG
echo.
echo       📌 Chạy file: 2_check_environment.bat
echo       📌 Đảm bảo tất cả kiểm tra đều PASS ✅
echo.
echo    4️⃣  KHỞI ĐỘNG BOT
echo.
echo       📌 Chạy file: 3_qbot_manager.bat
echo.
echo ═══════════════════════════════════════════════════════════════════════
echo.
if "%LOGGING_DISABLED%"=="0" (
    echo 💡 TIP: Xem log chi tiết tại:
    echo    • %INFO_LOG%
    echo    • %ERROR_LOG%
    echo.
) else (
    echo ⚠️  LƯU Ý: Logging bị tắt do lỗi quyền ghi file
    echo.
)
echo 📝 VERBOSE MODE: %VERBOSE% (Đổi thành 0 trong script để ẩn output chi tiết)
echo.
echo.
echo ═══════════════════════════════════════════════════════════════════════
set /p RETURN_MENU="👉 Quay lại menu chính? (Y/N): "
if /i "%RETURN_MENU%"=="Y" (
    cls
    goto :MainMenu
)
goto :ExitScript

REM ============================================================================
REM OPTION 2: CHỈ CÀI PYTHON
REM ============================================================================
:InstallPythonOnly
call :LogInfo "Starting Python-only installation"
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                      CÀI ĐẶT PYTHON 3.11                              ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
set /p CONFIRM_PYTHON="👉 Xác nhận cài đặt Python? (Y/N): "
if /i not "%CONFIRM_PYTHON%"=="Y" (
    call :LogInfo "User cancelled Python installation"
    goto :MainMenu
)
echo.

REM Jump to Python installation step
goto :Step1_CheckPython

REM ============================================================================
REM OPTION 3: CHỈ CÀI THƯ VIỆN
REM ============================================================================
:InstallLibrariesOnly
call :LogInfo "Starting libraries-only installation"
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                      CÀI ĐẶT THƯ VIỆN PYTHON                          ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM Check if Python exists
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ LỖI: Python chưa được cài đặt!
    echo.
    echo 💡 Vui lòng cài Python trước (chọn Option 2 hoặc Option 1)
    echo.
    pause
    goto :MainMenu
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Đã phát hiện Python %PYTHON_VERSION%
echo.

set /p CONFIRM_LIB="👉 Xác nhận cài đặt thư viện? (Y/N): "
if /i not "%CONFIRM_LIB%"=="Y" (
    call :LogInfo "User cancelled library installation"
    goto :MainMenu
)
echo.

REM Jump to library installation step
goto :Step3_InstallLibraries

REM ============================================================================
REM OPTION 4: CHỈ TẠO CONFIG
REM ============================================================================
:CreateConfigOnly
call :LogInfo "Starting config creation only"
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                      TẠO FILE CONFIG.INI                              ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM Jump to config creation step
goto :Step4_CreateConfig

REM ============================================================================
REM OPTION 5: CHỈ KIỂM TRA FILES
REM ============================================================================
:CheckFilesOnly
call :LogInfo "Starting file check only"
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                      KIỂM TRA FILES SOURCE CODE                       ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM Jump to file check step
goto :Step5_CheckFiles

REM ============================================================================
REM OPTION 6: KIỂM TRA MÔI TRƯỜNG
REM ============================================================================
:CheckEnvironment
call :LogInfo "Starting environment check"
cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                      KIỂM TRA MÔI TRƯỜNG                              ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

set ENV_OK=1

REM Check Python
echo [1/4] Kiểm tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo    ❌ Python: CHƯA CÀI
    set ENV_OK=0
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo    ✅ Python: %PYTHON_VERSION%
)
echo.

REM Check pip
echo [2/4] Kiểm tra pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo    ❌ pip: CHƯA CÀI
    set ENV_OK=0
) else (
    for /f "tokens=2" %%i in ('python -m pip --version 2^>^&1') do set PIP_VERSION=%%i
    echo    ✅ pip: %PIP_VERSION%
)
echo.

REM Check critical libraries
echo [3/4] Kiểm tra thư viện quan trọng...
python -c "import ccxt" 2>nul
if errorlevel 1 (
    echo    ❌ ccxt: CHƯA CÀI
    set ENV_OK=0
) else (
    echo    ✅ ccxt: OK
)

python -c "import telegram" 2>nul
if errorlevel 1 (
    echo    ❌ python-telegram-bot: CHƯA CÀI
    set ENV_OK=0
) else (
    echo    ✅ python-telegram-bot: OK
)

python -c "import gspread" 2>nul
if errorlevel 1 (
    echo    ❌ gspread: CHƯA CÀI
    set ENV_OK=0
) else (
    echo    ✅ gspread: OK
)

python -c "import pandas" 2>nul
if errorlevel 1 (
    echo    ❌ pandas: CHƯA CÀI
    set ENV_OK=0
) else (
    echo    ✅ pandas: OK
)
echo.

REM Check config.ini
echo [4/4] Kiểm tra file config...
if exist ../config.ini (
    echo    ✅ config.ini: TỒN TẠI
) else (
    echo    ❌ config.ini: CHƯA TẠO
    set ENV_OK=0
)
echo.

echo ═══════════════════════════════════════════════════════════════════════
if %ENV_OK%==1 (
    echo ✅ TẤT CẢ ĐỀU SẴN SÀNG! Bot có thể chạy được.
) else (
    echo ⚠️  MÔI TRƯỜNG CHƯA ĐẦY ĐỦ! Vui lòng cài đặt các phần còn thiếu.
    echo.
    echo 💡 Gợi ý: Chọn Option 1 (Cài đặt toàn bộ) từ menu chính.
)
echo ═══════════════════════════════════════════════════════════════════════
echo.
pause
goto :MainMenu

REM ============================================================================
REM EXIT SCRIPT
REM ============================================================================
:ExitScript
call :LogInfo "User exited the script"
echo.
echo 👋 Cảm ơn bạn đã sử dụng QBot Setup!
echo.
pause
exit /b 0

REM ============================================================================
REM HELPER FUNCTIONS
REM ============================================================================

:RefreshPath
REM Refresh environment PATH without restarting CMD
call :LogInfo "Refreshing PATH..."
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%b"

REM Check if paths were retrieved
if "%SYS_PATH%"=="" (
    call :LogError "Cannot retrieve system PATH from registry"
    echo ⚠️  CẢNH BÁO: Không đọc được System PATH từ registry
)
if "%USER_PATH%"=="" (
    call :LogInfo "User PATH not found in registry (this is OK)"
)

set "PATH=%SYS_PATH%;%USER_PATH%"
call :LogInfo "PATH refreshed"
echo ✅ PATH đã được refresh
goto :eof

:LogInfo
REM Log information with timestamp to info.txt
if "%LOGGING_DISABLED%"=="1" goto :eof
set "TIMESTAMP=%date% %time%"
echo [%TIMESTAMP%] [INFO] %~1 >> "%INFO_LOG%" 2>nul
REM Không hiển thị error nữa vì đã cảnh báo ở đầu
goto :eof

:LogError
REM Log error with timestamp to error.txt
if "%LOGGING_DISABLED%"=="1" goto :eof
set "TIMESTAMP=%date% %time%"
echo [%TIMESTAMP%] [ERROR] %~1 >> "%ERROR_LOG%" 2>nul
echo [%TIMESTAMP%] [ERROR] %~1 >> "%INFO_LOG%" 2>nul
REM Không hiển thị error nữa vì đã cảnh báo ở đầu
goto :eof
