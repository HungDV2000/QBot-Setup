import gg_sheet_factory
import ccxt 
import time
from datetime import datetime, timedelta
import numpy as np
import cst
import logging
import ctypes
import platform
import os
from pathlib import Path

file_name = os.path.basename(os.path.abspath(__file__))

# Set title theo OS (Windows/macOS/Linux)
if platform.system() == "Windows":
    os.system(f"title {file_name} - {cst.key_name}")
else:
    # macOS/Linux: set terminal title bằng ANSI escape codes
    print(f"\033]0;{file_name} - {cst.key_name}\007", end='', flush=True)

# Tạo thư mục logs/ nếu chưa có
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Tạo tên file log với timestamp: hd_update_price_dd_mm_yyyy_H_M_S.txt
log_timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
log_filename = logs_dir / f'hd_update_price_{log_timestamp}.txt'

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

exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'enableRateLimit': True,  
    'apiKey': cst.key_binance,
    'secret': cst.secret_binance,
    'options': {
        'defaultType': 'future' 
    }
})
exchange.setSandboxMode(False)

def do_it():
    print(f"-------------------------------start scan giá: {datetime.now()}-------------------------------------", flush=True)
    start_time = time.time()

    # Fix: Thêm retry logic cho fetch_tickers()
    max_retries = 3
    retry_delay = 5
    tickers = None
    
    for attempt in range(max_retries):
        try:
            tickers = exchange.fetch_tickers()
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Lỗi khi fetch_tickers (lần thử {attempt + 1}/{max_retries}): {e}", flush=True)
                print(f"Đợi {retry_delay} giây trước khi thử lại...", flush=True)
                time.sleep(retry_delay)
            else:
                print(f"Lỗi fetch_tickers sau {max_retries} lần thử: {e}", flush=True)
                logger.error(f"Lỗi fetch_tickers: {e}", exc_info=True)
                raise
    
    if tickers is None:
        print("Không thể lấy dữ liệu tickers, bỏ qua lần này", flush=True)
        return

    list_all = []
    sheet_dat_lenh = gg_sheet_factory.get_100_ma(f"A3:A500")
    
    for d in sheet_dat_lenh:
        try:
            if not d or not d[0]:  # Kiểm tra dòng trống hoặc cell trống
                continue  # Bỏ qua dòng trống nhưng TIẾP TỤC scan (không break)
            
            sym = d[0].strip()
            
            # Chuẩn hóa symbol format
            if not sym.endswith(":USDT"):
                if sym.endswith("/USDT"):
                    sym = sym + ":USDT"
                elif not "/" in sym:
                    # Giả sử format BTCUSDT -> BTC/USDT:USDT
                    if sym.endswith("USDT"):
                        base = sym[:-4]
                        sym = f"{base}/USDT:USDT"
                    else:
                        sym = f"{sym}/USDT:USDT"
            
            list_all.append(sym)
            print(sym, flush=True)

        except Exception as e:
            print(f"Lỗi xử lý symbol tại dòng {d}: {e}", flush=True)
            logger.error(f"Lỗi xử lý symbol: {e}", exc_info=True)
            continue

    tab_100_ma_2d_arr = []
    not_symbol_contain = "trong 24h"
    
    for symbol in list_all:
        # Logic dễ đọc hơn: nếu KHÔNG CHỨA text "trong 24h"
        if not_symbol_contain not in symbol:
            print(symbol, flush=True)
            
            # Kiểm tra symbol có tồn tại trong tickers không
            if symbol not in tickers:
                print(f"⚠️  {symbol} không tìm thấy trong tickers, bỏ qua", flush=True)
                tab_100_ma_2d_arr.append([])  # Thêm dòng trống để giữ đúng vị trí
                continue
            
            try:
                last_price = tickers[symbol]['last']
                print(f"{symbol}: {last_price}", flush=True)
                row = [last_price]
                tab_100_ma_2d_arr.append(row)
            except KeyError as e:
                print(f"⚠️  Lỗi lấy giá cho {symbol}: {e}", flush=True)
                logger.error(f"Lỗi lấy giá cho {symbol}: {e}", exc_info=True)
                tab_100_ma_2d_arr.append([])
        else:
            # Dòng title (chứa "trong 24h")
            print(f"[TITLE] {symbol}", flush=True)
            tab_100_ma_2d_arr.append([])

    print(f"\n📊 Cập nhật {len(tab_100_ma_2d_arr)} dòng vào sheet...", flush=True)
    gg_sheet_factory.update_multi(gg_sheet_factory.tab_list_all_ma, 1, tab_100_ma_2d_arr, "Y")

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"✅ Thời gian thực thi: {execution_time:.2f} giây", flush=True)

while True:
    try:
        do_it()
    except Exception as e:
        print(f"❌ Tổng Lỗi: {e}", flush=True)
        logger.error(f"Tổng lỗi: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
    
    time.sleep(cst.delay_update_price)
