#!/bin/bash
# QBot - Install Build Dependencies
# Chạy script này trước khi build

echo "========================================"
echo "  QBot - Cài Đặt Dependencies"
echo "========================================"
echo ""

# Check Python
echo "🔍 Kiểm tra Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 không được cài đặt!"
    echo "Vui lòng cài Python 3.9+ từ: https://www.python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION"
echo ""

# Install PyInstaller
echo "📦 Cài đặt PyInstaller..."
python3 -m pip install --upgrade pyinstaller

# Install other build dependencies
echo ""
echo "📦 Cài đặt các dependencies khác..."
python3 -m pip install --upgrade pip setuptools wheel

# Install project dependencies (nếu có requirements.txt)
if [ -f "requirements.txt" ]; then
    echo ""
    echo "📦 Cài đặt project dependencies..."
    python3 -m pip install -r requirements.txt
fi

echo ""
echo "========================================"
echo "  ✅ Cài đặt hoàn tất!"
echo "========================================"
echo ""
echo "Bước tiếp theo:"
echo "  python3 build_windows.py"
echo ""
