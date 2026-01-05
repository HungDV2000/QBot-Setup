@echo off
chcp 65001 >nul 2>&1
REM ============================================================================
REM QBot v2.1 - Google Sheets Authentication
REM Xác thực quyền truy cập Google Sheets API
REM ============================================================================

title QBot - Google Authentication

cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║              QBot v2.1 - Xác Thực Google Sheets API                    ║
echo ║              Google Sheets Authentication                              ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM ============================================================================
REM BƯỚC 1: KIỂM TRA PYTHON
REM ============================================================================
echo [1/4] Đang kiểm tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ LỖI: Python chưa được cài đặt!
    echo.
    echo 💡 Vui lòng chạy: 1_setup_install.bat trước
    echo.
    pause
    exit /b 1
)
echo ✅ Python đã sẵn sàng
echo.

REM ============================================================================
REM BƯỚC 2: KIỂM TRA CREDENTIALS.JSON
REM ============================================================================
echo [2/4] Đang kiểm tra credentials.json...
if not exist ../credentials.json (
    echo.
    echo ❌ THIẾU FILE: credentials.json
    echo.
    echo ═══════════════════════════════════════════════════════════════════════
    echo 📝 HƯỚNG DẪN LẤY FILE credentials.json:
    echo ═══════════════════════════════════════════════════════════════════════
    echo.
    echo    1️⃣  Truy cập: https://console.cloud.google.com/
    echo.
    echo    2️⃣  Tạo Project mới hoặc chọn Project có sẵn
    echo.
    echo    3️⃣  Vào "APIs & Services" → "Credentials"
    echo.
    echo    4️⃣  Click "CREATE CREDENTIALS" → "OAuth client ID"
    echo.
    echo    5️⃣  Application type: "Desktop app"
    echo.
    echo    6️⃣  Tải file JSON xuống và đổi tên thành "credentials.json"
    echo.
    echo    7️⃣  Copy file vào thư mục: %CD%\..
    echo.
    echo    8️⃣  Enable Google Sheets API:
    echo        - Vào "APIs & Services" → "Library"
    echo        - Tìm "Google Sheets API"
    echo        - Click "ENABLE"
    echo.
    echo ═══════════════════════════════════════════════════════════════════════
    echo.
    echo 💡 Sau khi có file credentials.json, chạy lại script này
    echo.
    pause
    exit /b 1
)
echo ✅ credentials.json tìm thấy
echo.

REM ============================================================================
REM BƯỚC 3: KIỂM TRA THƯ VIỆN GOOGLE
REM ============================================================================
echo [3/4] Đang kiểm tra thư viện Google...
python -c "import google.auth; import gspread" 2>nul
if errorlevel 1 (
    echo ❌ LỖI: Thư viện Google chưa được cài đặt!
    echo.
    echo 💡 Vui lòng chạy: 1_setup_install.bat để cài đặt thư viện
    echo.
    pause
    exit /b 1
)
echo ✅ Thư viện Google đã sẵn sàng
echo.

REM ============================================================================
REM BƯỚC 4: CHẠY AUTHENTICATION
REM ============================================================================
echo [4/4] Đang khởi động quá trình xác thực...
echo.
echo ═══════════════════════════════════════════════════════════════════════
echo 🔐 BƯỚC TIẾP THEO:
echo ═══════════════════════════════════════════════════════════════════════
echo.
echo    1. Trình duyệt sẽ tự động mở
echo    2. Đăng nhập bằng tài khoản Google của bạn
echo    3. Click "Allow" để cấp quyền truy cập Google Sheets
echo    4. Sau khi hoàn tất, đóng trình duyệt và quay lại đây
echo.
echo ═══════════════════════════════════════════════════════════════════════
echo.
pause

REM Chạy authentication Python script
cd ..
python auth_google.py
set AUTH_RESULT=%ERRORLEVEL%
cd setup

echo.
echo ═══════════════════════════════════════════════════════════════════════

if %AUTH_RESULT%==0 (
    echo.
    echo ╔════════════════════════════════════════════════════════════════════════╗
    echo ║                   XÁC THỰC THÀNH CÔNG!                                ║
    echo ╚════════════════════════════════════════════════════════════════════════╝
    echo.
    echo 📊 TRẠNG THÁI:
    echo.
    echo    ✅ credentials.json
    echo    ✅ token.json (đã tạo)
    echo    ✅ Kết nối Google Sheets API thành công
    echo.
    echo ═══════════════════════════════════════════════════════════════════════
    echo.
    echo 📝 CÁC BƯỚC TIẾP THEO:
    echo.
    echo    1️⃣  Mở file config.ini
    echo        Điền spreadsheet_id (ID của Google Sheet bạn muốn dùng)
    echo.
    echo    2️⃣  Chạy kiểm tra môi trường:
    echo        2_check_environment.bat
    echo.
    echo    3️⃣  Khởi động bot:
    echo        3_qbot_manager.bat
    echo.
    echo ═══════════════════════════════════════════════════════════════════════
) else (
    echo.
    echo ╔════════════════════════════════════════════════════════════════════════╗
    echo ║                     XÁC THỰC THẤT BẠI!                                ║
    echo ╚════════════════════════════════════════════════════════════════════════╝
    echo.
    echo ❌ Không thể xác thực với Google Sheets API
    echo.
    echo 💡 Vui lòng:
    echo    1. Kiểm tra lại credentials.json
    echo    2. Đảm bảo đã enable Google Sheets API
    echo    3. Kiểm tra OAuth consent screen
    echo    4. Chạy lại script này
    echo.
)

echo.
pause

REM Cleanup helper script (không cần nữa vì đã dùng file Python riêng)

exit /b %AUTH_RESULT%

