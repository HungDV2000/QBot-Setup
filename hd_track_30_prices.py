"""
Tracking 30 Price Levels - Module tracking 30 mức giá gần nhất (thực tế 19 giá do giới hạn cột)
Chạy mỗi 1 phút để cập nhật giá cho các mã có Leverage ≠ 0 và ≠ N (sẽ được bot đặt lệnh)

Logic:
- Quét sheet "ĐẶT LỆNH (100 MÃ)" hàng 4-53 (LONG) và 55-104 (SHORT)
- Chỉ track mã có cột B (Leverage) ≠ 0, ≠ "N"
- Lấy 19 mức giá gần nhất (nến 1m) từ Binance
- Ghi vào cột I:Z (18 cột) của cùng hàng với mã đó (H là Capital, bỏ qua)
  Nếu cần 19 giá, sẽ lấy tối đa 18 giá gần nhất
"""

import ccxt
from binance_futures_direct import resync_exchange_time  # [Fix1] chống clock drift -1021
import logging
import time
from datetime import datetime
from typing import Dict, List
import cst
import gg_sheet_factory
from data_collector import get_data_collector
import os
from pathlib import Path

file_name = os.path.basename(os.path.abspath(__file__))  
os.system(f"title {file_name} - {cst.key_name}")

# Tạo thư mục logs/ nếu chưa có
logs_dir = cst.account_dir('logs')  # [MULTI-ACC] tách theo tài khoản
logs_dir.mkdir(exist_ok=True)

# Tạo tên file log với timestamp: hd_track_30_prices_dd_mm_yyyy_H_M_S.txt
log_timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
log_filename = logs_dir / f'hd_track_30_prices_{log_timestamp}.txt'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# Tạo file handler với tên file động
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

# Setup exchange
exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'enableRateLimit': True,  
    'apiKey': cst.key_binance,
    'secret': cst.secret_binance,
    'options': {
        'defaultType': 'future',
        'fetchCurrencies': False,          # [A2] tránh gọi /sapi getall (signed) khi load_markets
        'adjustForTimeDifference': True,   # [A2] tự đồng bộ clock -> hết lỗi -1021
        'recvWindow': 60000,               # [A2+Fix2] nới cửa sổ timestamp lên max 60s
    }
})
exchange.setSandboxMode(False)

# Data collector
data_collector = get_data_collector(exchange)


class PriceTracker:
    """Tracking giá cho các mã đã đặt lệnh"""
    
    def __init__(self):
        self.tracked_symbols = {}  # {symbol: {'order_price': ..., 'filled_price': ..., 'prices': []}}
    
    def get_symbols_with_orders(self) -> List[Dict]:
        """
        Lấy danh sách các mã có Leverage ≠ 0 và ≠ N (theo quy trình đặt lệnh thực tế)
        
        Returns:
            List[Dict]: Danh sách với keys: symbol, leverage, activation_price
        """
        result = []
        
        try:
            # Khối DƯỚI = SHORT (dòng 55-104). A=Symbol, B=Leverage, D=Giá vào, H=Vốn
            # (row_num tính từ 55 nên số dòng vẫn đúng — chỉ đổi tên biến cho khỏi nhầm)
            short_block = gg_sheet_factory.get_dat_lenh("A55:H104")
            for idx, row in enumerate(short_block):
                if len(row) > 0 and row[0]:  # Có symbol
                    symbol = row[0]
                    leverage = row[1] if len(row) > 1 else ""  # Cột B: Leverage
                    
                    # Chỉ track nếu leverage ≠ 0, ≠ "N", và là số hợp lệ
                    # (Theo quy trình: B ≠ 0 và B ≠ "N" thì bot sẽ đặt lệnh)
                    if leverage and leverage != "N" and leverage != "0" and leverage != 0:
                        try:
                            lev_value = float(leverage)
                            if lev_value > 0:
                                activation = row[3] if len(row) > 3 else 0.0  # Cột D: Activation Price
                                result.append({
                                    'symbol': symbol,
                                    'leverage': lev_value,
                                    'activation_price': float(activation) if activation else 0.0,
                                    'row_num': 55 + idx
                                })
                        except (ValueError, TypeError):
                            # Nếu leverage không phải số, bỏ qua
                            pass
            
            # Khối TRÊN = LONG (dòng 4-53)
            long_block = gg_sheet_factory.get_dat_lenh("A4:H53")
            for idx, row in enumerate(long_block):
                if len(row) > 0 and row[0]:
                    symbol = row[0]
                    leverage = row[1] if len(row) > 1 else ""
                    
                    if leverage and leverage != "N" and leverage != "0" and leverage != 0:
                        try:
                            lev_value = float(leverage)
                            if lev_value > 0:
                                activation = row[3] if len(row) > 3 else 0.0
                                result.append({
                                    'symbol': symbol,
                                    'leverage': lev_value,
                                    'activation_price': float(activation) if activation else 0.0,
                                    'row_num': 4 + idx
                                })
                        except (ValueError, TypeError):
                            pass
            
            logger.info(f"Tìm thấy {len(result)} mã có leverage hợp lệ (sẽ đặt lệnh)")
            return result
            
        except Exception as e:
            logger.error(f"Lỗi lấy danh sách mã có lệnh: {e}")
            return []
    
    def track_prices(self):
        """Track và cập nhật 18 mức giá gần nhất cho các mã có leverage hợp lệ (cột I:Z, bỏ qua H)"""
        print(f"=== Bắt đầu tracking 18 prices - {datetime.now()} ===", flush=True)
        logger.info(f"=== Bắt đầu tracking 18 prices - {datetime.now()} ===")
        
        symbols_with_orders = self.get_symbols_with_orders()
        
        if not symbols_with_orders:
            print("⚠️ Không tìm thấy mã nào có leverage hợp lệ (B ≠ 0, B ≠ N)", flush=True)
            logger.info("Không tìm thấy mã nào có leverage hợp lệ")
            return
        
        for item in symbols_with_orders:
            symbol = item['symbol']
            row_num = item['row_num']
            leverage = item['leverage']
            
            try:
                print(f"📊 Tracking {symbol} (Hàng {row_num}, Leverage {leverage}x)...", flush=True)
                
                # Lấy 30 mức giá gần nhất
                price_data = data_collector.get_30_recent_prices(symbol)
                
                if price_data:
                    # Track giá từ cột I đến Z (18 cột), BỎ QUA cột H (Capital)
                    # I = price 1, J = price 2, ..., Z = price 18
                    # Vì cột H là Capital nên không được ghi đè
                    
                    prices_only = [p['price'] for p in price_data[-18:]]  # Lấy tối đa 18 giá gần nhất (I-Z = 18 cột)
                    
                    # Pad nếu không đủ 18
                    while len(prices_only) < 18:
                        prices_only.insert(0, "")
                    
                    # Update vào sheet (cột I:Z tương ứng 18 prices, bỏ qua H)
                    gg_sheet_factory.update_multi(
                        gg_sheet_factory.tab_dat_lenh,
                        row_num - 2,  # array_index = row_num - 2 (vì update_multi dùng index = 2 + array_index)
                        [prices_only],
                        "I"  # Bắt đầu từ cột I (sau H)
                    )
                    
                    print(f"✅ Đã update 18 prices cho {symbol} tại hàng {row_num} (cột I:Z, bỏ qua H)", flush=True)
                    logger.info(f"✅ Đã update 18 prices cho {symbol} tại hàng {row_num} (cột I:Z)")
                else:
                    print(f"⚠️ Không lấy được price data cho {symbol}", flush=True)
                    logger.warning(f"Không lấy được price data cho {symbol}")
                    
            except Exception as e:
                print(f"❌ Lỗi tracking prices cho {symbol}: {e}", flush=True)
                logger.error(f"Lỗi tracking prices cho {symbol}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"=== Hoàn thành tracking 18 prices ===\n", flush=True)
        logger.info(f"=== Hoàn thành tracking 18 prices ===\n")


def do_it():
    """Main loop"""
    tracker = PriceTracker()
    tracker.track_prices()


if __name__ == "__main__":
    print("🚀 Khởi động module Track 18 Prices", flush=True)
    logger.info("🚀 Khởi động module Track 18 Prices")
    
    while True:
        try:
            resync_exchange_time(exchange)  # [Fix1] chống clock drift -> hết -1021
            do_it()
        except Exception as e:
            if '-1021' in str(e) or 'recvWindow' in str(e):
                resync_exchange_time(exchange, min_interval=0)  # [Fix4] ép resync ccxt ngay
            print(f"❌ Tổng lỗi: {e}", flush=True)
            logger.error(f"Tổng lỗi: {e}")
            import traceback
            traceback.print_exc()
        
        # Sleep theo config (mặc định 60s)
        delay = getattr(cst, 'delay_track_30_prices', 60)
        print(f"💤 Ngủ {delay}s...", flush=True)
        logger.info(f"Ngủ {delay}s...")
        time.sleep(delay)

