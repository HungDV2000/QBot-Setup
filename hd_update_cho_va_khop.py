import ccxt
import cst
import gg_sheet_factory
import logging
import time
from datetime import datetime
from pathlib import Path
import os
import requests
import hmac
import hashlib
import urllib.parse
from googleapiclient.errors import HttpError

file_name = os.path.basename(os.path.abspath(__file__))  
os.system(f"title {file_name} - {cst.key_name}")

# Tạo thư mục logs/ nếu chưa có
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Tạo tên file log với timestamp: cho_va_khop_dd_mm_yyyy_H_M_S.txt
log_timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
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


def call_binance_api_direct(method, endpoint, params=None):
    """
    Gọi Binance API trực tiếp bằng requests (để lấy algo orders)
    """
    base_url = 'https://fapi.binance.com'
    url = f"{base_url}{endpoint}"
    
    if params is None:
        params = {}
    
    # Thêm timestamp
    params['timestamp'] = int(time.time() * 1000)
    
    # Tạo query string
    query_string = urllib.parse.urlencode(params)
    
    # Tạo signature
    signature = hmac.new(
        cst.secret_binance.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    params['signature'] = signature
    
    # Headers
    headers = {
        'X-MBX-APIKEY': cst.key_binance
    }
    
    try:
        if method.upper() == 'GET':
            response = requests.get(url, params=params, headers=headers, timeout=10)
        else:
            return None
            
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Lỗi khi gọi Binance API trực tiếp ({method} {endpoint}): {e}")
        return None

def get_algo_orders_for_symbol(symbol):
    """
    Lấy algo orders cho một symbol cụ thể từ Binance API
    Dùng endpoint: /fapi/v1/allAlgoOrders (Query All Algo Orders)
    """
    try:
        # Binance API yêu cầu symbol format: HOMEUSDT (không có / và :USDT)
        symbol_clean = symbol.replace('/', '').replace(':USDT', '')
        
        params = {
            'symbol': symbol_clean
        }
        
        response = call_binance_api_direct('GET', '/fapi/v1/allAlgoOrders', params)
        
        if not response:
            return []
        
        # Binance trả về có thể là array hoặc dict
        if isinstance(response, list):
            return response
        elif isinstance(response, dict):
            if 'data' in response:
                return response['data']
            elif response.get('code') == 200:
                return response
            else:
                logger.warning(f"Response có code khác 200 cho {symbol}: {response}")
                return []
        else:
            logger.warning(f"Response format không đúng cho {symbol}: {type(response)}")
            return []
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy algo orders cho {symbol}: {e}", exc_info=True)
        return []


def check_sl_tp_orders(symbol, orders):
    """
    Phân tích danh sách orders để xác định có SL và TP không
    ✅ CẬP NHẬT: Quét cả algo orders (giống hd_order_123.py)
    
    Logic phân biệt:
    - Algo Orders: STOP_MARKET, STOP_LOSS → SL; TRAILING_STOP → TP
    - Open Orders: STOP, STOP_LIMIT, STOP_MARKET → SL
    
    Returns: (has_sl, has_tp, order_count)
    """
    has_sl = False
    has_tp = False
    
    try:
        # ✅ BƯỚC 1: QUÉT ALGO ORDERS (quan trọng nhất!)
        algo_orders = get_algo_orders_for_symbol(symbol)
        active_algo_orders = [o for o in algo_orders if o.get('algoStatus', '').upper() == 'NEW']
        
        logger.debug(f"{symbol}: Tìm thấy {len(active_algo_orders)} active algo orders")
        
        for order in active_algo_orders:
            algo_type = order.get('algoType', '').upper()
            reduce_only = order.get('reduceOnly', False)
            
            # Lấy callbackRate để phân biệt
            callback_rate = order.get('callbackRate')
            callback_val = 0.0
            if callback_rate is not None:
                try:
                    callback_val = float(callback_rate)
                except:
                    callback_val = 0.0

            if reduce_only:
                # == KIỂM TRA TP (Trailing Stop) ==
                if algo_type in ['CONDITIONAL', 'VP', 'TRAILING_STOP_MARKET'] and callback_val > 0:
                    has_tp = True
                    logger.debug(f"  → Detected TP algo order: {algo_type}, callbackRate={callback_val}")
                
                # == KIỂM TRA SL (Stop Limit/Market) ==
                if algo_type in ['STOP', 'STOP_MARKET', 'STOP_LOSS', 'STOP_LOSS_MARKET', 'STOP_LIMIT']:
                    has_sl = True
                    logger.debug(f"  → Detected SL algo order: {algo_type}")
                elif algo_type == 'CONDITIONAL' and callback_val == 0:
                    has_sl = True
                    logger.debug(f"  → Detected SL algo order: CONDITIONAL (callbackRate=0)")
        
        # ✅ BƯỚC 2: QUÉT OPEN ORDERS (fallback nếu chưa có SL)
        if not has_sl:
            for order in orders:
                try:
                    order_type = str(order.get('type', '')).upper()
                    info = order.get('info', {})
                    reduce_only = order.get('reduceOnly', False) or info.get('reduceOnly', False)
                    
                    # Check Stop Loss (STOP nhưng không phải TRAILING_STOP)
                    if order_type in ['STOP', 'STOP_LIMIT', 'STOP_MARKET'] and reduce_only:
                        has_sl = True
                        logger.debug(f"  → Detected SL open order: {order_type}")
                    
                    # Check Take Profit (TRAILING_STOP hoặc TAKE_PROFIT)
                    if 'TRAILING' in order_type or 'TAKE_PROFIT' in order_type:
                        has_tp = True
                        logger.debug(f"  → Detected TP open order: {order_type}")
                        
                except Exception as e:
                    logger.error(f"Lỗi khi phân tích order: {e}")
                    continue
        
        # Đếm tổng số orders (algo + open)
        order_count = len(active_algo_orders) + len(orders)
        
    except Exception as e:
        logger.error(f"Lỗi khi check SL/TP cho {symbol}: {e}", exc_info=True)
        # Fallback: chỉ đếm open orders
        order_count = len(orders)
    
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
    SỬ DỤNG fetch_positions() thay vì fetch_balance() để có entryPrice!
    """
    try:
        # ✅ FIX: Dùng fetch_positions() thay vì fetch_balance()['info']['positions']
        # Vì fetch_balance() KHÔNG trả về entryPrice trong raw data!
        positions = exchange.fetch_positions()
        logger.info(f"✅ Đã lấy {len(positions)} positions từ fetch_positions()")
    except Exception as e:
        logger.error(f"Lỗi khi lấy positions: {e}", exc_info=True)
        return []
    
    opened_possition = []
    
    for position in positions:
        try:
            # CCXT fetch_positions() trả về format khác:
            # - 'contracts' (luôn dương) thay vì 'positionAmt' (có thể âm/dương)
            # - 'side' = "long" hoặc "short"
            # - 'symbol' = "HOME/USDT:USDT" (đã format sẵn)
            # - CÓ 'entryPrice' và 'leverage'!
            
            contracts = float(position.get('contracts', 0))
            if contracts == 0:
                continue  # Bỏ qua position rỗng
            
            side = position.get('side', '').lower()
            symbol_ccxt = position['symbol']  # "HOME/USDT:USDT"
            
            # Convert về format "HOMEUSDT" để tương thích với code hiện tại
            symbol = symbol_ccxt.replace('/', '').replace(':USDT', '')
            
            # Convert contracts + side thành position_amt (âm nếu short, dương nếu long)
            position_amt = contracts if side == 'long' else -contracts
            
            # Parse entry price - fetch_positions() CÓ entryPrice!
            entry_price_raw = position.get('entryPrice')
            if entry_price_raw is not None and entry_price_raw != '' and entry_price_raw != 0:
                try:
                    entry_price = float(entry_price_raw)
                except (ValueError, TypeError):
                    entry_price = 0.0
                    logger.warning(f"{symbol}: Lỗi parse entryPrice: {entry_price_raw}")
            else:
                entry_price = 0.0
                logger.warning(f"{symbol}: entryPrice rỗng hoặc = 0, raw: {entry_price_raw}")
            
            # Parse unrealized PnL
            unrealized_pnl_raw = position.get('unrealizedPnl', position.get('unrealizedProfit', 0))
            if unrealized_pnl_raw is not None and unrealized_pnl_raw != '':
                try:
                    unrealized_pnl = float(unrealized_pnl_raw)
                except (ValueError, TypeError):
                    unrealized_pnl = 0.0
            else:
                unrealized_pnl = 0.0
            
            # Parse leverage - fetch_positions() CÓ leverage!
            leverage_raw = position.get('leverage')
            if leverage_raw is not None and leverage_raw != '' and leverage_raw != 0:
                try:
                    leverage = int(float(leverage_raw))
                except (ValueError, TypeError):
                    leverage = 1
            else:
                leverage = 1
            
            # Thêm position vào danh sách
            # Lưu cả symbol gốc (CCXT format) và symbol format (để tương thích)
            position['symbol'] = symbol  # Format "HOMEUSDT" để tương thích với code hiện tại
            position['symbol_ccxt'] = symbol_ccxt  # Format "HOME/USDT:USDT" để dùng cho API calls
            position['positionAmt'] = str(position_amt)  # Thêm positionAmt để tương thích
            
            opened_possition.append(position)
            print(f"📊 {symbol}: Pos={position_amt}, Entry={entry_price}, PnL={unrealized_pnl:.2f}, Lev={leverage}x", flush=True)
            logger.info(f"Position: {symbol}, Amt={position_amt}, Entry={entry_price}, PnL={unrealized_pnl}, Lev={leverage}")
            
            # Debug: Log nếu entry price = 0 (không nên xảy ra với fetch_positions())
            if entry_price == 0.0:
                logger.error(f"❌ {symbol}: Entry price = 0! (Không nên xảy ra với fetch_positions())")
                logger.error(f"   Raw entryPrice: {entry_price_raw} (type: {type(entry_price_raw)})")
                logger.error(f"   FULL RAW POSITION DATA: {position}")
                print(f"    ⚠️  Entry price = 0! Xem log chi tiết.", flush=True)
                    
        except Exception as e:
            logger.error(f"Lỗi khi xử lý position {position.get('symbol', 'N/A')}: {e}", exc_info=True)
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
            
            # Debug: Log raw position data để kiểm tra
            logger.debug(f"Raw position data for {cac_ma}: {position}")
            
            # Format symbol: HOMEUSDT → HOME/USDT
            symbol_formatted = cac_ma.replace("USDT", "/USDT")
            
            # Xác định LONG/SHORT
            vi_the_short_long = 'LONG' if position_amt > 0 else 'SHORT' if position_amt < 0 else 'Flat'
            
            # Đã khớp (có position)
            cho_khop = "N"  # Không còn chờ
            da_khop_mo_vi_the = "Y"  # Đã mở vị thế
            
            # Entry price và leverage - Parse an toàn
            entry_price_raw = position.get('entryPrice')
            if entry_price_raw is not None and entry_price_raw != '' and entry_price_raw != 0:
                try:
                    gia_vao = float(entry_price_raw)
                except (ValueError, TypeError):
                    gia_vao = 0.0
                    logger.warning(f"{cac_ma}: Lỗi parse entryPrice: {entry_price_raw}")
            else:
                gia_vao = 0.0
                logger.warning(f"{cac_ma}: entryPrice rỗng hoặc = 0, raw: {entry_price_raw}")
            
            leverage_raw = position.get('leverage')
            if leverage_raw is not None and leverage_raw != '' and leverage_raw != 0:
                try:
                    don_bay = int(float(leverage_raw))
                except (ValueError, TypeError):
                    don_bay = 1
            else:
                don_bay = 1
            
            # Lấy orders cho symbol này - dùng symbol_ccxt nếu có (format CCXT chuẩn)
            symbol_for_orders = position.get('symbol_ccxt', cac_ma)
            # Nếu không có symbol_ccxt, convert từ "HOMEUSDT" → "HOME/USDT:USDT"
            if symbol_for_orders == cac_ma and 'symbol_ccxt' not in position:
                symbol_for_orders = cac_ma.replace("USDT", "/USDT:USDT")
            
            try:
                orders = exchange.fetch_open_orders(symbol=symbol_for_orders)
            except Exception as e:
                logger.warning(f"Lỗi khi lấy open orders cho {symbol_for_orders}: {e}")
                orders = []
            
            # ✅ LOGIC MỚI: Phân tích chính xác SL/TP (quét cả algo orders)
            # Truyền symbol để quét algo orders
            has_sl, has_tp, order_count = check_sl_tp_orders(symbol_for_orders, orders)
            
            lenh_ls = "Y" if has_sl else "N"  # Cột G
            lenh_tp = "Y" if has_tp else "N"  # Cột H
            lenh_nguoc = order_count  # Cột I (số lượng orders)
            
            print(f"    ✓ Side: {vi_the_short_long}, Entry: {gia_vao}, Lev: {don_bay}x", flush=True)
            print(f"    ✓ Orders: {order_count} (SL: {lenh_ls}, TP: {lenh_tp})", flush=True)
            
            # ⚠️ VALIDATION: SKIP NẾU ENTRY PRICE = 0
            if gia_vao == 0.0 or gia_vao is None:
                print(f"    ❌ BỎ QUA: Entry price = 0 hoặc None! (Raw: {entry_price_raw})", flush=True)
                logger.error(f"❌ {symbol_formatted}: Entry price không hợp lệ (0 hoặc None). Raw: {entry_price_raw}")
                logger.error(f"   Position data: {position}")
                logger.error(f"   FULL RAW POSITION DATA: {position}")
                logger.error(f"   Position keys: {list(position.keys())}")
                # Log từng field quan trọng để debug
                for key in ['entryPrice', 'positionAmt', 'unrealizedProfit', 'leverage', 'markPrice', 'liquidationPrice', 'notional', 'isolated', 'marginType']:
                    if key in position:
                        logger.error(f"   {key}: {position[key]} (type: {type(position[key])})")
                continue  # Bỏ qua position này
            
            logger.info(f"{symbol_formatted}: {vi_the_short_long}, Entry={gia_vao}, Lev={don_bay}, Orders={order_count}, SL={lenh_ls}, TP={lenh_tp}")
            
            # ✅ Tạo row với 16 cột (A-P)
            # M: Tick xóa lệnh 1 (entry), N: Tick xóa cặp 2-3 (SL+TP), O: Tick xóa lệnh đơn 2-3 sót lại
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
                "",                    # J: Giá kích hoạt SL - Để trống, user điền tay
                "",                    # K: Giá kích hoạt TP - Để trống, user điền tay
                "",                    # L: Trạng thái cho phép đặt lệnh (Y/N)
                "",                    # M: Tick xóa lệnh 1 (entry order)
                "",                    # N: Tick xóa cặp 2-3 (SL+TP)
                "",                    # O: Tick xóa lệnh đơn 2-3 sót lại
                ""                     # P: (trống)
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
            
            # ✅ Tạo row với 16 cột (A-P)
            # M: Tick xóa lệnh 1 (entry), N: Tick xóa cặp 2-3 (SL+TP), O: Tick xóa lệnh đơn 2-3 sót lại
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
                "",                    # J: Giá kích hoạt SL - Để trống
                "",                    # K: Giá kích hoạt TP - Để trống
                "",                    # L: Trạng thái cho phép đặt lệnh (Y/N)
                "",                    # M: Tick xóa lệnh 1 (entry order)
                "",                    # N: Tick xóa cặp 2-3 (SL+TP)
                "",                    # O: Tick xóa lệnh đơn 2-3 sót lại
                ""                     # P: (trống)
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
        # ✅ BƯỚC 5.1: ĐỌC DỮ LIỆU CŨ (trước khi clear) để giữ lại giá kích hoạt SL/TP (cột J, K), trạng thái (L) và cột O, P
        print("  📖 Đọc dữ liệu cũ để giữ lại giá kích hoạt SL/TP (J, K), trạng thái (L) và cột O, P...", flush=True)
        data_map = {}  # Dict: {symbol: (price_sl, price_tp, status, col_o, col_p)}
        
        try:
            # ✅ Đọc dữ liệu cũ từ hàng 2, cột A-P (15 cột để có cả O, P)
            old_data = gg_sheet_factory.get_cho_va_khop("A2:P1000")
            
            if old_data:
                for row in old_data:
                    # Kiểm tra row có đủ dữ liệu không (ít nhất 15 cột để có M, N, O, P)
                    if len(row) >= 15:
                        symbol = str(row[0]).strip() if len(row) > 0 and row[0] else ""
                        price_sl = str(row[9]).strip() if len(row) > 9 and row[9] else ""  # Cột J (index 9): Giá kích hoạt SL
                        price_tp = str(row[10]).strip() if len(row) > 10 and row[10] else ""  # Cột K (index 10): Giá kích hoạt TP
                        status = str(row[11]).strip().upper() if len(row) > 11 and row[11] else ""  # Cột L (index 11): Trạng thái Y/N
                        col_m = str(row[12]).strip() if len(row) > 12 and row[12] else ""  # Cột M (index 12): Tick xóa lệnh 1
                        col_n = str(row[13]).strip() if len(row) > 13 and row[13] else ""  # Cột N (index 13): Tick xóa cặp 2-3
                        col_o = str(row[14]).strip() if len(row) > 14 and row[14] else ""  # Cột O (index 14): Tick xóa lệnh đơn
                        
                        # Chỉ lưu nếu có symbol
                        if symbol:
                            # Chuẩn hóa symbol format: HOME/USDT hoặc HOME/USDT:USDT → HOME/USDT
                            symbol_normalized = symbol.replace(":USDT", "").strip()
                            data_map[symbol_normalized] = (price_sl, price_tp, status, col_m, col_n, col_o)
                            logger.debug(f"Lưu dữ liệu cho {symbol_normalized}: SL={price_sl}, TP={price_tp}, Status={status}, M={col_m}, N={col_n}, O={col_o}")
                
                print(f"    ✅ Đã đọc {len(data_map)} symbols từ dữ liệu cũ", flush=True)
                logger.info(f"Đã đọc {len(data_map)} symbols từ dữ liệu cũ (bao gồm M, N, O)")
            else:
                print("    ℹ️  Không có dữ liệu cũ", flush=True)
                
        except Exception as e:
            print(f"    ⚠️  Lỗi khi đọc dữ liệu cũ: {e} (tiếp tục không merge)", flush=True)
            logger.warning(f"Lỗi đọc dữ liệu cũ để merge: {e}", exc_info=True)
        
        # ✅ BƯỚC 5.2: MERGE GIÁ KÍCH HOẠT SL/TP (J, K), TRẠNG THÁI (L) và cột M, N, O vào dữ liệu mới
        if data_map:
            print("  🔄 Merge giá kích hoạt SL/TP (J, K), trạng thái (L) và cột M, N, O vào dữ liệu mới...", flush=True)
            merged_count = 0
            
            for i, row in enumerate(tab_100_ma_2d_arr):
                if len(row) >= 12:  # Đảm bảo row có đủ 12 cột
                    symbol = str(row[0]).strip() if row[0] else ""
                    # Chuẩn hóa symbol để so sánh
                    symbol_normalized = symbol.replace(":USDT", "").strip()
                    
                    # Check xem symbol có trong data_map không
                    if symbol_normalized in data_map:
                        price_sl, price_tp, status, col_m, col_n, col_o = data_map[symbol_normalized]
                        # Update row: giữ nguyên các cột A-L, update M, N, O
                        row_list = list(row)
                        
                        # Đảm bảo row_list có đủ 16 cột (A-P)
                        while len(row_list) < 16:
                            row_list.append("")  # Thêm cột rỗng nếu thiếu
                        
                        # ✅ Update cột J, K (giá kích hoạt SL/TP) - CHỈ merge nếu có giá trị (không rỗng)
                        if price_sl:  # Chỉ merge nếu price_sl không rỗng
                            row_list[9] = price_sl   # Cột J: Giá kích hoạt SL
                        if price_tp:  # Chỉ merge nếu price_tp không rỗng
                            row_list[10] = price_tp  # Cột K: Giá kích hoạt TP
                        if status:  # Chỉ merge nếu status không rỗng
                            row_list[11] = status  # Cột L: Trạng thái Y/N
                        
                        # Giữ lại cột M, N, O (tick xóa lệnh)
                        if col_m:
                            row_list[12] = col_m  # Cột M: Tick xóa lệnh 1
                        if col_n:
                            row_list[13] = col_n  # Cột N: Tick xóa cặp 2-3
                        if col_o:
                            row_list[14] = col_o  # Cột O: Tick xóa lệnh đơn
                        
                        tab_100_ma_2d_arr[i] = tuple(row_list)
                        merged_count += 1
                        logger.debug(f"Merged cho {symbol_normalized}: SL={price_sl}, TP={price_tp}, Status={status}, M={col_m}, N={col_n}, O={col_o}")
            
            print(f"    ✅ Đã merge giá kích hoạt (J/K), trạng thái (L) và cột M, N, O cho {merged_count} symbols", flush=True)
            logger.info(f"Đã merge giá kích hoạt (J/K), trạng thái (L) và cột M, N, O cho {merged_count} symbols từ dữ liệu cũ")
        
        # ✅ Clear dữ liệu cũ CHỈ từ cột A-L (KHÔNG xóa cột M, N, O - giữ lại tick xóa lệnh)
        print("  🗑️  Xóa dữ liệu cũ (chỉ cột A-L, giữ nguyên M, N, O)...", flush=True)
        # Clear từ cột A đến L (end_column="L") - Giữ nguyên M, N, O
        gg_sheet_factory.clear_multi(gg_sheet_factory.tab_cho_va_khop, 2, "a", end_row=1000, end_column="L")
        
        # Ghi timestamp vào A2
        timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"  📅 Cập nhật timestamp vào A2: {timestamp_str}", flush=True)
        gg_sheet_factory.update_single_value(gg_sheet_factory.tab_cho_va_khop, "A2", timestamp_str)
        
        # Update dữ liệu mới (bắt đầu từ hàng 2, đã có rate merged)
        print("  ✍️  Ghi dữ liệu mới (đã merge rate)...", flush=True)
        gg_sheet_factory.update_multi(gg_sheet_factory.tab_cho_va_khop, 2, tab_100_ma_2d_arr, "a")
        
        print(f"✅ Hoàn thành! Đã cập nhật {len(tab_100_ma_2d_arr)} dòng vào sheet (đã giữ lại rate)", flush=True)
        logger.info(f"✅ Hoàn thành cập nhật sheet: {len(tab_100_ma_2d_arr)} dòng (đã merge rate)")
        
    except HttpError as e:
        # ✅ Xử lý đặc biệt cho lỗi 403 (Permission denied)
        if e.resp.status == 403:
            error_msg = f"❌ Lỗi 403 - Permission denied khi cập nhật sheet: {e}"
            print(error_msg, flush=True)
            logger.error(error_msg, exc_info=True)
            print("⚠️  Lưu ý: Token có thể đã hết hạn hoặc không có quyền truy cập sheet", flush=True)
            print("   Bot sẽ tự động thử refresh token ở lần scan tiếp theo", flush=True)
            logger.warning("Lỗi 403 - Bot sẽ thử lại ở lần scan tiếp theo sau khi refresh token")
        else:
            error_msg = f"❌ HttpError (status {e.resp.status}) khi cập nhật sheet: {e}"
            print(error_msg, flush=True)
            logger.error(error_msg, exc_info=True)
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
