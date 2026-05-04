import cst
from enum import Enum
import gg_sheet_factory
import threading
import logging
import subprocess
import time
import os
import sys
import ccxt
from datetime import datetime
import binance_utils
import telegram_factory
from pathlib import Path
from binance_order_helper import BinanceOrderHelper
from cascade_manager import CascadeManager, get_cascade_manager
from notification_manager import NotificationManager, get_notification_manager
import requests
import hmac
import hashlib
import urllib.parse

# --- CẤU HÌNH HỆ THỐNG & LOGGING ---
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

file_name = os.path.basename(os.path.abspath(__file__))  
os.system(f"title {file_name} - {cst.key_name}")

# Tạo thư mục logs/ nếu chưa có
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

log_timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
log_filename = logs_dir / f'hd_order_123_{log_timestamp}.txt'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
console_handler.setLevel(logging.INFO)

logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.propagate = False

order_logger = logging.getLogger('order')
order_logger.setLevel(logging.INFO)
order_log_path = logs_dir / 'order.log'
order_handler = logging.FileHandler(order_log_path, encoding='utf-8')
order_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
order_logger.addHandler(order_handler)

STATE_SHORT = "SHORT"
STATE_LONG  = "LONG"

# --- CÁC HÀM TIỆN ÍCH ---

def is_same_pair(sym1, sym2):
    sym1 = sym1.replace("/", "").upper().strip()
    sym2 = sym2.replace("/", "").upper().strip()
    if sym1 == sym2 :
       return True
    return False

def parse_multi_layer_sl_tp_from_sheet(symbol, side, row_data, entry_price):
    """
    [TASK 1] Đọc 3 lớp SL/TP + tỉ lệ từ sheet "Chờ và khớp" (layout 23 cột A-W).

    Layout dùng:
      J (idx 9)  = % lớp 1  (default 40)
      K (idx 10) = % lớp 2  (default 40)
      L (idx 11) = % lớp 3  (default 20)
      M (idx 12) = Giá SL1
      N (idx 13) = Giá SL2
      O (idx 14) = Giá SL3
      P (idx 15) = Giá TP1
      Q (idx 16) = Giá TP2
      R (idx 17) = Giá TP3

    Args:
        symbol, side: để log
        row_data: list dữ liệu từ sheet
        entry_price: để validate hợp lệ giá

    Returns:
        dict {
            'sl_prices': [sl1, sl2, sl3] (None nếu user không nhập hoặc không hợp lệ),
            'tp_prices': [tp1, tp2, tp3] (tương tự),
            'ratios':    [r1, r2, r3]   (% lớp, mặc định 40/40/20),
            'has_sl': True nếu có ít nhất 1 SL price hợp lệ,
            'has_tp': tương tự,
        }
    """
    DEFAULT_RATIOS = [40.0, 40.0, 20.0]

    def _parse_float(idx, label):
        if len(row_data) <= idx or not row_data[idx]:
            return None
        raw = str(row_data[idx]).strip().replace(",", ".")
        if not raw or raw in ("0", "0.0"):
            return None
        try:
            v = float(raw)
            return v if v > 0 else None
        except (ValueError, TypeError):
            logger.debug(f"{symbol}: Cột {label} không phải số: '{raw}'")
            return None

    # --- Tỉ lệ J/K/L ---
    r1 = _parse_float(9, "J (% lớp 1)") or DEFAULT_RATIOS[0]
    r2 = _parse_float(10, "K (% lớp 2)") or DEFAULT_RATIOS[1]
    r3 = _parse_float(11, "L (% lớp 3)")
    if r3 is None:
        # Tự tính nếu rỗng: = 100 - r1 - r2 (cap >= 0)
        r3 = max(0.0, 100.0 - r1 - r2)
    ratios = [r1, r2, r3]

    # --- Giá SL1/2/3 ---
    sl_prices = [_parse_float(12, "M (SL1)"), _parse_float(13, "N (SL2)"), _parse_float(14, "O (SL3)")]
    # --- Giá TP1/2/3 ---
    tp_prices = [_parse_float(15, "P (TP1)"), _parse_float(16, "Q (TP2)"), _parse_float(17, "R (TP3)")]

    # Validate từng SL theo side (SL LONG < entry, SL SHORT > entry)
    is_long = (side == STATE_LONG)
    for i, v in enumerate(sl_prices):
        if v is None:
            continue
        if is_long and v >= entry_price:
            logger.warning(f"{symbol}: SL{i+1}={v} >= entry={entry_price} cho LONG — bỏ qua")
            sl_prices[i] = None
        elif (not is_long) and v <= entry_price:
            logger.warning(f"{symbol}: SL{i+1}={v} <= entry={entry_price} cho SHORT — bỏ qua")
            sl_prices[i] = None

    # Validate từng TP theo side (TP LONG > entry, TP SHORT < entry)
    for i, v in enumerate(tp_prices):
        if v is None:
            continue
        if is_long and v <= entry_price:
            logger.warning(f"{symbol}: TP{i+1}={v} <= entry={entry_price} cho LONG — bỏ qua")
            tp_prices[i] = None
        elif (not is_long) and v >= entry_price:
            logger.warning(f"{symbol}: TP{i+1}={v} >= entry={entry_price} cho SHORT — bỏ qua")
            tp_prices[i] = None

    has_sl = any(p is not None for p in sl_prices)
    has_tp = any(p is not None for p in tp_prices)

    logger.info(
        f"{symbol} ({side}) Entry={entry_price} | "
        f"SL={sl_prices} TP={tp_prices} | Ratios={ratios} | has_sl={has_sl} has_tp={has_tp}"
    )
    return {
        'sl_prices': sl_prices,
        'tp_prices': tp_prices,
        'ratios': ratios,
        'has_sl': has_sl,
        'has_tp': has_tp,
    }


def get_sl_tp_activation_price_from_cho_va_khop(symbol, side, row_data, entry_price):
    """
    [DEPRECATED — giữ lại cho tham chiếu] Lấy 1 giá SL/TP từ sheet cũ (J, K).
    Code mới dùng parse_multi_layer_sl_tp_from_sheet().
    """
    # Config mặc định (fallback)
    if side == STATE_LONG:
        default_sl = cst.lenh2_rate_long
        default_tp = cst.lenh3_rate_long
    else:
        default_sl = cst.lenh2_rate_short
        default_tp = cst.lenh3_rate_short
    
    # Khởi tạo với giá trị mặc định
    sl_rate = default_sl
    tp_rate = default_tp
    sl_activation_price = None
    tp_activation_price = None
    
    sl_source = "Config"
    tp_source = "Config"
    
    try:
        # Cột J (index 9) - Giá kích hoạt SL
        if len(row_data) > 9 and row_data[9]:
            val = str(row_data[9]).strip()
            if val and val not in ["", "0", "0.0"]:
                try:
                    sl_activation_price = float(val)
                    # Tính rate từ giá kích hoạt (có xét LONG/SHORT)
                    if entry_price > 0:
                        if side == STATE_LONG:
                            # LONG: SL < Entry → rate = (entry - sl) / entry * 100
                            if sl_activation_price < entry_price:
                                sl_rate = (entry_price - sl_activation_price) / entry_price * 100
                            else:
                                logger.warning(f"{symbol}: SL ({sl_activation_price}) >= Entry ({entry_price}) cho LONG - không hợp lệ!")
                                sl_rate = default_sl
                        else:
                            # SHORT: SL > Entry → rate = (sl - entry) / entry * 100
                            if sl_activation_price > entry_price:
                                sl_rate = (sl_activation_price - entry_price) / entry_price * 100
                            else:
                                logger.warning(f"{symbol}: SL ({sl_activation_price}) <= Entry ({entry_price}) cho SHORT - không hợp lệ!")
                                sl_rate = default_sl
                        
                        if sl_rate > 0:
                            sl_source = "Sheet (từ giá kích hoạt)"
                            logger.debug(f"{symbol}: Giá kích hoạt SL từ cột J = {sl_activation_price}, Rate = {sl_rate}% (Side: {side})")
                        else:
                            logger.warning(f"{symbol}: Rate SL tính được = {sl_rate}% <= 0, dùng default {default_sl}%")
                            sl_rate = default_sl
                except (ValueError, TypeError) as e:
                    logger.debug(f"{symbol}: Lỗi parse giá kích hoạt SL từ sheet cột J: {e}")
    except Exception as e:
        logger.debug(f"{symbol}: Lỗi đọc giá kích hoạt SL từ sheet cột J: {e}")
    
    try:
        # Cột K (index 10) - Giá kích hoạt TP
        if len(row_data) > 10 and row_data[10]:
            val = str(row_data[10]).strip()
            if val and val not in ["", "0", "0.0"]:
                try:
                    tp_activation_price = float(val)
                    # Tính rate từ giá kích hoạt (có xét LONG/SHORT)
                    if entry_price > 0:
                        if side == STATE_LONG:
                            # LONG: TP > Entry → rate = (tp - entry) / entry * 100
                            if tp_activation_price > entry_price:
                                tp_rate = (tp_activation_price - entry_price) / entry_price * 100
                            else:
                                logger.warning(f"{symbol}: TP ({tp_activation_price}) <= Entry ({entry_price}) cho LONG - không hợp lệ!")
                                tp_rate = default_tp
                        else:
                            # SHORT: TP < Entry → rate = (entry - tp) / entry * 100
                            if tp_activation_price < entry_price:
                                tp_rate = (entry_price - tp_activation_price) / entry_price * 100
                            else:
                                logger.warning(f"{symbol}: TP ({tp_activation_price}) >= Entry ({entry_price}) cho SHORT - không hợp lệ!")
                                tp_rate = default_tp
                        
                        if tp_rate > 0:
                            tp_source = "Sheet (từ giá kích hoạt)"
                            logger.debug(f"{symbol}: Giá kích hoạt TP từ cột K = {tp_activation_price}, Rate = {tp_rate}% (Side: {side})")
                        else:
                            logger.warning(f"{symbol}: Rate TP tính được = {tp_rate}% <= 0, dùng default {default_tp}%")
                            tp_rate = default_tp
                except (ValueError, TypeError) as e:
                    logger.debug(f"{symbol}: Lỗi parse giá kích hoạt TP từ sheet cột K: {e}")
    except Exception as e:
        logger.debug(f"{symbol}: Lỗi đọc giá kích hoạt TP từ sheet cột K: {e}")
    
    logger.info(f"{symbol}: Rate SL={sl_rate}% ({sl_source}), TP={tp_rate}% ({tp_source})")
    if sl_activation_price:
        logger.info(f"{symbol}: Giá kích hoạt SL={sl_activation_price}")
    if tp_activation_price:
        logger.info(f"{symbol}: Giá kích hoạt TP={tp_activation_price}")
    
    return sl_rate, tp_rate, f"SL from {sl_source}, TP from {tp_source}", sl_activation_price, tp_activation_price

def call_binance_api_direct(method, endpoint, params=None, api_key=None, secret_key=None):
    base_url = 'https://fapi.binance.com'
    url = f"{base_url}{endpoint}"
    if params is None: params = {}
    if api_key is None: api_key = cst.key_binance
    if secret_key is None: secret_key = cst.secret_binance
    
    params['timestamp'] = int(time.time() * 1000)
    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    params['signature'] = signature
    headers = {'X-MBX-APIKEY': api_key}
    
    try:
        if method.upper() == 'GET':
            response = requests.get(url, params=params, headers=headers, timeout=10)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, params=params, headers=headers, timeout=10)
        else:
            return None
            
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Lỗi khi gọi Binance API trực tiếp ({method} {endpoint}): {e}")
        return None

def get_algo_orders_for_symbol(symbol):
    """
    Returns:
        None  → API thực sự lỗi (không xác định được trạng thái)
        []    → API thành công, không có orders
        [..] → API thành công, có danh sách orders
    """
    try:
        symbol_clean = symbol.replace('/', '').replace(':USDT', '').upper()

        if '-' in symbol_clean:
            logger.debug(f"Bỏ qua delivery futures symbol: {symbol_clean}")
            return []

        params = {'symbol': symbol_clean}
        logger.debug(f"Lấy algo orders cho {symbol} (cleaned: {symbol_clean})")
        response = call_binance_api_direct('GET', '/fapi/v1/allAlgoOrders', params)

        # [Bug 5 FIX] None = API thực sự lỗi (khác [] = thành công nhưng không có order)
        if response is None:
            return None

        if isinstance(response, list): return response
        elif isinstance(response, dict):
            if 'data' in response: return response['data']
            elif response.get('code') == 200: return []
            else:
                logger.warning(f"Response code khác 200 cho {symbol}: {response}")
                return None  # Không chắc chắn → None để caller xử lý an toàn
        else:
            logger.warning(f"Response format không đúng cho {symbol}: {type(response)}")
            return None
    except Exception as e:
        if '400' in str(e):
            logger.debug(f"Lỗi 400 cho {symbol} - có thể là delivery futures, bỏ qua")
            return []
        else:
            logger.error(f"Lỗi khi lấy algo orders: {e}", exc_info=True)
        return None

def cancel_all_algo_orders_direct(symbol):
    try:
        active_orders = get_algo_orders_for_symbol(symbol)
        pending_orders = [o for o in active_orders if o.get('algoStatus') == 'NEW']
        
        if not pending_orders: return True
            
        logger.info(f"Tìm thấy {len(pending_orders)} Algo Orders cần hủy cho {symbol}")
        
        count = 0
        failed_orders = []

        for order in pending_orders:
            algo_id = order.get('algoId')
            if algo_id:
                # ✅ [FIX] Binance API yêu cầu symbol format: HOMEUSDT (không có / và :USDT)
                symbol_clean = symbol.replace('/', '').replace(':USDT', '').upper()
                params = {'symbol': symbol_clean, 'algoId': algo_id}
                response = call_binance_api_direct('DELETE', '/fapi/v1/algoOrder', params)
                
                is_success = False
                if response:
                    code = response.get('code')
                    if str(code) == '200': is_success = True
                
                if is_success: count += 1
                else: failed_orders.append(algo_id)

        logger.info(f"Đã hủy thành công {count}/{len(pending_orders)} lệnh Algo cho {symbol}")
        
        if failed_orders:
            msg = f"⚠️ <b>CẢNH BÁO</b>\n\nKhông thể hủy {len(failed_orders)} lệnh Algo của {symbol}."
            telegram_factory.send_tele(msg, cst.chat_id, True, True)
            return False 

        return True
    except Exception as e:
        logger.error(f"Lỗi hủy Algo Orders {symbol}: {e}")
        return False

def has_sl_tp_orders(symbol, exchange):
    try:
        algo_orders = get_algo_orders_for_symbol(symbol)

        # [Bug 5 FIX] None = API lỗi → chặn tạo lệnh để tránh trùng (safety first)
        if algo_orders is None:
            logger.warning(f"⚠️ {symbol}: API lỗi khi lấy algo orders → Chặn tạo lệnh (safety first)")
            return True, True

        try: open_orders = exchange.fetch_open_orders(symbol)
        except: open_orders = []
            
        has_sl = False
        has_tp = False
        
        # --- 1. QUÉT ALGO ORDERS ---
        # [Bug C FIX] Bắt cả TRIGGERED (TP đã kích hoạt nhưng chưa fill)
        active_algo_orders = [o for o in algo_orders if o.get('algoStatus', '').upper() in ('NEW', 'TRIGGERED')]
        
        for order in active_algo_orders:
            algo_type = order.get('algoType', '').upper()
            reduce_only = order.get('reduceOnly', False)
            
            # Lấy callbackRate để phân biệt
            callback_rate = order.get('callbackRate')
            
            # Xử lý giá trị callbackRate an toàn
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
                
                # == KIỂM TRA SL (Stop Limit/Market) ==
                if algo_type in ['STOP', 'STOP_MARKET', 'STOP_LOSS', 'STOP_LOSS_MARKET', 'STOP_LIMIT']:
                    has_sl = True
                elif algo_type == 'CONDITIONAL' and callback_val == 0:
                    has_sl = True

        # --- 2. QUÉT OPEN ORDERS ---
        if not has_sl:
            for order in open_orders:
                order_type = order.get('type', '').upper()
                info = order.get('info', {})
                reduce_only = order.get('reduceOnly', False) or info.get('reduceOnly', False)
                if order_type in ['STOP', 'STOP_LIMIT', 'STOP_MARKET'] and reduce_only:
                    has_sl = True

        return has_sl, has_tp
        
    except Exception as e:
        # ✅ [FIX BUG] Khi lỗi API, KHÔNG return False ngay (sẽ tạo lệnh trùng)
        # Thay vào đó, log error và return True, True để CHẶN tạo lệnh (an toàn hơn)
        logger.error(f"❌ Lỗi check SL/TP cho {symbol}: {e}", exc_info=True)
        logger.warning(f"⚠️ {symbol}: Lỗi API khi check SL/TP → Chặn tạo lệnh để tránh trùng (safety first)")
        # Return True, True để CHẶN tạo lệnh khi không chắc chắn (tránh tạo trùng)
        return True, True  # ✅ Safety first - Chặn tạo lệnh khi không check được

# --- HÀM HỖ TRỢ ---

def get_position_amount_from_binance(symbol):
    """
    Lấy position amount từ Binance cho symbol cụ thể
    Dùng để tính toán SL/TP amount
    
    Returns: 
        (position_amt, entry_price) hoặc (None, None) nếu không có position
    """
    try:
        positions = exchange.fetch_positions([symbol])
        for position in positions:
            try:
                amount = float(position.get('contracts', 0))
            except:
                amount = 0.0
            
            if amount != 0:
                position_side = position.get('side', '').lower()
                is_long = (position_side == 'long')
                
                # Lấy entry price (để verify với sheet)
                entry_price_raw = position.get('entryPrice', 0)
                entry_price = float(entry_price_raw) if entry_price_raw else 0.0
                
                # CCXT contracts luôn dương, cần thêm dấu dựa vào side
                position_amt_rounded = float(exchange.amount_to_precision(symbol, amount))
                position_amt = position_amt_rounded if is_long else -position_amt_rounded
                
                logger.debug(f"{symbol}: Position amount = {position_amt}, Entry = {entry_price}")
                return position_amt, entry_price
        
        return None, None
    except Exception as e:
        logger.error(f"Lỗi lấy position amount cho {symbol}: {e}")
        return None, None

# --- KHỞI TẠO EXCHANGE ---
logger.info(f"{datetime.now()}. Khởi tạo Bot -------------------------")
exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'enableRateLimit': True,  
    'apiKey': cst.key_binance,
    'secret': cst.secret_binance,
    'options': {'defaultType': 'future'}
})
exchange.setSandboxMode(False)

# [FIX 1 - QUAN TRỌNG] Tải thông tin thị trường để lấy Precision rule (tránh lỗi -1111)
print("⏳ Đang cập nhật thông tin thị trường (Precision/TickSize)...", flush=True)
try:
    exchange.load_markets(True) # Force reload
    print("✅ Đã cập nhật xong thông tin thị trường.", flush=True)
except Exception as e:
    print(f"⚠️ Lỗi cập nhật markets: {e}", flush=True)

order_helper = BinanceOrderHelper(exchange)
cascade_mgr = get_cascade_manager(exchange, order_helper)


# --- LOGIC CHÍNH MỚI: ĐỌC TỪ SHEET "CHỜ VÀ KHỚP" ---

def do_it():
    logger.info(f"{datetime.now()}. Scan Lệnh 123 - Đọc từ Sheet 'Chờ và khớp' -------------------------")
    
    # [TASK 1] Đọc sheet "Chờ và khớp" với layout mới 23 cột (A-W)
    try:
        sheet_data = gg_sheet_factory.get_cho_va_khop("A4:W1000")
        logger.info(f"✅ Đã đọc {len(sheet_data)} dòng từ sheet 'Chờ và khớp' (23 cột A-W)")
    except Exception as e:
        logger.error(f"❌ Lỗi khi đọc sheet 'Chờ và khớp': {e}")
        return
    
    processed_count = 0
    
    for row in sheet_data:
        try:
            # [BƯỚC 1] PARSE DỮ LIỆU TỪ SHEET
            if len(row) < 4:
                continue  # Dòng không đủ dữ liệu tối thiểu
            
            # Cột A: Symbol
            symbol_raw = row[0] if len(row) > 0 else None
            if not symbol_raw:
                continue
            symbol = str(symbol_raw).strip()
            
            # ✅ Chuẩn hóa symbol format cho CCXT Binance Futures (HOME/USDT -> HOME/USDT:USDT)
            if ':USDT' not in symbol:
                # Nếu chưa có :USDT, thêm vào
                if symbol.endswith('/USDT'):
                    symbol = f"{symbol}:USDT"
                elif symbol.endswith('USDT'):
                    # HOMEUSDT -> HOME/USDT:USDT
                    base = symbol[:-4]
                    symbol = f"{base}/USDT:USDT"
                else:
                    # HOME -> HOME/USDT:USDT
                    symbol = f"{symbol}/USDT:USDT"
            
            # Cột B: Vị thế (LONG/SHORT)
            side_raw = row[1] if len(row) > 1 else None
            if not side_raw:
                continue
            side = str(side_raw).strip().upper()
            
            # Validate side
            if side not in [STATE_LONG, STATE_SHORT]:
                logger.warning(f"{symbol}: Side không hợp lệ: {side}")
                continue
            
            # Cột C: Chờ khớp (Y/N)
            cho_khop = str(row[2]).strip().upper() if len(row) > 2 else "N"
            
            # Cột D: Trạng thái (Y/N/ĐÓNG) - chỉ xử lý "Y" (position đang mở)
            da_khop = str(row[3]).strip().upper() if len(row) > 3 else "N"
            
            # [ĐIỀU KIỆN 1] Chỉ xử lý "Y" (position đang mở). Bỏ qua "N" (chờ) và "ĐÓNG"
            if da_khop != "Y":
                continue
            
            # Cột E: Giá vào
            try:
                entry_price = float(row[4]) if len(row) > 4 and row[4] else 0.0
            except:
                entry_price = 0.0
            
            if entry_price <= 0:
                logger.warning(f"{symbol}: Entry price = {entry_price} (không hợp lệ), bỏ qua")
                continue
            
            # Cột F: Đòn bẩy
            try:
                leverage_raw = row[5] if len(row) > 5 and row[5] else "1"
                if str(leverage_raw).strip().upper() == "N":
                    leverage = 1
                else:
                    leverage = int(float(leverage_raw))
            except:
                leverage = 1
            
            # Cột G: Lệnh Stop Limit (Y/N) - từ sheet (chỉ để reference)
            has_sl_sheet = str(row[6]).strip().upper() == "Y" if len(row) > 6 else False
            
            # Cột H: Lệnh Trailing Stop (Y/N) - từ sheet (chỉ để reference)
            has_tp_sheet = str(row[7]).strip().upper() == "Y" if len(row) > 7 else False
            
            # ✅ [FIX BUG LẶP ĐƠN] KIỂM TRA THỰC TẾ TRÊN BINANCE (không chỉ dựa vào sheet!)
            # Sheet có thể bị cập nhật chậm hoặc bị clear → PHẢI check Binance thực tế
            try:
                has_sl_binance, has_tp_binance = has_sl_tp_orders(symbol, exchange)
                logger.debug(f"{symbol}: Binance check - SL: {has_sl_binance}, TP: {has_tp_binance} | Sheet - SL: {has_sl_sheet}, TP: {has_tp_sheet}")
            except Exception as e:
                logger.error(f"❌ {symbol}: Lỗi khi check SL/TP trên Binance: {e}", exc_info=True)
                # Nếu lỗi check Binance, fallback về sheet (nhưng cảnh báo)
                logger.warning(f"⚠️ {symbol}: Fallback về sheet check do lỗi Binance API")
                has_sl_binance = has_sl_sheet
                has_tp_binance = has_tp_sheet
            
            # [ĐIỀU KIỆN 2] Chỉ xử lý nếu THIẾU SL hoặc THIẾU TP (dựa vào BINANCE thực tế!)
            need_sl = not has_sl_binance
            need_tp = not has_tp_binance
            
            # ✅ Kiểm tra conflict giữa Sheet và Binance
            if has_sl_sheet != has_sl_binance:
                logger.warning(f"⚠️ {symbol}: Sheet vs Binance - SL mismatch! Sheet={has_sl_sheet}, Binance={has_sl_binance}")
            if has_tp_sheet != has_tp_binance:
                logger.warning(f"⚠️ {symbol}: Sheet vs Binance - TP mismatch! Sheet={has_tp_sheet}, Binance={has_tp_binance}")
            
            if not need_sl and not need_tp:
                # Đã đủ cả 2 trên Binance → Bỏ qua (không tạo lệnh trùng)
                logger.debug(f"{symbol}: Đã có đủ SL và TP trên Binance, bỏ qua")
                continue
            
            # ✅ [ĐIỀU KIỆN 3] KIỂM TRA TRẠNG THÁI CHO PHÉP ĐẶT LỆNH (Cột S - index 18)
            # [TASK 1] Cột L cũ (allow) đã chuyển sang cột S trong layout 23 cột
            allow_order = False
            try:
                if len(row) > 18 and row[18]:
                    status_str = str(row[18]).strip().upper()
                    allow_order = (status_str == "Y")
                    if allow_order:
                        logger.info(f"{symbol}: Cột S = '{status_str}' → Cho phép đặt lệnh")
                    else:
                        logger.info(f"{symbol}: Cột S = '{status_str}' (không phải Y) → Bỏ qua")
                else:
                    logger.info(f"{symbol}: Cột S rỗng → Bỏ qua, không đặt lệnh")
            except Exception as e:
                logger.warning(f"{symbol}: Lỗi đọc cột S: {e} → Bỏ qua (safety first)")
                allow_order = False
            
            if not allow_order:
                continue
            
            print(f"🔍 Xử lý: {symbol} | Side: {side} | Entry: {entry_price} | Need SL: {need_sl}, TP: {need_tp}", flush=True)
            
            # [TASK 1 - BƯỚC 2] ĐỌC 3 LỚP SL/TP + TỈ LỆ TỪ SHEET (cột J-R)
            multi = parse_multi_layer_sl_tp_from_sheet(symbol, side, row, entry_price)
            sl_prices = multi['sl_prices']  # [sl1, sl2, sl3]
            tp_prices = multi['tp_prices']  # [tp1, tp2, tp3]
            ratios = multi['ratios']        # [r1, r2, r3] (%)
            has_sl_input = multi['has_sl']
            has_tp_input = multi['has_tp']

            # Nếu cần SL nhưng không có giá SL nào trong sheet → skip
            if need_sl and not has_sl_input:
                logger.warning(f"⚠️ {symbol}: Cần SL nhưng không có giá SL trong sheet (M/N/O rỗng), bỏ qua")
                continue
            if need_tp and not has_tp_input:
                logger.warning(f"⚠️ {symbol}: Cần TP nhưng không có giá TP trong sheet (P/Q/R rỗng), bỏ qua")
                continue

            # [BƯỚC 3] LẤY POSITION AMOUNT TỪ BINANCE
            position_amt, entry_price_binance = get_position_amount_from_binance(symbol)
            
            if position_amt is None:
                logger.warning(f"⚠️ {symbol}: Không tìm thấy position trên Binance")
                continue
            
            if entry_price_binance and abs(entry_price_binance - entry_price) / entry_price > 0.01:
                logger.warning(f"⚠️ {symbol}: Entry price Sheet={entry_price} vs Binance={entry_price_binance} (chênh >1%)")

            # [TASK 1 - BƯỚC 4] TẠO 3 LỚP SL + 3 LỚP TP
            print(f"🎯 Multi-layer: {symbol} | SL={sl_prices} TP={tp_prices} ratios={ratios}% | need_sl={need_sl} need_tp={need_tp}", flush=True)

            try:
                result = cascade_mgr.on_entry_filled_multi_layer(
                    symbol=symbol,
                    entry_price=entry_price,
                    leverage=leverage,
                    position_amt=position_amt,
                    side=side,
                    sl_prices=sl_prices,
                    tp_prices=tp_prices,
                    ratios=ratios,
                    callback_rate=cst.lenh3_callback_rate,
                    skip_sl=not need_sl,   # Đã có SL → bỏ qua 3 lớp SL
                    skip_tp=not need_tp,   # Đã có TP → bỏ qua 3 lớp TP
                )

                sl_orders = result['sl_orders']  # list 3 phần tử
                tp_orders = result['tp_orders']
                errors = result.get('errors', [])

                sl_ids = [str(o.get('id', 'N/A')) for o in sl_orders if o]
                tp_ids = [str(o.get('id', 'N/A')) for o in tp_orders if o]
                created_parts = []
                if sl_ids:
                    created_parts.append(f"SL×{len(sl_ids)}: {', '.join(sl_ids)}")
                    for i, o in enumerate(sl_orders):
                        if o:
                            order_logger.info(f"LỆNH 2 (SL{i+1}) | {symbol} | {side} | Entry: {entry_price} | Price: {sl_prices[i]} | Ratio: {ratios[i]}% | OrderID: {o.get('id')}")
                if tp_ids:
                    created_parts.append(f"TP×{len(tp_ids)}: {', '.join(tp_ids)}")
                    for i, o in enumerate(tp_orders):
                        if o:
                            order_logger.info(f"LỆNH 3 (TP{i+1}) | {symbol} | {side} | Entry: {entry_price} | Price: {tp_prices[i]} | Ratio: {ratios[i]}% | OrderID: {o.get('id')}")

                if sl_ids or tp_ids:
                    print(f"✅ Đã tạo: {' | '.join(created_parts)} cho {symbol}", flush=True)
                    msg_parts = [
                        f"✅ <b>ĐÃ TẠO LỆNH 3 LỚP</b>", "",
                        f"<b>Mã:</b> {symbol}",
                        f"<b>Side:</b> {side}",
                        f"<b>Entry:</b> {entry_price}",
                        f"<b>Tỉ lệ:</b> {ratios[0]:.0f}/{ratios[1]:.0f}/{ratios[2]:.0f}%",
                    ]
                    if need_sl and sl_prices:
                        sl_summary = ", ".join([f"{p}" if p else "(rỗng)" for p in sl_prices])
                        msg_parts.append(f"<b>SL:</b> [{sl_summary}] → Tạo {len(sl_ids)}/3 lệnh")
                    if need_tp and tp_prices:
                        tp_summary = ", ".join([f"{p}" if p else "(rỗng)" for p in tp_prices])
                        msg_parts.append(f"<b>TP:</b> [{tp_summary}] → Tạo {len(tp_ids)}/3 lệnh")
                    if errors:
                        msg_parts.append(f"<b>⚠ Lỗi:</b> {len(errors)} lớp thất bại")
                    msg = "\n".join(msg_parts)
                    try:
                        telegram_factory.send_tele(msg, cst.chat_id, True, True)
                    except Exception as tele_error:
                        logger.error(f"❌ Lỗi gửi Telegram: {tele_error}", exc_info=True)
                    processed_count += 1
                else:
                    logger.warning(f"⚠️ {symbol}: Không tạo được lệnh nào | errors={errors}")
                    err_summary = " | ".join(errors[:3]) if errors else "không rõ"
                    msg = f"⚠️ <b>KHÔNG TẠO ĐƯỢC LỆNH</b>\n\n<b>Mã:</b> {symbol}\n<b>Side:</b> {side}\n<b>Entry:</b> {entry_price}\n<b>Lỗi:</b> {err_summary}"
                    try:
                        telegram_factory.send_tele(msg, cst.chat_id, True, True)
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"❌ Lỗi tạo multi-layer cho {symbol}: {e}", exc_info=True)
                msg = f"🚨 <b>LỖI TẠO LỆNH MULTI-LAYER</b>\n\n<b>Mã:</b> {symbol}\n<b>Lỗi:</b> {str(e)}"
                try:
                    telegram_factory.send_tele(msg, cst.chat_id, True, True)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"❌ Lỗi xử lý dòng sheet: {e}", exc_info=True)
    
    # Tổng kết
    logger.info(f"✅ Hoàn thành scan - Đã xử lý {processed_count} symbol")

while True:
    try:
        do_it()
        sys.stdout.flush()
    except Exception as e:
        print(f"Tổng Lỗi: {e}", flush=True)
        logger.error(f"Tổng lỗi: {e}", exc_info=True)
    time.sleep(cst.delay_vao_lenh_123)