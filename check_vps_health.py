#!/usr/bin/env python3
"""
Chạy trên TỪNG VPS để so sánh: python check_vps_health.py
In ra: thời gian máy, phiên bản file fix, test API algo cho 1-2 symbol.
"""
import hashlib
import json
import os
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

FILES_TO_CHECK = [
    'binance_futures_direct.py',
    'hd_order.py',
    'hd_order_123.py',
    'hd_update_cho_va_khop.py',
    'cst.py',
    'config.ini',
]


def file_fingerprint(path: Path) -> str:
    if not path.is_file():
        return 'MISSING'
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()[:12]


def main():
    print('=' * 60)
    print('QBOT VPS HEALTH CHECK')
    print('=' * 60)
    print(f'Host: {socket.gethostname()}')
    print(f'CWD:  {os.getcwd()}')
    print(f'Root: {ROOT}')
    local = datetime.now()
    utc = datetime.now(timezone.utc)
    print(f'Local time: {local.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'UTC time:   {utc.strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    print('--- File fingerprints (so sánh giữa các VPS) ---')
    for name in FILES_TO_CHECK:
        fp = file_fingerprint(ROOT / name)
        print(f'  {name:30} {fp}')
    print()

    try:
        import cst
        key_ok = bool(getattr(cst, 'key_binance', None))
        secret_ok = bool(getattr(cst, 'secret_binance', None))
        sheet_ok = bool(getattr(cst, 'spreadsheet_id', None))
        print('--- config.ini (cst) ---')
        print(f'  key_binance:    {"OK" if key_ok else "MISSING"}')
        print(f'  secret_binance: {"OK" if secret_ok else "MISSING"}')
        print(f'  spreadsheet_id: {"OK" if sheet_ok else "MISSING"}')
        print(f'  key_name:       {getattr(cst, "key_name", "?")}')
    except Exception as e:
        print(f'  Lỗi load cst: {e}')
        return 1
    print()

    try:
        from binance_futures_direct import fetch_algo_orders_for_symbol
        has_fix = True
    except ImportError as e:
        print(f'❌ Thiếu binance_futures_direct.py: {e}')
        print('   → VPS này CHƯA có bản fix 400 allAlgoOrders')
        has_fix = False

    if not has_fix or not key_ok:
        return 1

    test_symbols = ['BTC/USDT:USDT', 'BAS/USDT:USDT']
    print('--- Test algo API (openAlgo + allAlgo) ---')
    for sym in test_symbols:
        t0 = time.time()
        orders = fetch_algo_orders_for_symbol(sym, history_hours=24)
        dt = time.time() - t0
        if orders is None:
            status = 'API_LOI (None)'
        elif orders == []:
            status = 'OK — không có algo'
        else:
            status = f'OK — {len(orders)} order(s)'
        print(f'  {sym:20} {status}  ({dt:.2f}s)')
    print()
    print('Nếu fingerprint khác VPS đang chạy tốt → copy đủ file và restart bot.')
    print('Nếu BAS = API_LOI trên mọi VPS nhưng BTC OK → có thể do symbol; bản fix coi 400 là [].')
    return 0


if __name__ == '__main__':
    sys.exit(main())
