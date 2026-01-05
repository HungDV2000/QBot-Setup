import gg_sheet_factory
import ccxt 
import time
import datetime
from enum import Enum
import numpy as np
from datetime import datetime, timedelta
import cst
import time
import logging
import pandas as pd
import ctypes
import utils
import numpy as np
import json

import os
from pathlib import Path

file_name = os.path.basename(os.path.abspath(__file__))  
os.system(f"title {file_name} - {cst.key_name}")

# Tạo thư mục logs/ nếu chưa có
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Chỉ log ERROR vào logs/error.log
logging.basicConfig(
    level=logging.ERROR,  # Chỉ log ERROR
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
# Thêm file handler cho error.log
error_log_path = logs_dir / 'error.log'
error_handler = logging.FileHandler(error_log_path, encoding='utf-8')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(error_handler)

def set_cmd_title(title):
    ctypes.windll.kernel32.SetConsoleTitleW(title)

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
            sym = d[0]
            
            if sym:
                list_all.append(sym+":USDT")
                print(sym, flush=True)
            else:
                break
            

        except Exception as e:
            print(f"Lỗi:getLenh23Rate : {e}", flush=True)
            logger.error(f"Lỗi xử lý symbol: {e}", exc_info=True)

    tab_100_ma_2d_arr = []

    not_symbol_contain = "trong 24h"
    
    for symbol in list_all:
        if not not_symbol_contain in symbol:
            print(symbol, flush=True)
            
            print(symbol, tickers[symbol]['last'], flush=True)
            pair= symbol.replace(":USDT", "")
            
            row = [ tickers[symbol]['last']]
            tab_100_ma_2d_arr.append(row)
        else:
            print("---------------", flush=True)
            tab_100_ma_2d_arr.append([])

    
    
    
    
    print(tab_100_ma_2d_arr, flush=True)
    gg_sheet_factory.update_multi(gg_sheet_factory.tab_list_all_ma, 1, tab_100_ma_2d_arr, "Y")

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Thời gian thực thi: {execution_time} giây", flush=True)
 

while True:
    try:
        do_it()
        
        
    except Exception as e:
        print(f"Tổng Lỗi: {e}", flush=True)
        logger.error(f"Tổng lỗi: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
    
    time.sleep(cst.delay_update_price)