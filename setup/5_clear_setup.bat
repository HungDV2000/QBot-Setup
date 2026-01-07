@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
REM ============================================================================
REM QBot v2.1 - Clear Setup & Reset Environment with Logging
REM Xóa toàn bộ cài đặt trước đó để cài lại từ đầu
REM Log: clear_info.txt (thông tin), clear_error.txt (lỗi)
REM ============================================================================

title QBot - Clear Setup

REM ============================================================================
REM KHỞI TẠO LOGGING
REM ============================================================================
REM Tạo log files trong thư mục cha (qbot_setup/) giống install script
set "INFO_LOG=..\clear_info.txt"
set "ERROR_LOG=..\clear_error.txt"

REM Clear log files với fallback
echo. > "%INFO_LOG%" 2>nul
if errorlevel 1 (
    set "INFO_LOG=clear_info.txt"
    set "ERROR_LOG=clear_error.txt"
    echo. > "%INFO_LOG%"
) else (
    echo. > "%ERROR_LOG%" 2>nul
)

REM Helper function để ghi log với timestamp
call :LogInfo "=========================================="
call :LogInfo "QBot v2.1 - Clear Setup Started"
call :LogInfo "=========================================="

cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                   QBot v2.1 - DỌN DẸP CÀI ĐẶT                         ║
echo ║                   Clear Setup ^& Reset                                  ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM ============================================================================
REM CẢNH BÁO
REM ============================================================================
echo ⚠️  CẢNH BÁO: Script này sẽ XÓA:
echo.
echo    ❌ Tất cả thư viện Python trong requirements.txt
echo    ❌ Virtual environment (nếu có)
echo    ❌ File config.ini (sẽ backup trước)
echo    ❌ Cache files (__pycache__, *.pyc)
echo    ❌ Temp files
echo.
echo ⚠️  TÙY CHỌN XÓA (sẽ hỏi sau):
echo.
echo    ❓ Python
echo    ❓ Log files
echo    ❓ Config backup files
echo.
echo ✅ KHÔNG XÓA:
echo.
echo    ✅ Source code (.py files)
echo    ✅ credentials.json (giữ nguyên)
echo.
echo ═══════════════════════════════════════════════════════════════════════
echo.

set /p CONFIRM="   Bạn có CHẮC CHẮN muốn xóa tất cả? Gõ 'YES' để xác nhận: "

if /i not "%CONFIRM%"=="YES" (
    call :LogInfo "User cancelled clear setup"
    echo.
    echo ❌ Đã hủy! Không có gì bị xóa.
    echo.
    pause
    exit /b 0
)

call :LogInfo "User confirmed clear setup with YES"
echo.
set /p DELETE_PYTHON="   Bạn có muốn GỠ PYTHON khỏi máy không? (Y/N): "
call :LogInfo "Delete Python choice: !DELETE_PYTHON!"

echo.
echo ═══════════════════════════════════════════════════════════════════════
echo 🔄 BẮT ĐẦU DỌN DẸP...
echo ═══════════════════════════════════════════════════════════════════════
echo.

REM ============================================================================
REM BƯỚC 1: GỠ PYTHON (NẾU CHỌN)
REM ============================================================================
if /i "!DELETE_PYTHON!"=="Y" (
    echo [1/8] Đang gỡ cài đặt Python...
    call :LogInfo "[STEP 1/8] Uninstalling Python (user chose Y)"
    echo.
    
    python --version >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
        call :LogInfo "Python version found: %PYTHON_VERSION%"
        echo    ⚠️  CẢNH BÁO: Đang gỡ Python khỏi máy...
        echo    💡 Quá trình này có thể mất 1-2 phút
        echo.
        
        REM Thử gỡ qua winget trước
        winget --version >nul 2>&1
        if not errorlevel 1 (
            call :LogInfo "Trying Method 1: Winget uninstall"
            echo    🔄 Đang gỡ Python qua Winget...
            winget uninstall Python.Python.3.11 --silent >nul 2>&1
            if not errorlevel 1 (
                call :LogInfo "Python uninstalled successfully via Winget"
                echo    ✅ Đã gỡ Python qua Winget
            ) else (
                call :LogError "Winget uninstall failed"
                echo    ⚠️  Không thể gỡ qua Winget, thử phương pháp khác...
                goto :UninstallPythonManual
            )
        ) else (
            call :LogInfo "Winget not available"
            :UninstallPythonManual
            call :LogInfo "Trying Method 2: MsiExec uninstall"
            echo    🔄 Đang gỡ Python qua Windows Programs...
            
            REM Gỡ Python qua Windows Installer (MsiExec)
            REM Tìm Python 3.11 trong registry
            for /f "tokens=*" %%a in ('wmic product where "name like 'Python 3.11%%'" get IdentifyingNumber /value 2^>nul ^| findstr "IdentifyingNumber"') do (
                set "PYTHON_GUID=%%a"
                set "PYTHON_GUID=!PYTHON_GUID:IdentifyingNumber=!"
                set "PYTHON_GUID=!PYTHON_GUID:~1!"
                
                call :LogInfo "Found Python GUID: !PYTHON_GUID!"
                echo    🗑️  Đang gỡ Python với GUID: !PYTHON_GUID!
                msiexec /x !PYTHON_GUID! /qn
                
                if not errorlevel 1 (
                    call :LogInfo "Python uninstalled successfully via MsiExec"
                    echo    ✅ Đã gỡ Python thành công
                ) else (
                    call :LogError "MsiExec uninstall failed"
                    echo    ⚠️  Gỡ Python thất bại
                    echo    💡 Vui lòng gỡ thủ công qua Control Panel:
                    echo       Settings → Apps → Python 3.11 → Uninstall
                )
            )
        )
        
        echo.
        echo    💡 Lưu ý: Bạn có thể cần khởi động lại máy để hoàn tất việc gỡ Python
        echo.
    ) else (
        call :LogInfo "Python not found, skipping uninstall"
        echo    ℹ️  Python không có sẵn, bỏ qua
    )
) else (
    echo [1/8] Bỏ qua gỡ Python (giữ nguyên)
    call :LogInfo "[STEP 1/8] Skipping Python uninstall (user chose N)"
    echo    ✅ Python được giữ lại trên máy
)

echo.

REM ============================================================================
REM BƯỚC 2: BACKUP CONFIG.INI
REM ============================================================================
echo [2/8] Backup config.ini...
call :LogInfo "[STEP 2/8] Backing up config.ini"

if exist ../config.ini (
    set BACKUP_NAME=config.backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.ini
    set BACKUP_NAME=!BACKUP_NAME: =0!
    copy ../config.ini "../!BACKUP_NAME!" >nul 2>&1
    if not errorlevel 1 (
        call :LogInfo "config.ini backed up as: !BACKUP_NAME!"
        echo    ✅ Đã backup: !BACKUP_NAME!
    ) else (
        call :LogError "Failed to backup config.ini"
        echo    ⚠️  Không thể backup config.ini
    )
) else (
    call :LogInfo "config.ini not found, skipping backup"
    echo    ℹ️  config.ini không tồn tại, bỏ qua
)

echo.

REM ============================================================================
REM BƯỚC 3: GỠ CÀI ĐẶT THƯ VIỆN PYTHON
REM ============================================================================
echo [3/8] Đang gỡ cài đặt thư viện Python...
call :LogInfo "[STEP 3/8] Uninstalling Python libraries from requirements.txt"

python --version >nul 2>&1
if not errorlevel 1 (
    if exist ../requirements.txt (
        echo    🔄 Đang gỡ các packages từ requirements.txt...
        echo.
        
        REM Đọc từng dòng từ requirements.txt và uninstall
        for /f "usebackq tokens=1 delims==" %%p in ("../requirements.txt") do (
            set "LINE=%%p"
            REM Bỏ qua dòng comment (bắt đầu bằng #) và dòng trống
            if not "!LINE!"=="" (
                echo !LINE! | findstr /r "^#" >nul 2>&1
                if errorlevel 1 (
                    REM Không phải comment, xóa package
                    echo       Gỡ: %%p...
                    call :LogInfo "Uninstalling package: %%p"
                    python -m pip uninstall %%p -y >nul 2>&1
                )
            )
        )
        
        call :LogInfo "Packages from requirements.txt uninstalled"
        echo.
        echo    ✅ Đã gỡ các thư viện từ requirements.txt
    ) else (
        call :LogError "requirements.txt not found"
        echo    ⚠️  requirements.txt không tồn tại
    )
) else (
    call :LogInfo "Python not available, skipping library uninstall"
    echo    ℹ️  Python không có sẵn, bỏ qua
)

echo.

REM ============================================================================
REM BƯỚC 4: XÓA VIRTUAL ENVIRONMENT
REM ============================================================================
echo [4/8] Đang xóa virtual environment...
call :LogInfo "[STEP 4/8] Removing virtual environment"

if exist ../venv (
    call :LogInfo "venv folder found, removing..."
    echo    🗑️  Đang xóa folder venv...
    rmdir /s /q ../venv 2>nul
    if not exist ../venv (
        call :LogInfo "venv removed successfully"
        echo    ✅ Đã xóa venv
    ) else (
        call :LogError "Failed to remove venv (may be in use)"
        echo    ⚠️  Không thể xóa venv (có thể đang được sử dụng)
    )
) else (
    call :LogInfo "venv not found, skipping"
    echo    ℹ️  venv không tồn tại, bỏ qua
)

echo.

REM ============================================================================
REM BƯỚC 5: XÓA CONFIG.INI
REM ============================================================================
echo [5/8] Đang xóa config.ini...
call :LogInfo "[STEP 5/8] Removing config.ini"

if exist ../config.ini (
    call :LogInfo "config.ini found, removing..."
    del ../config.ini >nul 2>&1
    if not exist ../config.ini (
        call :LogInfo "config.ini removed successfully"
        echo    ✅ Đã xóa config.ini
    ) else (
        call :LogError "Failed to remove config.ini"
        echo    ⚠️  Không thể xóa config.ini
    )
) else (
    call :LogInfo "config.ini already removed or not found"
    echo    ℹ️  config.ini đã được xóa hoặc không tồn tại
)

echo.

REM ============================================================================
REM BƯỚC 6: XÓA CACHE VÀ TEMP FILES
REM ============================================================================
echo [6/8] Đang xóa cache và temp files...
call :LogInfo "[STEP 6/8] Removing cache and temp files"

REM Xóa __pycache__
set PYCACHE_COUNT=0
for /d /r .. %%d in (__pycache__) do @if exist "%%d" (
    echo    🗑️  Xóa: %%d
    call :LogInfo "Removing __pycache__: %%d"
    rmdir /s /q "%%d" 2>nul
    set /a PYCACHE_COUNT+=1
)
call :LogInfo "Removed !PYCACHE_COUNT! __pycache__ folders"

REM Xóa .pyc files
echo    🗑️  Đang xóa *.pyc files...
call :LogInfo "Removing .pyc files"
del /s /q ..\.pyc >nul 2>&1

REM Xóa .pyo files
call :LogInfo "Removing .pyo files"
del /s /q ..\.pyo >nul 2>&1

REM Xóa temp files từ bot operations
call :LogInfo "Removing temp files"
if exist ../_check_libs.py (
    del ../_check_libs.py >nul 2>&1
    call :LogInfo "Removed _check_libs.py"
)
if exist ../_bot_status.tmp (
    del ../_bot_status.tmp >nul 2>&1
    call :LogInfo "Removed _bot_status.tmp"
)
if exist ../_running_pids.tmp (
    del ../_running_pids.tmp >nul 2>&1
    call :LogInfo "Removed _running_pids.tmp"
)

REM Xóa temp files từ install script
echo    🗑️  Đang xóa temp files từ install script...
call :LogInfo "Removing install script temp files"
if exist pip_install.tmp (
    del pip_install.tmp >nul 2>&1
    call :LogInfo "Removed pip_install.tmp"
)
if exist download_error.tmp (
    del download_error.tmp >nul 2>&1
    call :LogInfo "Removed download_error.tmp"
)

REM Xóa setup log files từ install script (cả 2 vị trí)
echo    🗑️  Đang xóa setup log files...
call :LogInfo "Removing setup log files"
if exist ..\setup_info.txt (
    del ..\setup_info.txt >nul 2>&1
    call :LogInfo "Removed ..\setup_info.txt"
)
if exist ..\setup_error.txt (
    del ..\setup_error.txt >nul 2>&1
    call :LogInfo "Removed ..\setup_error.txt"
)
if exist setup_info.txt (
    del setup_info.txt >nul 2>&1
    call :LogInfo "Removed setup\setup_info.txt"
)
if exist setup_error.txt (
    del setup_error.txt >nul 2>&1
    call :LogInfo "Removed setup\setup_error.txt"
)

REM Xóa config template (nếu có)
if exist ..\config.template.ini (
    del ..\config.template.ini >nul 2>&1
    call :LogInfo "Removed config.template.ini"
)

REM Xóa Python installer (cả 2 vị trí: parent và setup)
echo    🗑️  Đang xóa Python installers...
call :LogInfo "Removing Python installers"
for %%f in (../python-*.exe) do (
    if exist "%%f" (
        del "%%f" >nul 2>&1
        call :LogInfo "Removed Python installer: %%f"
    )
)
for %%f in (python-*.exe) do (
    if exist "%%f" (
        del "%%f" >nul 2>&1
        call :LogInfo "Removed Python installer in setup: %%f"
    )
)

call :LogInfo "Cache and temp files cleanup completed"
echo    ✅ Đã xóa cache và temp files

echo.

REM ============================================================================
REM BƯỚC 7: XÓA LOG FILES
REM ============================================================================
echo [7/8] Đang xóa log files...
call :LogInfo "[STEP 7/8] Removing log files"

set /p DELETE_LOGS="   Bạn có muốn XÓA TẤT CẢ FILE LOG không? (Y/N): "
call :LogInfo "Delete logs choice: %DELETE_LOGS%"

if /i "!DELETE_LOGS!"=="Y" (
    call :LogInfo "User chose to delete log files"
    echo    🗑️  Đang xóa log files...
    
    REM Count log files
    set LOG_COUNT=0
    for %%f in (../*.log) do set /a LOG_COUNT+=1
    call :LogInfo "Found !LOG_COUNT! log files in root"
    
    REM Xóa log files trong folder gốc
    del ../*.log >nul 2>&1
    
    REM Xóa log files trong folder logs
    if exist ../logs (
        call :LogInfo "Removing log files from logs folder"
        del /s /q ../logs/*.log >nul 2>&1
    )
    
    call :LogInfo "All log files removed"
    echo    ✅ Đã xóa tất cả log files
) else (
    call :LogInfo "User chose to keep log files"
    echo    ℹ️  Bỏ qua xóa log files
)

echo.

REM ============================================================================
REM BƯỚC 8: XÓA CONFIG BACKUP FILES (TÙY CHỌN)
REM ============================================================================
echo [8/8] Đang kiểm tra config backup files...
call :LogInfo "[STEP 8/8] Checking config backup files"

REM Count backup files
set BACKUP_COUNT=0
for %%f in (../config.backup_*.ini) do (
    if exist "%%f" set /a BACKUP_COUNT+=1
)

if !BACKUP_COUNT! GTR 0 (
    echo    📦 Tìm thấy !BACKUP_COUNT! file(s) backup config
    echo.
    set /p DELETE_BACKUPS="   Bạn có muốn XÓA CÁC FILE BACKUP CŨ không? (Y/N): "
    call :LogInfo "Delete backups choice: !DELETE_BACKUPS!"
    
    if /i "!DELETE_BACKUPS!"=="Y" (
        call :LogInfo "User chose to delete backup files"
        echo    🗑️  Đang xóa backup files...
        
        for %%f in (../config.backup_*.ini) do (
            if exist "%%f" (
                echo       Xóa: %%~nxf
                del "%%f" >nul 2>&1
                call :LogInfo "Removed backup: %%f"
            )
        )
        
        call :LogInfo "All backup files removed"
        echo    ✅ Đã xóa tất cả backup files
    ) else (
        call :LogInfo "User chose to keep backup files"
        echo    ℹ️  Giữ lại các file backup
    )
) else (
    call :LogInfo "No backup files found"
    echo    ℹ️  Không có file backup nào
)

echo.

REM ============================================================================
REM TÓM TẮT
REM ============================================================================
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                        DỌN DẸP HOÀN TẤT!                              ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

call :LogInfo "Clear setup completed successfully"
call :LogInfo "Summary:"
if /i "!DELETE_PYTHON!"=="Y" (
    call :LogInfo "- Python: UNINSTALLED"
) else (
    call :LogInfo "- Python: KEPT"
)
if not "!BACKUP_NAME!"=="" (
    call :LogInfo "- Config backup: !BACKUP_NAME!"
)
call :LogInfo "- Python libraries: requirements.txt UNINSTALLED"
call :LogInfo "- Virtual environment: REMOVED"
call :LogInfo "- config.ini: REMOVED"
call :LogInfo "- config.template.ini: REMOVED"
call :LogInfo "- Cache files: REMOVED"
call :LogInfo "- Setup log files: REMOVED"
call :LogInfo "- Temp files: REMOVED"
if /i "!DELETE_LOGS!"=="Y" (
    call :LogInfo "- Bot log files: REMOVED"
) else (
    call :LogInfo "- Bot log files: KEPT"
)
if !BACKUP_COUNT! GTR 0 (
    if /i "!DELETE_BACKUPS!"=="Y" (
        call :LogInfo "- Config backup files: REMOVED"
    ) else (
        call :LogInfo "- Config backup files: KEPT"
    )
)
call :LogInfo "=========================================="
call :LogInfo "QBot v2.1 - Clear Setup Completed"
call :LogInfo "=========================================="

echo 📊 ĐÃ THỰC HIỆN:
echo.
if /i "!DELETE_PYTHON!"=="Y" (
    echo    ✅ Gỡ cài đặt Python
) else (
    echo    ℹ️  Giữ nguyên Python
)
if not "!BACKUP_NAME!"=="" (
    echo    ✅ Backup config.ini: !BACKUP_NAME!
)
echo    ✅ Gỡ cài đặt thư viện từ requirements.txt
echo    ✅ Xóa virtual environment
echo    ✅ Xóa config.ini
echo    ✅ Xóa config.template.ini
echo    ✅ Xóa cache và temp files
echo    ✅ Xóa setup log files (setup_info.txt, setup_error.txt)
echo    ✅ Xóa Python installers
if /i "!DELETE_LOGS!"=="Y" (
    echo    ✅ Xóa bot log files
) else (
    echo    ℹ️  Giữ nguyên bot log files
)
if !BACKUP_COUNT! GTR 0 (
    if /i "!DELETE_BACKUPS!"=="Y" (
        echo    ✅ Xóa !BACKUP_COUNT! config backup file(s)
    ) else (
        echo    ℹ️  Giữ lại !BACKUP_COUNT! config backup file(s)
    )
)
echo.
echo ═══════════════════════════════════════════════════════════════════════
echo.
echo 📝 CÁC BƯỚC TIẾP THEO:
echo.
echo    1️⃣  CÀI ĐẶT LẠI TỪ ĐẦU
echo.
echo       📌 Chạy file: 1_setup_install.bat
echo       📌 Làm theo hướng dẫn
echo.
if not "!BACKUP_NAME!"=="" (
    echo    2️⃣  KHÔI PHỤC CONFIG (NẾU CẦN)
    echo.
    echo       📌 File backup: !BACKUP_NAME!
    echo       📌 Đổi tên thành: config.ini
    echo.
)
echo ═══════════════════════════════════════════════════════════════════════
echo.
echo 💡 LƯU Ý:
echo.
if /i not "!DELETE_PYTHON!"=="Y" (
    echo    - Python vẫn còn trên máy (chưa bị xóa)
)
echo    - Source code (.py) vẫn còn nguyên
echo    - credentials.json vẫn còn nguyên (nếu có)
if /i "!DELETE_PYTHON!"=="Y" (
    echo    - ⚠️  Python đã bị gỡ - cần cài lại khi chạy setup
    echo    - 💡 Có thể cần khởi động lại máy
)
echo.
echo ═══════════════════════════════════════════════════════════════════════
echo.
echo 💡 TIP: Xem log chi tiết tại:
echo    • %INFO_LOG%
echo    • %ERROR_LOG%
echo.
echo 🧹 Dọn dẹp log files của clear script...

REM Cleanup own log files after user reads the summary
set /p CLEANUP_CLEAR_LOGS="👉 Bạn có muốn XÓA LOG FILES của clear script này không? (Y/N): "
if /i "!CLEANUP_CLEAR_LOGS!"=="Y" (
    echo.
    echo 🗑️  Đang xóa clear log files...
    REM Save log location before deleting
    set TEMP_INFO_LOG=!INFO_LOG!
    set TEMP_ERROR_LOG=!ERROR_LOG!
    
    if exist "!TEMP_INFO_LOG!" del "!TEMP_INFO_LOG!" >nul 2>&1
    if exist "!TEMP_ERROR_LOG!" del "!TEMP_ERROR_LOG!" >nul 2>&1
    
    echo ✅ Đã xóa clear_info.txt và clear_error.txt
    echo.
)

pause
exit /b 0

REM ============================================================================
REM HELPER FUNCTIONS
REM ============================================================================

:LogInfo
REM Log information with timestamp to clear_info.txt
set "TIMESTAMP=%date% %time%"
echo [%TIMESTAMP%] [INFO] %~1 >> "%INFO_LOG%"
goto :eof

:LogError
REM Log error with timestamp to clear_error.txt
set "TIMESTAMP=%date% %time%"
echo [%TIMESTAMP%] [ERROR] %~1 >> "%ERROR_LOG%"
echo [%TIMESTAMP%] [ERROR] %~1 >> "%INFO_LOG%"
goto :eof
