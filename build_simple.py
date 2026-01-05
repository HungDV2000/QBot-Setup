#!/usr/bin/env python3
"""
Simple Build Script - Build all modules to .exe
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

# Print with flush
def p(msg):
    print(msg)
    sys.stdout.flush()

p("="*60)
p("QBot - Simple Build Script")
p("="*60)

# Modules to build
MODULES = [
    "hd_order.py",
    "hd_order_123.py", 
    "hd_update_all.py",
    "hd_update_price.py",
    "hd_update_cho_va_khop.py",
    "hd_update_danhmuc.py",
    "hd_alert_possition_and_open_order.py",
    "hd_cancel_orders_schedule.py",
    "check_status.py",
]

# Check PyInstaller
p("\nChecking PyInstaller...")
try:
    result = subprocess.run([sys.executable, '-m', 'PyInstaller', '--version'], 
                          capture_output=True, text=True)
    p(f"PyInstaller: {result.stdout.strip()}")
except:
    p("ERROR: PyInstaller not found!")
    p("Install: python3 -m pip install pyinstaller")
    sys.exit(1)

# Clean
p("\nCleaning...")
for d in ['build', 'dist', '__pycache__']:
    if Path(d).exists():
        shutil.rmtree(d)
        p(f"  Removed {d}/")

for f in Path('.').glob('*.spec'):
    f.unlink()
    p(f"  Removed {f}")

# Build each module
p(f"\nBuilding {len(MODULES)} modules...")
success = 0

for i, mod in enumerate(MODULES, 1):
    if not Path(mod).exists():
        p(f"[{i}/{len(MODULES)}] SKIP: {mod} (not found)")
        continue
    
    p(f"\n[{i}/{len(MODULES)}] Building: {mod}")
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--console',
        '--name', mod.replace('.py', ''),
        '--clean',
        '--hidden-import', 'cst',
        '--hidden-import', 'utils',
        '--hidden-import', 'gg_sheet_factory',
        '--hidden-import', 'telegram_factory',
        '--hidden-import', 'binance_utils',
        '--hidden-import', 'google.auth.transport.requests',
        '--hidden-import', 'google.oauth2.credentials',
        '--hidden-import', 'ccxt',
        '--hidden-import', 'telegram',
        '--hidden-import', 'pandas',
        mod
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        p(f"  ✅ SUCCESS")
        success += 1
    else:
        p(f"  ❌ FAILED")
        if result.stderr:
            p(f"     {result.stderr[:200]}")

# Create dist_windows
p("\n" + "="*60)
p(f"Built {success}/{len(MODULES)} modules")

if success > 0:
    p("\nCreating dist_windows...")
    dist = Path('dist_windows')
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir()
    
    # Copy .exe files
    for f in Path('dist').glob('*'):
        if f.is_file():
            shutil.copy(f, dist / f.name)
            p(f"  Copied: {f.name}")
    
    # Copy config
    if Path('config.ini.example').exists():
        shutil.copy('config.ini.example', dist / 'config.ini.example')
        p("  Copied: config.ini.example")
    
    p(f"\n✅ DONE! Output: {dist.absolute()}")
else:
    p("\n❌ No modules built!")

p("="*60)
