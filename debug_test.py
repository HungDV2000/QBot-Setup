#!/usr/bin/env python3
import sys
import os

# Write to file to debug
with open('debug_output.txt', 'w') as f:
    f.write(f"Python version: {sys.version}\n")
    f.write(f"Python executable: {sys.executable}\n")
    f.write(f"Current directory: {os.getcwd()}\n")
    f.write(f"Script location: {__file__}\n\n")
    
    try:
        import PyInstaller
        f.write(f"PyInstaller version: {PyInstaller.__version__}\n")
        f.write("PyInstaller imported successfully!\n")
    except Exception as e:
        f.write(f"PyInstaller import ERROR: {e}\n")
    
    # Check if modules exist
    modules = ["hd_order.py", "check_status.py", "cst.py"]
    f.write("\nChecking modules:\n")
    for mod in modules:
        exists = os.path.exists(mod)
        f.write(f"  {mod}: {'EXISTS' if exists else 'NOT FOUND'}\n")
    
    f.write("\nDebug complete!\n")

print("Debug info written to debug_output.txt")
print("Run: cat debug_output.txt")
