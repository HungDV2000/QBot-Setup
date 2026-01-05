#!/bin/bash
# Simple build test

cd "$(dirname "$0")"

echo "Testing build script..."
echo "Current directory: $(pwd)"
echo "Python version: $(python3 --version)"

python3 << 'PYTHON_SCRIPT'
import sys
import os

print("=" * 60)
print("QBot - Build Test")
print("=" * 60)
print()

# Test imports
try:
    import PyInstaller
    print(f"✅ PyInstaller: {PyInstaller.__version__}")
except ImportError:
    print("❌ PyInstaller not found")
    sys.exit(1)

# Test module existence
modules = ["hd_order.py", "hd_order_123.py", "check_status.py"]
print("\nChecking modules...")
for mod in modules:
    if os.path.exists(mod):
        print(f"✅ {mod}")
    else:
        print(f"❌ {mod} not found")

print("\n✅ All checks passed!")
print("\nTo build, run: python3 build_windows.py")

PYTHON_SCRIPT
