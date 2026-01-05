#!/bin/bash
# QBot - Build Windows Script (macOS/Linux)
# Sử dụng python3 thay vì python

echo "========================================"
echo "QBot - Building for Windows (macOS)"
echo "========================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found!"
    exit 1
fi

# Check PyInstaller
if ! python3 -m PyInstaller --version &> /dev/null; then
    echo "❌ PyInstaller not found!"
    echo "Run: ./install_dependencies.sh"
    exit 1
fi

# Run build script
python3 build_windows.py
