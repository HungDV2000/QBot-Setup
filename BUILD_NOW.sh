#!/bin/bash
# Quick Build Script - Run this to build immediately!

clear
echo "================================================================================"
echo "                    🤖 QBOT - QUICK BUILD SCRIPT"
echo "================================================================================"
echo ""
echo "Đây là script để build nhanh tất cả modules thành file .exe cho Windows"
echo ""
echo "Script này sẽ:"
echo "  1. Kiểm tra Python và PyInstaller"
echo "  2. Chạy build_simple.py để build tất cả modules"
echo "  3. Hiển thị kết quả"
echo ""
echo "Thời gian: ~5-10 phút"
echo ""
read -p "Nhấn ENTER để bắt đầu, hoặc Ctrl+C để hủy..."

cd "$(dirname "$0")"

# Check Python
echo ""
echo "🔍 Kiểm tra Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 không được cài đặt!"
    echo "Vui lòng cài Python 3.9+ từ: https://www.python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION"

# Check PyInstaller
echo ""
echo "🔍 Kiểm tra PyInstaller..."
if ! python3 -m PyInstaller --version &> /dev/null; then
    echo "⚠️  PyInstaller chưa được cài đặt!"
    echo ""
    read -p "Bạn có muốn cài PyInstaller ngay bây giờ? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 Đang cài PyInstaller..."
        python3 -m pip install pyinstaller
        if [ $? -eq 0 ]; then
            echo "✅ PyInstaller đã được cài đặt!"
        else
            echo "❌ Không thể cài PyInstaller! Vui lòng cài thủ công."
            exit 1
        fi
    else
        echo "❌ Cần PyInstaller để build. Thoát..."
        exit 1
    fi
else
    PYINSTALLER_VERSION=$(python3 -m PyInstaller --version 2>&1 | head -1)
    echo "✅ PyInstaller: $PYINSTALLER_VERSION"
fi

# Run build
echo ""
echo "================================================================================"
echo "                    🔨 BẮT ĐẦU BUILD"
echo "================================================================================"
echo ""
echo "Đang build tất cả modules..."
echo "Vui lòng đợi 5-10 phút..."
echo ""

python3 build_simple.py

BUILD_STATUS=$?

echo ""
echo "================================================================================"
if [ $BUILD_STATUS -eq 0 ]; then
    echo "                    ✅ BUILD HOÀN TẤT!"
    echo "================================================================================"
    echo ""
    echo "📦 Kết quả build:"
    if [ -d "dist_windows" ]; then
        ls -lh dist_windows/
        echo ""
        FILE_COUNT=$(ls -1 dist_windows/ | wc -l | tr -d ' ')
        echo "✅ Đã tạo $FILE_COUNT files trong dist_windows/"
        echo ""
        echo "📋 Bước tiếp theo:"
        echo "   1. Copy folder dist_windows sang máy Windows"
        echo "   2. Đọc file README.txt trong folder"
        echo "   3. Cấu hình config.ini"
        echo "   4. Chạy start_all_bots.bat"
    else
        echo "⚠️  Folder dist_windows không được tạo."
        echo "Vui lòng kiểm tra log ở trên để xem lỗi."
    fi
else
    echo "                    ❌ BUILD THẤT BẠI"
    echo "================================================================================"
    echo ""
    echo "Vui lòng:"
    echo "  1. Kiểm tra error messages ở trên"
    echo "  2. Đọc file BUILD_GUIDE_VIETNAMESE.md để được hướng dẫn"
    echo "  3. Hoặc build từng module để test: python3 build_one_module.py check_status.py"
fi

echo ""
echo "================================================================================"
echo ""
