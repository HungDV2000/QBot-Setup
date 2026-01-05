#!/usr/bin/env python3
"""
QBot - Status Checker
Kiểm tra xem tất cả modules có đang chạy không
"""

import subprocess
import sys

# Required modules
REQUIRED_MODULES = [
    ("hd_order.py", "Entry Orders", "CRITICAL"),
    ("hd_order_123.py", "SL/TP Orders", "CRITICAL"),
    ("hd_update_all.py", "Market Data", "IMPORTANT"),
    ("hd_update_price.py", "Price Updates", "IMPORTANT"),
    ("hd_update_cho_va_khop.py", "Status Updates", "IMPORTANT"),
    ("hd_alert_possition_and_open_order.py", "Alerts", "NORMAL"),
    ("hd_cancel_orders_schedule.py", "Cancel Scheduler", "NORMAL"),
]

def check_process_running(module_name):
    """Check if a Python module is running"""
    try:
        # Linux/macOS
        if sys.platform != 'win32':
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            return module_name in result.stdout
        else:
            # Windows
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/V'],
                capture_output=True,
                text=True
            )
            return module_name in result.stdout
    except Exception as e:
        print(f"Error checking {module_name}: {e}")
        return False

def main():
    print("=" * 60)
    print("QBot - Status Check")
    print("=" * 60)
    print()
    
    all_running = True
    critical_running = True
    
    for module, description, priority in REQUIRED_MODULES:
        is_running = check_process_running(module)
        
        # Status icons
        if is_running:
            status = "✅ RUNNING"
            icon = "●"
        else:
            status = "❌ STOPPED"
            icon = "○"
            all_running = False
            if priority == "CRITICAL":
                critical_running = False
        
        # Priority color (for terminal)
        if priority == "CRITICAL":
            priority_str = f"🔴 {priority}"
        elif priority == "IMPORTANT":
            priority_str = f"🟡 {priority}"
        else:
            priority_str = f"🟢 {priority}"
        
        print(f"{icon} {status:15} | {priority_str:20} | {module:40} | {description}")
    
    print()
    print("=" * 60)
    
    # Summary
    if all_running:
        print("✅ All modules are running!")
        return 0
    elif critical_running:
        print("⚠️  Some modules are stopped, but CRITICAL modules are OK")
        return 1
    else:
        print("❌ CRITICAL modules are stopped! Bot may not be working!")
        return 2

if __name__ == "__main__":
    sys.exit(main())

