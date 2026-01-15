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

# Tạo tên file log với timestamp: cho_va_khop_dd_mm_yyyy.txt
log_timestamp = datetime.now().strftime('%d_%m_%Y')
log_filename_base = f'cho_va_khop_{log_timestamp}'

# Logging cải thiện với file trong logs/
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# File handler cho error log với timestamp (định dạng .txt)
error_log_path = logs_dir / f'{log_filename_base}_error.txt'
error_handler = logging.FileHandler(error_log_path, encoding='utf-8')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(error_handler)

# File handler cho info log với timestamp (định dạng .txt)
info_log_path = logs_dir / f'{log_filename_base}_info.txt'
info_handler = logging.FileHandler(info_log_path, encoding='utf-8')
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(info_handler)

print(f"📝 Log files: {error_log_path.name} & {info_log_path.name}", flush=True)

exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'enableRateLimit': True,  
    'apiKey': cst.key_binance,
    'secret': cst.secret_binance,
    'options': {
        'defaultType': 'future',
        'warnOnFetchOpenOrdersWithoutSymbol': False  # Suppress warning
    }
})
exchange.setSandboxMode(False)

logger.info("✅ Khởi tạo Binance exchange thành công")


def check_sl_tp_orders(orders):
    """
    Phân tích danh sách orders để xác định có SL và TP không
    
    Logic phân biệt:
    - STOP_MARKET, STOP → Stop Loss (SL)
    - TRAILING_STOP_MARKET → Take Profit (TP)
    - TAKE_PROFIT_MARKET, TAKE_PROFIT → Take Profit (TP)
    
    Returns: (has_sl, has_tp, order_count)
    """
    has_sl = False
    has_tp = False
    order_count = len(orders)
    
    for order in orders:
        try:
            order_type = str(order.get('type', '')).upper()
            
            # Debug log
            logger.debug(f"Order type: {order_type}, ID: {order.get('id', 'N/A')}")
            
            # Check Stop Loss (STOP nhưng không phải TRAILING_STOP)
            if 'STOP' in order_type and 'TRAILING' not in order_type:
                has_sl = True
                logger.debug(f"  → Detected SL order")
            
            # Check Take Profit (TRAILING_STOP hoặc TAKE_PROFIT)
            if 'TRAILING' in order_type or 'TAKE_PROFIT' in order_type:
                has_tp = True
                logger.debug(f"  → Detected TP order")
                
        except Exception as e:
            logger.error(f"Lỗi khi phân tích order: {e}")
            continue
    
    return has_sl, has_tp, order_count


def get_all_open_orders_with_single_order():
    """
    Lấy tất cả orders có đúng 1 order pending cho mỗi symbol
    (Sử dụng để track lệnh entry đang chờ khớp)
    """
    res = []
    
    try:
        # Lấy TẤT CẢ open orders từ Binance (không cần biết symbols trước)
        print("🔍 Đang lấy tất cả open orders từ Binance...", flush=True)
        all_orders = exchange.fetch_open_orders()
        
        print(f"✅ Tổng số orders: {len(all_orders)}", flush=True)
        logger.info(f"Tổng số open orders: {len(all_orders)}")
        
        # Nhóm orders theo symbol
        orders_by_symbol = {}
        for order in all_orders:
            symbol = order['symbol']
            if symbol not in orders_by_symbol:
                orders_by_symbol[symbol] = []
            orders_by_symbol[symbol].append(order)
        
        # Chỉ lấy symbols có đúng 1 order (lệnh entry chờ khớp)
        for symbol, orders in orders_by_symbol.items():
            if len(orders) == 1:
                res.append(orders[0])
                print(f"  📌 {symbol}: 1 order (chờ khớp)", flush=True)
                order = orders[0]
                print(f"     ID: {order['id']}, Type: {order.get('type', 'N/A')}, Amount: {order['amount']}, Price: {order.get('price', 'N/A')}", flush=True)
        
        print(f"✅ Tìm thấy {len(res)} symbols có đúng 1 order (lệnh entry)", flush=True)
        logger.info(f"Symbols có đúng 1 order: {len(res)}")
        
    except Exception as e:
        print(f"❌ Lỗi khi lấy orders từ Binance: {e}", flush=True)
        logger.error(f"Lỗi get_all_open_orders_with_single_order: {e}", exc_info=True)
    
    return res

def get_opened_possition():
    """
    Lấy tất cả positions đang mở (position_amt != 0)
    """
    balance = exchange.fetch_balance()
    positions = balance['info']['positions']
    opened_possition = []
    
    for position in positions:
        try:
            symbol = position['symbol']
            position_amt = float(position['positionAmt'])
            
            # Fix: Kiểm tra key tồn tại trước khi dùng
            entry_price = float(position.get('entryPrice', 0)) if position.get('entryPrice') else 0.0
            unrealized_pnl = float(position.get('unrealizedProfit', 0)) if position.get('unrealizedProfit') else 0.0
            leverage = int(position.get('leverage', 1)) if position.get('leverage') else 1
            
            if position_amt != 0:
                opened_possition.append(position)
                print(f"📊 {symbol}: Pos={position_amt}, Entry={entry_price}, PnL={unrealized_pnl:.2f}, Lev={leverage}x", flush=True)
                logger.info(f"Position: {symbol}, Amt={position_amt}, Entry={entry_price}, PnL={unrealized_pnl}, Lev={leverage}")
        except Exception as e:
            logger.error(f"Lỗi khi xử lý position {position.get('symbol', 'N/A')}: {e}")
            continue
    
    return opened_possition

def do_it():
    current_time = datetime.now()
    print(f"\n{'='*80}", flush=True)
    print(f"🔄 {current_time.strftime('%Y-%m-%d %H:%M:%S')} - Bắt đầu scan 'Chờ và khớp'", flush=True)
    print(f"{'='*80}\n", flush=True)
    logger.info(f"{'='*80}")
    logger.info(f"Bắt đầu scan 'Chờ và khớp'")

    tab_100_ma_2d_arr = []
    
    # BƯỚC 1: Lấy positions đang mở
    print("📊 BƯỚC 1: Lấy positions đang mở từ Binance...", flush=True)
    res = get_opened_possition()
    print(f"✅ Tổng positions: {len(res)}\n", flush=True)
    logger.info(f"Tổng positions đang mở: {len(res)}")
    
    # BƯỚC 2: Xử lý từng position
    print("🔧 BƯỚC 2: Xử lý từng position...", flush=True)
    for idx, position in enumerate(res, 1):
        try:
            position_amt = float(position['positionAmt'])
            cac_ma = position['symbol']
            
            print(f"\n  [{idx}/{len(res)}] Xử lý {cac_ma}...", flush=True)
            
            # Format symbol: HOMEUSDT → HOME/USDT
            symbol_formatted = cac_ma.replace("USDT", "/USDT")
            
            # Xác định LONG/SHORT
            vi_the_short_long = 'LONG' if position_amt > 0 else 'SHORT' if position_amt < 0 else 'Flat'
            
            # Đã khớp (có position)
            cho_khop = "N"  # Không còn chờ
            da_khop_mo_vi_the = "Y"  # Đã mở vị thế
            
            # Entry price và leverage
            gia_vao = position.get('entryPrice', 0) if position.get('entryPrice') else 0.0
            don_bay = position.get('leverage', 1) if position.get('leverage') else 1
            
            # Lấy orders cho symbol này
            orders = exchange.fetch_open_orders(symbol=cac_ma)
            
            # ✅ LOGIC MỚI: Phân tích chính xác SL/TP
            has_sl, has_tp, order_count = check_sl_tp_orders(orders)
            
            lenh_ls = "Y" if has_sl else "N"  # Cột G
            lenh_tp = "Y" if has_tp else "N"  # Cột H
            lenh_nguoc = order_count  # Cột I (số lượng orders)
            
            print(f"    ✓ Side: {vi_the_short_long}, Entry: {gia_vao}, Lev: {don_bay}x", flush=True)
            print(f"    ✓ Orders: {order_count} (SL: {lenh_ls}, TP: {lenh_tp})", flush=True)
            
            logger.info(f"{symbol_formatted}: {vi_the_short_long}, Entry={gia_vao}, Lev={don_bay}, Orders={order_count}, SL={lenh_ls}, TP={lenh_tp}")
            
            # Tạo row với 11 cột (A-K)
            row = (
                symbol_formatted,      # A: Symbol
                vi_the_short_long,     # B: LONG/SHORT
                cho_khop,              # C: Chờ khớp (N)
                da_khop_mo_vi_the,     # D: Đã khớp (Y)
                gia_vao,               # E: Giá vào
                don_bay,               # F: Đòn bẩy
                lenh_ls,               # G: Lệnh Stop Limit (Y/N)
                lenh_tp,               # H: Lệnh Trailing Stop (Y/N)
                lenh_nguoc,            # I: Số lượng orders
                "",                    # J: Rate SL (%) - Để trống, user điền tay
                ""                     # K: Rate TP (%) - Để trống, user điền tay
            )
            tab_100_ma_2d_arr.append(row)
            
        except Exception as e:
            print(f"    ❌ Lỗi xử lý position {cac_ma}: {e}", flush=True)
            logger.error(f"Lỗi xử lý position {cac_ma}: {e}", exc_info=True)
            continue

    # BƯỚC 3: Lấy orders chờ khớp (entry orders)
    print("\n📝 BƯỚC 3: Lấy orders chờ khớp (entry orders)...", flush=True)
    res1 = get_all_open_orders_with_single_order()
    print(f"✅ Tổng orders chờ khớp: {len(res1)}\n", flush=True)
    logger.info(f"Tổng orders chờ khớp: {len(res1)}")

    # BƯỚC 4: Xử lý từng order chờ khớp
    print("🔧 BƯỚC 4: Xử lý orders chờ khớp...", flush=True)
    for idx, order in enumerate(res1, 1):
        try:
            print(f"\n  [{idx}/{len(res1)}] Xử lý order {order.get('id', 'N/A')}...", flush=True)
            
            order_symbol = order['info']['symbol']
            
            # Skip nếu symbol đã có position (tránh trùng lặp)
            if next((position for position in res if order_symbol == position['symbol']), None):
                print(f"    ⏭️  Bỏ qua (đã có position)", flush=True)
                continue

            print(f"    ✓ Symbol: {order['symbol']}, Type: {order.get('type', 'N/A')}", flush=True)
            
            # Format symbol
            cac_ma = order_symbol
            symbol_formatted = cac_ma.replace("USDT", "/USDT")
            
            # Xác định side từ order
            side = order['info']['side']
            vi_the_short_long = 'LONG' if side == "BUY" else 'SHORT'
            
            # Đang chờ khớp (chưa có position)
            cho_khop = "Y"  # Đang chờ
            da_khop_mo_vi_the = "N"  # Chưa mở vị thế
            
            # Price và leverage
            gia_vao = order['info'].get('price', 0)
            don_bay = "N"  # Chưa có leverage (chưa có position)
            
            # Chưa có SL/TP (chưa vào lệnh)
            lenh_ls = "N"
            lenh_tp = "N"
            lenh_nguoc = 0  # Không có orders khác
            
            print(f"    ✓ Side: {vi_the_short_long}, Price: {gia_vao}", flush=True)
            print(f"    ✓ Trạng thái: Chờ khớp", flush=True)
            
            logger.info(f"{symbol_formatted}: {vi_the_short_long}, Price={gia_vao}, Status=Chờ khớp")
            
            # Tạo row với 11 cột (A-K)
            row = (
                symbol_formatted,      # A: Symbol
                vi_the_short_long,     # B: LONG/SHORT
                cho_khop,              # C: Chờ khớp (Y)
                da_khop_mo_vi_the,     # D: Đã khớp (N)
                gia_vao,               # E: Giá vào (activation price)
                don_bay,               # F: Đòn bẩy (N - chưa có)
                lenh_ls,               # G: Lệnh SL (N)
                lenh_tp,               # H: Lệnh TP (N)
                lenh_nguoc,            # I: Số lượng orders (0)
                "",                    # J: Rate SL (%) - Để trống
                ""                     # K: Rate TP (%) - Để trống
            )
            tab_100_ma_2d_arr.append(row)
            
        except Exception as e:
            print(f"    ❌ Lỗi xử lý order: {e}", flush=True)
            logger.error(f"Lỗi xử lý order {order.get('id', 'N/A')}: {e}", exc_info=True)
            continue

    # BƯỚC 5: Cập nhật lên Google Sheet
    print(f"\n📤 BƯỚC 5: Cập nhật lên Google Sheet...", flush=True)
    print(f"  Tổng dòng dữ liệu: {len(tab_100_ma_2d_arr)}", flush=True)
    logger.info(f"Tổng dòng dữ liệu: {len(tab_100_ma_2d_arr)}")
    
    try:
        # Clear dữ liệu cũ (từ hàng 4 trở đi, giữ header hàng 1-3)
        print("  🗑️  Xóa dữ liệu cũ...", flush=True)
        gg_sheet_factory.clear_multi(gg_sheet_factory.tab_cho_va_khop, 2, "a", end_row=1000)
        
        # Ghi timestamp vào A2
        timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"  📅 Cập nhật timestamp vào A2: {timestamp_str}", flush=True)
        gg_sheet_factory.update_single_value(gg_sheet_factory.tab_cho_va_khop, "A2", timestamp_str)
        
        # Update dữ liệu mới (bắt đầu từ hàng 4)
        print("  ✍️  Ghi dữ liệu mới...", flush=True)
        gg_sheet_factory.update_multi(gg_sheet_factory.tab_cho_va_khop, 2, tab_100_ma_2d_arr, "a")
        
        print(f"✅ Hoàn thành! Đã cập nhật {len(tab_100_ma_2d_arr)} dòng vào sheet", flush=True)
        logger.info(f"✅ Hoàn thành cập nhật sheet: {len(tab_100_ma_2d_arr)} dòng")
        
    except Exception as e:
        print(f"❌ Lỗi khi cập nhật sheet: {e}", flush=True)
        logger.error(f"Lỗi cập nhật sheet: {e}", exc_info=True)
    
    print(f"\n{'='*80}\n", flush=True)

print(f"🚀 Bot hd_update_cho_va_khop khởi động - Scan mỗi {cst.delay_cho_va_khop}s", flush=True)
logger.info(f"Bot khởi động - Scan interval: {cst.delay_cho_va_khop}s")

scan_count = 0

while True:
    try:
        scan_count += 1
        print(f"\n🔄 Scan lần {scan_count}", flush=True)
        logger.info(f"{'='*80}")
        logger.info(f"Scan lần {scan_count}")
        
        do_it()
        
        print(f"⏳ Chờ {cst.delay_cho_va_khop}s trước lần scan tiếp theo...\n", flush=True)
        
    except KeyboardInterrupt:
        print("\n⚠️  Nhận Ctrl+C - Dừng bot...", flush=True)
        logger.info("Bot dừng bởi user (Ctrl+C)")
        break
        
    except Exception as e:
        print(f"\n❌ Tổng Lỗi: {e}", flush=True)
        logger.error(f"Tổng lỗi: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        print(f"⏳ Chờ {cst.delay_cho_va_khop}s trước khi thử lại...\n", flush=True)
    
    time.sleep(cst.delay_cho_va_khop)

print("👋 Bot đã dừng", flush=True)
logger.info("Bot đã dừng")
