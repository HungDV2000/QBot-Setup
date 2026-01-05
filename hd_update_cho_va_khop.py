import ccxt
import cst
import gg_sheet_factory
import logging
import time
from datetime import datetime
from pathlib import Path
import os

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

exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'enableRateLimit': True,  
    'apiKey': cst.key_binance,
    'secret': cst.secret_binance,
    'options': {
        'defaultType': 'future',
        'warnOnFetchOpenOrdersWithoutSymbol': False  # Fix: Suppress warning về rate limits
    }
})
exchange.setSandboxMode(False)



def get_all_open_orders_with_single_order():
    """
    Lấy tất cả orders có đúng 1 order pending cho mỗi symbol
    Thay đổi: Lấy trực tiếp từ Binance API thay vì từ thư mục local
    """
    res = []
    
    try:
        # Fix: Lấy TẤT CẢ open orders từ Binance (không cần biết symbols trước)
        # Không truyền symbol = lấy tất cả orders của tất cả symbols
        all_orders = exchange.fetch_open_orders()
        
        print(f"Tổng số orders từ Binance: {len(all_orders)}", flush=True)
        
        # Nhóm orders theo symbol
        orders_by_symbol = {}
        for order in all_orders:
            symbol = order['symbol']
            if symbol not in orders_by_symbol:
                orders_by_symbol[symbol] = []
            orders_by_symbol[symbol].append(order)
        
        # Chỉ lấy symbols có đúng 1 order
        for symbol, orders in orders_by_symbol.items():
            if len(orders) == 1:
                res.append(orders[0])
                print(f"Symbol: {symbol}, ID: {orders[0]['id']}, Status: {orders[0]['status']}, Amount: {orders[0]['amount']}, Price: {orders[0].get('price', 'N/A')}")
        
        print(f"Tìm thấy {len(res)} symbols có đúng 1 order")
        
    except Exception as e:
        print(f"Lỗi khi lấy orders từ Binance: {e}")
        logging.error(f"Lỗi get_all_open_orders_with_single_order: {e}")
    
    return res

def get_opened_possition():
    
    balance = exchange.fetch_balance()
    positions = balance['info']['positions']
    opened_possition = []
    
    for position in positions:
        
        symbol = position['symbol']
        position_amt = float(position['positionAmt'])
        # Fix: Kiểm tra key 'entryPrice' tồn tại trước khi dùng
        entry_price = float(position.get('entryPrice', 0)) if position.get('entryPrice') else 0.0
        unrealized_pnl = float(position.get('unrealizedProfit', 0)) if position.get('unrealizedProfit') else 0.0
        leverage = int(position.get('leverage', 1)) if position.get('leverage') else 1
        if position_amt != 0:
            print(position, flush=True)
            opened_possition.append(position)
            print(f"Symbol: {symbol}, Position: {position_amt}, Entry Price: {entry_price}, Unrealized PnL: {unrealized_pnl}, Leverage: {leverage}", flush=True)
    return opened_possition

def do_it():
    print(f"{datetime.now()}. Update chờ và khớp----------------------------------------------------", flush=True)

    tab_100_ma_2d_arr = []
    res = get_opened_possition()
    print(f"Tổng Lệnh: {len(res)}", flush=True)
    print(res, flush=True)
    
    for position in res:
        position_amt = float(position['positionAmt'])
        cac_ma = position['symbol']
        vi_the_short_long = 'LONG' if  position_amt > 0 else 'SHORT' if position_amt < 0 else 'Flat'
        cho_khop = "N"
        da_khop_mo_vi_the = "Y"
        # Fix: Kiểm tra key tồn tại trước khi dùng
        gia_vao = position.get('entryPrice', 0) if position.get('entryPrice') else 0.0
        don_bay = position.get('leverage', 1) if position.get('leverage') else 1
        
        orders = exchange.fetch_open_orders(symbol=cac_ma)
        
        lenh_nguoc_da_co_chua_co_2= len(orders)
        if lenh_nguoc_da_co_chua_co_2 == 1:
            
            lenh_tp= "Y"
            lenh_ls= "Y"
        else:
            
            lenh_tp= "N"
            lenh_ls= "N"
        print(cac_ma.replace("USDT", "/USDT"),vi_the_short_long ,cho_khop,da_khop_mo_vi_the , gia_vao,don_bay , lenh_tp, lenh_ls, lenh_nguoc_da_co_chua_co_2, flush=True)
        row  = cac_ma.replace("USDT", "/USDT"),vi_the_short_long ,cho_khop,da_khop_mo_vi_the , gia_vao,don_bay , lenh_tp, lenh_ls, lenh_nguoc_da_co_chua_co_2
        tab_100_ma_2d_arr.append(row)

    res1 = get_all_open_orders_with_single_order()
    print(res1, flush=True)
    print(f"Tổng Lệnh: {len(res1)}", flush=True)

    for order in res1:
        print(f"Symbol: {order['symbol']}, ID: {order['id']}, Status: {order['status']}, Amount: {order['amount']}, Price: {order['price']}", flush=True)
        
        
        order_symbol = order['info']['symbol']
        if next((position for position in res if order_symbol == position['symbol']), None):
                continue

        print(f"Found: {order}", flush=True)
        
        cac_ma = order_symbol
        side = order['info']['side']
        vi_the_short_long = 'LONG' if  side == "BUY" else 'SHORT'
        cho_khop = "Y"
        da_khop_mo_vi_the = "N"
        gia_vao = order['info']['price']
        don_bay = "N"
        lenh_tp= "N"
        lenh_ls= "N"
        lenh_nguoc_da_co_chua_co_2 = 0
        print(cac_ma.replace("USDT", "/USDT"),vi_the_short_long ,cho_khop,da_khop_mo_vi_the , gia_vao,don_bay , lenh_tp, lenh_ls, lenh_nguoc_da_co_chua_co_2, flush=True)
        row  = cac_ma.replace("USDT", "/USDT"),vi_the_short_long ,cho_khop,da_khop_mo_vi_the , gia_vao,don_bay , lenh_tp, lenh_ls, lenh_nguoc_da_co_chua_co_2
        tab_100_ma_2d_arr.append(row)

    # Fix: Clear dữ liệu cũ và thêm timestamp
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Fix: Clear từ hàng 2 trở đi (giữ header ở hàng 1)
    # array_index = 0 để clear từ hàng 2 (vì index = 2 + 0 = 2)
    gg_sheet_factory.clear_multi(gg_sheet_factory.tab_cho_va_khop, 0, "a", end_row=1000)
    
    # Fix: Ghi timestamp vào A4 trước (riêng biệt để đảm bảo được cập nhật)
    print(f"Cập nhật timestamp vào A4: {current_time}", flush=True)
    gg_sheet_factory.update_single_value(gg_sheet_factory.tab_cho_va_khop, "A4", current_time)
    
    # Thêm timestamp vào đầu array
    if tab_100_ma_2d_arr:
        # Thêm timestamp vào hàng đầu tiên của data
        tab_100_ma_2d_arr = [[current_time] + [""] * (len(tab_100_ma_2d_arr[0]) - 1) if tab_100_ma_2d_arr else [current_time]] + tab_100_ma_2d_arr
    
    # Fix: Update dữ liệu mới từ hàng 4 (thay thế, không append)
    # array_index = 2 để update từ hàng 4 (vì index = 2 + 2 = 4)
    gg_sheet_factory.update_multi(gg_sheet_factory.tab_cho_va_khop, 2, tab_100_ma_2d_arr, "a")

while True:
    try:
        do_it()
        
        
    except Exception as e:
        print(f"Tổng Lỗi: {e}", flush=True)
        logger.error(f"Tổng lỗi: {e}", exc_info=True)
        import traceback
        traceback.print_exc()

    time.sleep(cst.delay_cho_va_khop)