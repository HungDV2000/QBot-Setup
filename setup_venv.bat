@echo off
REM Script tự động setup virtual environment cho project (Windows)

echo ==========================================
echo   Setup Virtual Environment
echo ==========================================

REM Kiểm tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python không tìm thấy!
    pause
    exit /b 1
)

echo ✓ Python version:
python --version

REM Tạo venv
echo.
echo 🔹 Tạo virtual environment...
python -m venv venv

if not exist "venv" (
    echo ❌ Không thể tạo venv!
    pause
    exit /b 1
)

echo ✓ Virtual environment đã được tạo

REM Activate venv
echo.
echo 🔹 Activate virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo 🔹 Upgrade pip...
python -m pip install --upgrade pip --quiet

REM Cài đặt packages
echo.
echo 🔹 Cài đặt packages...

pip install google-auth --quiet
pip install google-auth-oauthlib --quiet
pip install google-api-python-client --quiet
pip install python-telegram-bot --quiet
pip install ccxt --quiet
pip install pandas --quiet
pip install numpy --quiet
pip install aiohttp --quiet
pip install requests --quiet
pip install pyinstaller --quiet
pip install uncompyle6 --quiet

REM Tạo requirements.txt
echo.
echo 🔹 Tạo requirements.txt...
pip freeze > requirements.txt
echo ✓ requirements.txt đã được tạo

REM Summary
echo.
echo ==========================================
echo   ✅ Setup hoàn tất!
echo ==========================================
echo.
echo Để activate virtual environment:
echo   venv\Scripts\activate
echo.
echo Để deactivate:
echo   deactivate
echo.

pause
