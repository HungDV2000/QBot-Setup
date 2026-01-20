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

def get_sl_tp_activation_price_from_cho_va_khop(symbol, side, row_data, entry_price):
    """
    Lấy giá kích hoạt SL/TP từ sheet "Chờ và khớp" (cột J, K)
    Tính rate từ giá kích hoạt và entry price
    
    Args:
        symbol: Symbol hiện tại
        side: "LONG" hoặc "SHORT"
        row_data: Dữ liệu dòng từ sheet (list)
        entry_price: Giá vào lệnh (để tính rate từ giá kích hoạt)
    
    Returns:
        (sl_rate, tp_rate, source_info, sl_activation_price, tp_activation_price)
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
    try:
        # ✅ [FIX BUG] Binance API yêu cầu symbol format: HOMEUSDT (không có / và :USDT)
        # HOME/USDT:USDT -> HOMEUSDT
        # HOMEUSDT:USDT -> HOMEUSDT
        symbol_clean = symbol.replace('/', '').replace(':USDT', '').upper()
        params = {'symbol': symbol_clean}
        logger.debug(f"Lấy algo orders cho {symbol} (cleaned: {symbol_clean})")
        response = call_binance_api_direct('GET', '/fapi/v1/allAlgoOrders', params)
        if not response: return []
        if isinstance(response, list): return response
        elif isinstance(response, dict):
            if 'data' in response: return response['data']
            elif response.get('code') == 200: return response
            else: return []
        else: return []
    except Exception as e:
        logger.error(f"Lỗi khi lấy algo orders: {e}", exc_info=True)
        return []

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
        try: open_orders = exchange.fetch_open_orders(symbol)
        except: open_orders = []
            
        has_sl = False
        has_tp = False
        
        # --- 1. QUÉT ALGO ORDERS ---
        active_algo_orders = [o for o in algo_orders if o.get('algoStatus', '').upper() == 'NEW']
        
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
    
    # [LOGIC MỚI] Đọc sheet "Chờ và khớp" thay vì quét Binance trực tiếp
    try:
        sheet_data = gg_sheet_factory.get_cho_va_khop("A4:L1000")  # Đọc từ hàng 4 đến 1000, cột A-L (thêm cột L: trạng thái)
        logger.info(f"✅ Đã đọc {len(sheet_data)} dòng từ sheet 'Chờ và khớp'")
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
            
            # Cột C: Chờ khớp (Y/N) - không dùng nhưng vẫn parse để log
            cho_khop = str(row[2]).strip().upper() if len(row) > 2 else "N"
            
            # Cột D: Đã khớp/Mở vị thế (Y/N) - ĐIỀU KIỆN QUAN TRỌNG
            da_khop = str(row[3]).strip().upper() if len(row) > 3 else "N"
            
            # [ĐIỀU KIỆN 1] Chỉ xử lý lệnh ĐÃ KHỚP (đã vào lệnh)
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
            
            # ✅ [ĐIỀU KIỆN 3] KIỂM TRA TRẠNG THÁI CHO PHÉP ĐẶT LỆNH (Cột L)
            # Cột L (index 11) - Trạng thái cho phép đặt lệnh (Y/N)
            # ✅ CHỈ đặt lệnh nếu cột L = "Y", nếu rỗng hoặc khác "Y" thì KHÔNG đặt
            allow_order = False  # ✅ Mặc định KHÔNG cho phép (chỉ cho phép khi L = "Y")
            try:
                if len(row) > 11 and row[11]:
                    status_str = str(row[11]).strip().upper()
                    allow_order = (status_str == "Y")
                    if allow_order:
                        logger.info(f"{symbol}: Trạng thái cột L = '{status_str}' → Cho phép đặt lệnh")
                    else:
                        logger.info(f"{symbol}: Trạng thái cột L = '{status_str}' (không phải Y) → Bỏ qua, không đặt lệnh")
                else:
                    # Cột L rỗng hoặc không tồn tại → KHÔNG cho phép
                    logger.info(f"{symbol}: Cột L rỗng hoặc không tồn tại → Bỏ qua, không đặt lệnh")
            except Exception as e:
                logger.warning(f"{symbol}: Lỗi đọc trạng thái từ cột L: {e} → Bỏ qua, không đặt lệnh (safety first)")
                allow_order = False  # ✅ Lỗi thì không cho phép (an toàn)
            
            if not allow_order:
                logger.info(f"{symbol}: Không được phép đặt lệnh (cột L ≠ Y hoặc rỗng), bỏ qua")
                continue
            
            print(f"🔍 Xử lý: {symbol} | Side: {side} | Entry: {entry_price} | Need SL: {need_sl}, TP: {need_tp}", flush=True)
            
            # [BƯỚC 2] LẤY GIÁ KÍCH HOẠT SL/TP TỪ CỘT J, K và tính rate
            sl_rate, tp_rate, rate_source, sl_activation_price, tp_activation_price = get_sl_tp_activation_price_from_cho_va_khop(symbol, side, row, entry_price)
                
            # Validate rate
            if need_sl and sl_rate <= 0:
                logger.warning(f"⚠️ {symbol}: Thiếu SL nhưng SL rate = {sl_rate} <= 0, bỏ qua")
                continue
            if need_tp and tp_rate <= 0:
                logger.warning(f"⚠️ {symbol}: Thiếu TP nhưng TP rate = {tp_rate} <= 0, bỏ qua")
                continue
            
            # [BƯỚC 3] LẤY POSITION AMOUNT TỪ BINANCE
            position_amt, entry_price_binance = get_position_amount_from_binance(symbol)
            
            if position_amt is None:
                logger.warning(f"⚠️ {symbol}: Không tìm thấy position trên Binance (sheet có thể chưa sync)")
                continue
            
            # [Optional] Verify entry price từ Binance vs Sheet (warning nếu khác)
            if entry_price_binance and abs(entry_price_binance - entry_price) / entry_price > 0.01:  # Chênh lệch > 1%
                logger.warning(f"⚠️ {symbol}: Entry price khác biệt - Sheet: {entry_price}, Binance: {entry_price_binance}")
            
            # [BƯỚC 4] ĐẶT LỆNH LẺ (có thể chỉ SL hoặc chỉ TP)
            print(f"🎯 Đặt lệnh cho {symbol} | Entry: {entry_price} | SL: {sl_rate}%, TP: {tp_rate}%", flush=True)
            
            try:
                # Gọi cascade manager với rate từ sheet
                result = cascade_mgr.on_entry_filled(
                    symbol=symbol,
                    layer_num=1,
                    entry_price=entry_price,  # Từ sheet
                    leverage=leverage,  # Từ sheet
                    position_amt=position_amt,  # Từ Binance
                    side=side,  # Từ sheet
                    max_layers=3,
                    lenh2_rate=sl_rate,  # Từ sheet cột J (mỗi symbol riêng)
                    lenh3_rate=tp_rate,  # Từ sheet cột K (mỗi symbol riêng)
                    lenh3_callback_rate=cst.lenh3_callback_rate,
                    next_layer_config=None 
                )
                
                sl_order = result.get('sl_order')
                tp_order = result.get('tp_order')
                
                # ✅ Debug: Log chi tiết để kiểm tra
                logger.debug(f"{symbol}: Result từ cascade_mgr - sl_order: {sl_order is not None}, tp_order: {tp_order is not None}")
                if sl_order:
                    logger.debug(f"{symbol}: SL order ID: {sl_order.get('id', 'N/A')}")
                if tp_order:
                    logger.debug(f"{symbol}: TP order ID: {tp_order.get('id', 'N/A')}")
                
                # Log kết quả
                orders_created = []
                order_ids = []
                
                if need_sl and sl_order:
                    sl_id = sl_order.get('id', 'N/A')
                    orders_created.append(f"SL (ID: {sl_id})")
                    order_ids.append(sl_id)
                    order_logger.info(f"LỆNH 2 (SL) | {symbol} | {side} | Entry: {entry_price} | Rate: {sl_rate}%")
                elif need_sl:
                    logger.warning(f"⚠️ {symbol}: Cần SL nhưng cascade_mgr không trả về sl_order")
                
                if need_tp and tp_order:
                    tp_id = tp_order.get('id', 'N/A')
                    orders_created.append(f"TP (ID: {tp_id})")
                    order_ids.append(tp_id)
                    order_logger.info(f"LỆNH 3 (TP) | {symbol} | {side} | Entry: {entry_price} | Rate: {tp_rate}%")
                elif need_tp:
                    logger.warning(f"⚠️ {symbol}: Cần TP nhưng cascade_mgr không trả về tp_order")
                
                # ✅ Gửi Telegram và log CHỈ KHI thực sự có orders được tạo
                if orders_created:
                    print(f"✅ Đã tạo: {', '.join(orders_created)} cho {symbol}", flush=True)
                    logger.info(f"✅ Tạo lệnh thành công cho {symbol}: {', '.join(orders_created)}")
                    
                    msg = f"✅ <b>ĐÃ TẠO LỆNH</b>\n\n<b>Mã:</b> {symbol}\n<b>Side:</b> {side}\n<b>Entry:</b> {entry_price}\n<b>Lệnh:</b> {', '.join(orders_created)}\n<b>Rate:</b> SL {sl_rate}%, TP {tp_rate}%"
                    
                    # ✅ Gửi Telegram với try-catch để đảm bảo không bị lỗi im lặng
                    try:
                        telegram_factory.send_tele(msg, cst.chat_id, True, True)
                        logger.info(f"✅ Đã gửi Telegram cho {symbol}")
                    except Exception as tele_error:
                        logger.error(f"❌ Lỗi gửi Telegram cho {symbol}: {tele_error}", exc_info=True)
                        # Vẫn tiếp tục, không block việc xử lý
                    
                    processed_count += 1
                else:
                    # ✅ Log chi tiết khi không có orders được tạo
                    logger.warning(f"⚠️ {symbol}: Không có lệnh nào được tạo - need_sl={need_sl}, need_tp={need_tp}, sl_order={sl_order is not None}, tp_order={tp_order is not None}")
                    # ✅ Vẫn gửi Telegram cảnh báo để user biết
                    msg = f"⚠️ <b>KHÔNG TẠO ĐƯỢC LỆNH</b>\n\n<b>Mã:</b> {symbol}\n<b>Side:</b> {side}\n<b>Entry:</b> {entry_price}\n<b>Lý do:</b> cascade_mgr không trả về orders\n<b>Need:</b> SL={need_sl}, TP={need_tp}"
                    try:
                        telegram_factory.send_tele(msg, cst.chat_id, True, True)
                    except Exception as tele_error:
                        logger.error(f"❌ Lỗi gửi Telegram cảnh báo cho {symbol}: {tele_error}", exc_info=True)
                    
            except Exception as e:
                logger.error(f"❌ Lỗi tạo lệnh cho {symbol}: {e}", exc_info=True)
                msg = f"🚨 <b>LỖI TẠO LỆNH</b>\n\n<b>Mã:</b> {symbol}\n<b>Lỗi:</b> {str(e)}"
                try:
                    telegram_factory.send_tele(msg, cst.chat_id, True, True)
                except Exception as tele_error:
                    logger.error(f"❌ Lỗi gửi Telegram lỗi cho {symbol}: {tele_error}", exc_info=True)

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