#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tạm thời để cleanup các lệnh algo trùng lặp
Sau khi chạy xong, có thể xóa file này
"""

import ccxt
import cst
import requests
import hmac
import hashlib
import urllib.parse
import time
from datetime import datetime

print("=" * 60)
print("🧹 CLEANUP DUPLICATE ALGO ORDERS")
print("=" * 60)

# Khởi tạo exchange
exchange = ccxt.binance({
    'enableRateLimit': True,
    'apiKey': cst.key_binance,
    'secret': cst.secret_binance,
    'options': {'defaultType': 'future'}
})

def call_binance_api_direct(method, endpoint, params=None):
    """Gọi Binance API trực tiếp"""
    base_url = 'https://fapi.binance.com'
    url = f"{base_url}{endpoint}"
    
    if params is None:
        params = {}
    
    params['timestamp'] = int(time.time() * 1000)
    params['recvWindow'] = 60000
    
    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(
        cst.secret_binance.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    params['signature'] = signature
    
    headers = {
        'X-MBX-APIKEY': cst.key_binance
    }
    
    if method == 'GET':
        response = requests.get(url, params=params, headers=headers)
    elif method == 'DELETE':
        response = requests.delete(url, params=params, headers=headers)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ API Error: {response.status_code} - {response.text}")
        return None

def get_algo_orders_for_symbol(symbol):
    """Lấy tất cả algo orders cho symbol"""
    params = {'symbol': symbol.replace('/', '').replace(':USDT', '')}
    return call_binance_api_direct('GET', '/fapi/v1/allAlgoOrders', params)

def cancel_algo_order(symbol, algo_id):
    """Hủy algo order theo algoId"""
    params = {
        'symbol': symbol.replace('/', '').replace(':USDT', ''),
        'algoId': algo_id
    }
    return call_binance_api_direct('DELETE', '/fapi/v1/allAlgoOrders', params)

# Danh sách symbols cần cleanup (theo log)
SYMBOLS_TO_CHECK = [
    'DUSK/USDT:USDT',
    'HOME/USDT:USDT'
]

print(f"\n📋 Kiểm tra {len(SYMBOLS_TO_CHECK)} symbols có lệnh trùng lặp...\n")

for symbol in SYMBOLS_TO_CHECK:
    print(f"🔍 Kiểm tra {symbol}...")
    
    algo_orders = get_algo_orders_for_symbol(symbol)
    
    if not algo_orders:
        print(f"   ✅ Không có algo orders\n")
        continue
    
    # Lọc lệnh TRAILING_STOP với status=NEW
    active_trailing_stops = []
    for order in algo_orders:
        algo_type = order.get('algoType', '').upper()
        algo_status = order.get('algoStatus', '').upper()
        
        if algo_type in ['CONDITIONAL', 'VP'] and algo_status == 'NEW':
            active_trailing_stops.append(order)
    
    if len(active_trailing_stops) <= 1:
        print(f"   ✅ Chỉ có {len(active_trailing_stops)} lệnh active (OK)\n")
        continue
    
    # Có nhiều hơn 1 lệnh → Cleanup
    print(f"   ⚠️  Phát hiện {len(active_trailing_stops)} lệnh TRAILING_STOP active!")
    print(f"   📝 Danh sách:")
    
    for i, order in enumerate(active_trailing_stops, 1):
        algo_id = order.get('algoId')
        create_time = order.get('createTime', 0)
        create_time_str = datetime.fromtimestamp(create_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
        activation = order.get('activatePrice')
        callback = order.get('callbackRate')
        
        print(f"      {i}. AlgoId: {algo_id}")
        print(f"         Created: {create_time_str}")
        print(f"         Activation: {activation}, Callback: {callback}%")
    
    # Giữ lệnh MỚI NHẤT (createTime lớn nhất), xóa các lệnh cũ hơn
    active_trailing_stops.sort(key=lambda x: x.get('createTime', 0), reverse=True)
    
    keep_order = active_trailing_stops[0]
    delete_orders = active_trailing_stops[1:]
    
    print(f"\n   🔒 GIỮ LẠI: AlgoId {keep_order['algoId']} (Lệnh mới nhất)")
    print(f"   🗑️  XÓA: {len(delete_orders)} lệnh cũ hơn")
    
    # Confirm trước khi xóa
    confirm = input(f"\n   ❓ Bạn có chắc muốn xóa {len(delete_orders)} lệnh cũ không? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        for order in delete_orders:
            algo_id = order['algoId']
            print(f"      🗑️  Đang xóa AlgoId {algo_id}...", end=" ", flush=True)
            
            result = cancel_algo_order(symbol, algo_id)
            
            if result:
                print("✅ Thành công")
            else:
                print("❌ Thất bại")
        
        print(f"\n   ✅ Hoàn tất cleanup cho {symbol}\n")
    else:
        print(f"   ⏭️  Bỏ qua cleanup cho {symbol}\n")

print("=" * 60)
print("✅ HOÀN TẤT CLEANUP")
print("=" * 60)
print("\n💡 Nếu đã cleanup xong, có thể xóa file này (cleanup_duplicate_orders.py)")

