"""
Script debug để xem TẤT CẢ positions (bao gồm cả closed positions)
"""

import sys
import traceback
from pathlib import Path
from datetime import datetime

logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = logs_dir / f'debug_positions_{timestamp}.txt'

def log(message):
    print(message, flush=True)
    try:
        with open(log_filename, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    except:
        pass

log("=" * 80)
log("🐛 DEBUG: XEM TẤT CẢ POSITIONS (KỂ CẢ AMOUNT = 0)")
log("=" * 80)

try:
    import ccxt
    import configparser
    
    # Đọc config
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    
    api_key = config.get('global', 'key_binance')
    secret_key = config.get('global', 'secret_binance')
    
    # Kết nối
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': secret_key,
        'options': {'defaultType': 'future'},
        'timeout': 30000,
        'enableRateLimit': True
    })
    
    log("✅ Kết nối Binance thành công")
    log("")
    
    # Lấy ALL positions
    log("📊 Lấy ALL positions từ Binance...")
    all_positions = exchange.fetch_positions()
    
    log(f"✅ Tổng số: {len(all_positions)} positions")
    log("")
    
    # Lọc positions
    active_positions = []
    closed_positions = []
    
    for pos in all_positions:
        amt = float(pos.get('contracts', 0))
        if amt != 0:
            active_positions.append(pos)
        else:
            closed_positions.append(pos)
    
    log(f"📈 Active positions (amount != 0): {len(active_positions)}")
    log(f"📉 Closed positions (amount = 0): {len(closed_positions)}")
    log("")
    
    # Tìm HOME/USDT
    log("=" * 80)
    log("🔍 TÌM HOME/USDT...")
    log("=" * 80)
    
    found_home = False
    for pos in all_positions:
        if 'HOME' in pos['symbol'].upper():
            found_home = True
            symbol = pos['symbol']
            amt = float(pos.get('contracts', 0))
            entry_price = pos.get('entryPrice')
            
            log(f"✅ TÌM THẤY: {symbol}")
            log(f"   Amount: {amt}")
            log(f"   Entry Price: {entry_price}")
            log(f"   Status: {'ACTIVE' if amt != 0 else 'CLOSED'}")
            log(f"   Raw data: {pos}")
            log("")
    
    if not found_home:
        log("❌ KHÔNG TÌM THẤY HOME/USDT trong positions!")
        log("")
        log("💡 Có thể:")
        log("   1. Position đã đóng hoàn toàn (SL/TP đã chạm)")
        log("   2. Đóng thủ công")
        log("   3. Symbol format khác (kiểm tra list bên dưới)")
    
    log("")
    log("=" * 80)
    log("📋 DANH SÁCH TẤT CẢ ACTIVE POSITIONS")
    log("=" * 80)
    
    if not active_positions:
        log("⚠️  Không có position nào đang mở!")
    else:
        for idx, pos in enumerate(active_positions, 1):
            symbol = pos['symbol']
            amt = float(pos.get('contracts', 0))
            side = "LONG" if amt > 0 else "SHORT"
            entry = pos.get('entryPrice')
            
            log(f"{idx}. {symbol:<20} | {side:<5} | Amount: {amt:<15} | Entry: {entry}")
    
    log("")
    log("=" * 80)
    log("📋 MẪU 10 CLOSED POSITIONS ĐẦU TIÊN (Để tham khảo)")
    log("=" * 80)
    
    for idx, pos in enumerate(closed_positions[:10], 1):
        symbol = pos['symbol']
        entry = pos.get('entryPrice')
        log(f"{idx}. {symbol:<20} | Entry: {entry} | Amount: 0 (CLOSED)")
    
    if len(closed_positions) > 10:
        log(f"... và {len(closed_positions) - 10} closed positions khác")

except Exception as e:
    log("")
    log(f"❌ LỖI: {e}")
    log(traceback.format_exc())

log("")
log("=" * 80)
log(f"✅ Log đã lưu vào: {log_filename}")
log("=" * 80)
log("")

try:
    input("⏸️  Nhấn Enter để thoát...")
except:
    pass

