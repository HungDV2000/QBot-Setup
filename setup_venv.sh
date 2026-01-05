#!/bin/bash
# Script tự động setup virtual environment cho project

echo "=========================================="
echo "  Setup Virtual Environment"
echo "=========================================="

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 không tìm thấy!"
    exit 1
fi

echo "✓ Python version: $(python3 --version)"

# Tạo venv
echo ""
echo "🔹 Tạo virtual environment..."
python3 -m venv venv

if [ ! -d "venv" ]; then
    echo "❌ Không thể tạo venv!"
    exit 1
fi

echo "✓ Virtual environment đã được tạo"

# Activate venv
echo ""
echo "🔹 Activate virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "🔹 Upgrade pip..."
pip install --upgrade pip --quiet

# Cài đặt packages
echo ""
echo "🔹 Cài đặt packages..."

packages=(
    "google-auth"
    "google-auth-oauthlib"
    "google-api-python-client"
    "python-telegram-bot"
    "ccxt"
    "pandas"
    "numpy"
    "aiohttp"
    "requests"
    "pyinstaller"
    "uncompyle6"
)

for package in "${packages[@]}"; do
    echo "  Installing $package..."
    pip install "$package" --quiet
done

# Tạo requirements.txt
echo ""
echo "🔹 Tạo requirements.txt..."
pip freeze > requirements.txt
echo "✓ requirements.txt đã được tạo"

# Summary
echo ""
echo "=========================================="
echo "  ✅ Setup hoàn tất!"
echo "=========================================="
echo ""
echo "Để activate virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "Để deactivate:"
echo "  deactivate"
echo ""
