#!/usr/bin/env python3
"""
Build một module duy nhất để test
Usage: python3 build_one_module.py hd_order.py
"""

import sys
import subprocess
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python3 build_one_module.py <module_name>")
    print("Example: python3 build_one_module.py check_status.py")
    sys.exit(1)

module_name = sys.argv[1]

if not Path(module_name).exists():
    print(f"❌ File not found: {module_name}")
    sys.exit(1)

print("=" * 60)
print(f"Building: {module_name}")
print("=" * 60)

# Check PyInstaller
try:
    import PyInstaller
    print(f"✅ PyInstaller: {PyInstaller.__version__}")
except ImportError:
    print("❌ PyInstaller not found!")
    print("Install: python3 -m pip install pyinstaller")
    sys.exit(1)

# Build command
cmd = [
    'python3', '-m', 'PyInstaller',
    '--onefile',
    '--console',
    '--name', module_name.replace('.py', ''),
    '--hidden-import', 'cst',
    '--hidden-import', 'gg_sheet_factory',
    '--hidden-import', 'telegram_factory',
    '--hidden-import', 'binance_utils',
    '--hidden-import', 'utils',
    module_name
]

print(f"\nCommand: {' '.join(cmd)}\n")
sys.stdout.flush()

try:
    result = subprocess.run(cmd, check=False)
    
    if result.returncode == 0:
        print(f"\n✅ {module_name} built successfully!")
        print(f"📁 Output: dist/{module_name.replace('.py', '')}")
    else:
        print(f"\n❌ Build failed with exit code: {result.returncode}")
        sys.exit(1)
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
