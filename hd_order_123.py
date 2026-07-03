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
from binance_futures_direct import fetch_algo_orders_for_symbol, futures_signed_request, resync_exchange_time

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

# Sheet "Chờ và khớp" — hàng 1: cấu hình rate (số thập phân như config.ini: 0.3 = 30%)
#   J1 = SL LONG   K1 = SL SHORT   L1 = TP LONG   M1 = TP SHORT   N1 = Callback %
# Hàng data: N=giá SL | O=giá kích hoạt TP (trống/NGAY/NOW/0 → kích hoạt ngay tại mark/last)
_TP_IMMEDIATE_TOKENS = frozenset({'NOW', 'NGAY', 'IMMEDIATE', 'MARK', '*'})
CHO_VAKHOP_RATE_ROW_RANGE = "J1:N1"
_RATE_CELL_INDEX = {
    "lenh2_rate_long": 0,
    "lenh2_rate_short": 1,
    "lenh3_rate_long": 2,
    "lenh3_rate_short": 3,
    "lenh3_callback_rate": 4,
}

# --- CÁC HÀM TIỆN ÍCH ---


def _rate_defaults_from_cst():
    return {
        "lenh2_rate_long": float(getattr(cst, "lenh2_rate_long", 0.3)),
        "lenh2_rate_short": float(getattr(cst, "lenh2_rate_short", 0.3)),
        "lenh3_rate_long": float(getattr(cst, "lenh3_rate_long", 0.6)),
        "lenh3_rate_short": float(getattr(cst, "lenh3_rate_short", 0.6)),
        "lenh3_callback_rate": float(getattr(cst, "lenh3_callback_rate", 1.0)),
    }


def _parse_rate_cell(raw, default, name):
    """Ô sheet: 0.3 hoặc 30 (hiểu là %). Giá trị <=0 hoặc lỗi → default."""
    if raw is None:
        return default
    if isinstance(raw, (int, float)):
        v = float(raw)
    else:
        s = str(raw).strip().replace(",", ".")
        if not s or s.startswith("="):
            return default
        try:
            v = float(s)
        except (ValueError, TypeError):
            logger.warning(f"Rate {name}: không parse được '{raw}' → dùng config {default}")
            return default
    if v <= 0:
        return default
    if v > 1.0:
        if v <= 100.0:
            v = v / 100.0
        else:
            logger.warning(f"Rate {name}: {v} ngoài khoảng → dùng config {default}")
            return default
    return v


def load_cho_va_khop_rate_config():
    """
    Đọc rate từ hàng 1 sheet Chờ và khớp (J1–N1).
    Ô trống / lỗi → fallback config.ini (cst).
    """
    out = _rate_defaults_from_cst()
    try:
        rows = gg_sheet_factory.get_cho_va_khop(
            CHO_VAKHOP_RATE_ROW_RANGE, value_render_option="UNFORMATTED_VALUE"
        )
        if not rows or not rows[0]:
            logger.info(f"Rate config: J1–N1 trống → dùng config.ini {out}")
            return out
        row = rows[0]
        while len(row) < 5:
            row.append("")
        for key, idx in _RATE_CELL_INDEX.items():
            out[key] = _parse_rate_cell(row[idx], out[key], key)
        logger.info(
            "Rate config từ sheet hàng 1 (J–N): "
            f"SL_L={out['lenh2_rate_long']} SL_S={out['lenh2_rate_short']} "
            f"TP_L={out['lenh3_rate_long']} TP_S={out['lenh3_rate_short']} "
            f"callback={out['lenh3_callback_rate']}"
        )
    except Exception as e:
        logger.warning(f"Không đọc được rate J1–N1 → dùng config.ini: {e}")
    return out


def ensure_cho_va_khop_rate_row_from_config_if_empty():
    """
    Lần đầu: nếu J1–N1 đều trống, ghi giá trị mặc định từ config.ini (không ghi A1).
    Không ghi đè nếu user đã nhập số ở bất kỳ ô J–N.
    """
    try:
        rows = gg_sheet_factory.get_cho_va_khop(CHO_VAKHOP_RATE_ROW_RANGE)
        row = rows[0] if rows else []
        while len(row) < 5:
            row.append("")
        has_any = any(str(row[i]).strip() for i in range(5))
        if has_any:
            return
        d = _rate_defaults_from_cst()
        gg_sheet_factory.update_multi(
            gg_sheet_factory.tab_cho_va_khop,
            -1,
            [
                [
                    d["lenh2_rate_long"],
                    d["lenh2_rate_short"],
                    d["lenh3_rate_long"],
                    d["lenh3_rate_short"],
                    d["lenh3_callback_rate"],
                ]
            ],
            "J",
        )
        logger.info("Đã ghi mặc định rate vào J1–N1 (từ config.ini)")
        print(
            "📝 Đã khởi tạo hàng 1: J=SL LONG, K=SL SHORT, L=TP LONG, M=TP SHORT, N=Callback",
            flush=True,
        )
    except Exception as e:
        logger.warning(f"Không ghi được J1–N1 rate mặc định: {e}")

def is_same_pair(sym1, sym2):
    sym1 = sym1.replace("/", "").upper().strip()
    sym2 = sym2.replace("/", "").upper().strip()
    if sym1 == sym2 :
       return True
    return False


def resolve_entry_price(symbol, entry_sheet: float, entry_binance: float) -> float:
    """
    Giá vào để tính SL/TP (cột E hoặc fallback Binance).
    - E <= 0 → dùng entryPrice từ position Binance
    - E và Binance lệch >1% → ưu tiên Binance (giá khớp thực tế)
    """
    sheet = 0.0
    try:
        sheet = float(entry_sheet) if entry_sheet else 0.0
    except (TypeError, ValueError):
        sheet = 0.0

    binance = 0.0
    try:
        binance = float(entry_binance) if entry_binance else 0.0
    except (TypeError, ValueError):
        binance = 0.0

    if sheet <= 0:
        if binance > 0:
            logger.info(f"{symbol}: Cột E trống/0 → dùng entry Binance={binance}")
            return binance
        return 0.0

    if binance > 0 and abs(binance - sheet) / sheet > 0.01:
        logger.warning(
            f"{symbol}: Entry sheet={sheet} vs Binance={binance} (>1%) → dùng Binance cho lệnh 2/3"
        )
        return binance

    return sheet


def _o_cell_requests_tp_immediate(raw) -> bool:
    """O trống / 0 / NOW / NGAY → TP trailing kích hoạt ngay (phương án A)."""
    if not getattr(cst, 'lenh3_o_empty_immediate', True):
        return False
    if raw is None:
        return True
    s = str(raw).strip().upper()
    if not s or s.startswith('='):
        return True
    if s in _TP_IMMEDIATE_TOKENS or s in ('0', '0.0', '0,0'):
        return True
    return False


def parse_pair_sl_tp_from_sheet(symbol, side, row_data, entry_price, rate_config=None):
    """
    Đọc 1 cặp lệnh 2 (STOP LIMIT) và 3 (TRAILING STOP) theo layout sheet mới:
      N (idx 13): ACTIVE PRICE — STOP LIMIT (giá SL)
      O (idx 14): ACTIVE PRICE — TRAILING STOP (giá kích hoạt TP)

    O trống / NGAY / NOW / 0 → tp_immediate (giá lấy mark/last lúc đặt lệnh).
    O có số > 0 → chờ giá O. N trống → vẫn tính SL từ rate J/K.

    Return: dict {sl_price, tp_price, has_sl, has_tp, tp_immediate}
    """
    if rate_config is None:
        rate_config = _rate_defaults_from_cst()
    is_long = (side == STATE_LONG)

    def _to_float(v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace(",", ".")
        if not s or s.startswith("="):  # formula text — không thể eval ở đây
            return None
        try:
            f = float(s)
            return f if f > 0 else None
        except (ValueError, TypeError):
            return None

    o_raw = row_data[14] if len(row_data) > 14 else None
    tp_immediate = _o_cell_requests_tp_immediate(o_raw)

    # N (13) STOP LIMIT, O (14) TRAILING STOP — UNFORMATTED_VALUE từ sheet
    sl_price = _to_float(row_data[13]) if len(row_data) > 13 else None
    tp_price = None if tp_immediate else _to_float(o_raw)

    u = rate_config["lenh2_rate_long"]
    v = rate_config["lenh2_rate_short"]
    w = rate_config["lenh3_rate_long"]
    x = rate_config["lenh3_rate_short"]

    if sl_price is None and entry_price > 0:
        sl_price = entry_price * (1 - u) if is_long else entry_price * (1 + v)
        logger.info(f"{symbol}: N rỗng → compute SL từ sheet/config rate = {sl_price}")

    if tp_immediate:
        logger.info(
            f"{symbol}: O trống/NGAY → TP trailing kích hoạt ngay tại giá mark/last "
            f"(callback N1={rate_config.get('lenh3_callback_rate')})"
        )
    elif tp_price is None and entry_price > 0 and not getattr(cst, 'lenh3_o_empty_immediate', True):
        # Fallback cũ: chỉ khi tắt phương án A trong config
        tp_price = entry_price * (1 + w) if is_long else entry_price * (1 - x)
        logger.info(f"{symbol}: O rỗng (legacy) → TP từ rate L/M = {tp_price}")

    # Validate logic giá so với entry (bỏ qua khi TP kích hoạt ngay)
    if sl_price and entry_price > 0:
        if is_long and sl_price >= entry_price:
            logger.warning(f"{symbol}: SL={sl_price} >= entry={entry_price} cho LONG — bỏ qua SL")
            sl_price = None
        elif (not is_long) and sl_price <= entry_price:
            logger.warning(f"{symbol}: SL={sl_price} <= entry={entry_price} cho SHORT — bỏ qua SL")
            sl_price = None
    if tp_price and entry_price > 0 and not tp_immediate:
        if is_long and tp_price <= entry_price:
            logger.warning(f"{symbol}: TP={tp_price} <= entry={entry_price} cho LONG — bỏ qua TP")
            tp_price = None
        elif (not is_long) and tp_price >= entry_price:
            logger.warning(f"{symbol}: TP={tp_price} >= entry={entry_price} cho SHORT — bỏ qua TP")
            tp_price = None

    has_tp = tp_immediate or (tp_price is not None)
    return {
        'sl_price': sl_price,
        'tp_price': tp_price,
        'has_sl': sl_price is not None,
        'has_tp': has_tp,
        'tp_immediate': tp_immediate and has_tp,
    }


def get_sl_tp_activation_price_from_cho_va_khop(symbol, side, row_data, entry_price):
    """
    [DEPRECATED] Tham chiếu — layout mới dùng parse_pair_sl_tp_from_sheet (cột N/O).
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
    params['recvWindow'] = 60000
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
    except requests.exceptions.HTTPError as e:
        body = e.response.text if e.response else str(e)
        logger.error(f"Lỗi HTTP {e.response.status_code if e.response else 'N/A'}: {body}")
        return None
    except Exception as e:
        logger.error(f"Lỗi khi gọi Binance API trực tiếp ({method} {endpoint}): {e}")
        return None

def get_algo_orders_for_symbol(symbol):
    """
    Returns:
        None  → API thực sự lỗi
        []    → Không có orders / HTTP 400 coi như rỗng
        [..]  → Có danh sách orders
    """
    try:
        symbol_clean = symbol.replace('/', '').replace(':USDT', '').upper()
        if '-' in symbol_clean:
            logger.debug(f"Bỏ qua delivery futures symbol: {symbol_clean}")
            return []
        return fetch_algo_orders_for_symbol(symbol, history_hours=24)
    except Exception as e:
        logger.error(f"Lỗi khi lấy algo orders cho {symbol}: {e}", exc_info=True)
        return None

def cancel_all_algo_orders_direct(symbol):
    try:
        active_orders = get_algo_orders_for_symbol(symbol)
        if not active_orders:
            return True
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
                response = futures_signed_request('DELETE', '/fapi/v1/algoOrder', params)
                
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

        if algo_orders is None:
            logger.warning(
                f"⚠️ {symbol}: API lỗi khi lấy algo orders → chặn đặt lệnh 2/3 (tránh trùng)"
            )
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
    'options': {
        'defaultType': 'future',
        'fetchCurrencies': False,          # [A2] tránh gọi /sapi getall (signed) khi load_markets
        'adjustForTimeDifference': True,   # [A2] tự đồng bộ clock -> hết lỗi -1021
        'recvWindow': 60000,               # [A2+Fix2] nới cửa sổ timestamp lên max 60s
    }
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

try:
    ensure_cho_va_khop_rate_row_from_config_if_empty()
except Exception as _e:
    logger.warning(f"Khởi tạo hàng 1 rate trên sheet: {_e}")

# --- LOGIC CHÍNH MỚI: ĐỌC TỪ SHEET "CHỜ VÀ KHỚP" ---

def do_it():
    logger.info(f"{datetime.now()}. Scan Lệnh 123 - Đọc từ Sheet 'Chờ và khớp' -------------------------")

    rate_config = load_cho_va_khop_rate_config()

    # Layout A–P: N = STOP LIMIT (lệnh 2), O = TRAILING STOP (lệnh 3), P = ĐẶT LỆNH
    try:
        sheet_data = gg_sheet_factory.get_cho_va_khop("A4:P1000", value_render_option="UNFORMATTED_VALUE")
        logger.info(f"✅ Đã đọc {len(sheet_data)} dòng từ sheet 'Chờ và khớp' (A–P)")
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
            
            # Cột E: Giá vào (sheet) — có thể bổ sung từ Binance sau khi có position
            try:
                entry_sheet = float(row[4]) if len(row) > 4 and row[4] else 0.0
            except (TypeError, ValueError):
                entry_sheet = 0.0

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
            
            # ĐIỀU KIỆN 3: Cột P (index 15) — ĐẶT LỆNH = Y
            allow_order = False
            try:
                if len(row) > 15 and row[15]:
                    status_str = str(row[15]).strip().upper()
                    allow_order = (status_str == "Y")
                    if allow_order:
                        logger.info(f"{symbol}: Cột P (ĐẶT LỆNH) = '{status_str}' → Cho phép đặt lệnh")
                    else:
                        logger.info(f"{symbol}: Cột P = '{status_str}' → Bỏ qua")
                else:
                    logger.info(f"{symbol}: Cột P rỗng → Bỏ qua, không đặt lệnh")
            except Exception as e:
                logger.warning(f"{symbol}: Lỗi đọc cột P: {e} → Bỏ qua (safety first)")
                allow_order = False

            if not allow_order:
                continue

            position_amt, entry_price_binance = get_position_amount_from_binance(symbol)
            if position_amt is None:
                logger.warning(f"⚠️ {symbol}: Không tìm thấy position trên Binance")
                continue

            entry_price = resolve_entry_price(symbol, entry_sheet, entry_price_binance)
            if entry_price <= 0:
                logger.warning(f"{symbol}: Không có giá vào hợp lệ (E sheet / Binance), bỏ qua")
                continue

            print(
                f"🔍 Xử lý: {symbol} | Side: {side} | Entry: {entry_price} | "
                f"Need SL: {need_sl}, TP: {need_tp}",
                flush=True,
            )

            pair = parse_pair_sl_tp_from_sheet(symbol, side, row, entry_price, rate_config)
            sl_price = pair['sl_price'] if need_sl else None
            tp_price = pair['tp_price'] if need_tp else None
            tp_immediate = bool(pair.get('tp_immediate')) if need_tp else False

            if need_sl and sl_price is None:
                logger.warning(f"⚠️ {symbol}: Cần SL nhưng không có giá hợp lệ (N / rate) — chỉ đặt TP nếu có")
            if need_tp and not tp_immediate and tp_price is None:
                logger.warning(f"⚠️ {symbol}: Cần TP nhưng O không hợp lệ — chỉ đặt SL nếu có")

            will_place_sl = need_sl and sl_price is not None
            will_place_tp = need_tp and (tp_immediate or tp_price is not None)
            if not will_place_sl and not will_place_tp:
                logger.warning(f"⚠️ {symbol}: Không đặt được SL/TP nào — bỏ qua dòng")
                continue

            tp_label = 'NGAY@mark' if (will_place_tp and tp_immediate) else (
                str(tp_price) if will_place_tp else 'skip'
            )
            print(
                f"🎯 [1 cặp] {symbol} | SL={sl_price if will_place_sl else 'skip'} | "
                f"Trail={tp_label}",
                flush=True,
            )
            tp_act_logged = tp_price
            try:
                result = cascade_mgr.on_entry_filled_multi_layer(
                    symbol=symbol,
                    entry_price=entry_price,
                    leverage=leverage,
                    position_amt=position_amt,
                    side=side,
                    sl_prices=[sl_price if will_place_sl else None, None, None],
                    tp_prices=[tp_price if will_place_tp else None, None, None],
                    ratios=[100.0, 0.0, 0.0],
                    callback_rate=rate_config["lenh3_callback_rate"],
                    skip_sl=not will_place_sl,
                    skip_tp=not will_place_tp,
                    tp_immediate_flags=[tp_immediate, False, False] if will_place_tp else None,
                )
                sl_orders = result['sl_orders']
                tp_orders = result['tp_orders']
                errors = result.get('errors', [])
                created_sl = [o for o in sl_orders if o]
                created_tp = [o for o in tp_orders if o]

                if created_sl:
                    order_logger.info(f"LỆNH 2 (STOP LIMIT) | {symbol} | {side} | Entry: {entry_price} | Price: {sl_price} | OrderID: {created_sl[0].get('id')}")
                if result.get('tp_activation_prices'):
                    tp_act_logged = result['tp_activation_prices'][0] or tp_act_logged
                if created_tp:
                    order_logger.info(
                        f"LỆNH 3 (TRAILING) | {symbol} | {side} | Entry: {entry_price} | "
                        f"Activation: {tp_act_logged} | immediate={tp_immediate} | "
                        f"OrderID: {created_tp[0].get('id')}"
                    )

                if created_sl or created_tp:
                    parts = []
                    if created_sl:
                        parts.append(f"SL@{sl_price}")
                    if created_tp:
                        parts.append(f"Trail@{tp_act_logged}")
                    print(f"✅ [1 cặp] {symbol}: {' + '.join(parts)}", flush=True)
                    msg = (
                        f"✅ <b>ĐÃ TẠO CẶP LỆNH 2–3</b>\n\n"
                        f"<b>Mã:</b> {symbol}\n"
                        f"<b>Side:</b> {side}  |  <b>Entry:</b> {entry_price}\n"
                        f"<b>N STOP LIMIT:</b> {sl_price if created_sl else '(skip)'}\n"
                        f"<b>O TRAILING:</b> "
                        f"{'NGAY @ ' + str(tp_act_logged) if (created_tp and tp_immediate) else (tp_price if created_tp else '(skip)')}"
                    )
                    try:
                        telegram_factory.send_tele(msg, cst.chat_id, True, True)
                    except Exception as te:
                        logger.error(f"Lỗi gửi Telegram: {te}", exc_info=True)
                    processed_count += 1
                else:
                    logger.warning(f"⚠️ {symbol}: Không tạo được lệnh | errors={errors}")
            except Exception as e:
                logger.error(f"❌ Lỗi tạo cặp lệnh cho {symbol}: {e}", exc_info=True)
                try:
                    telegram_factory.send_tele(f"🚨 <b>LỖI LỆNH 2–3</b>\n{symbol}: {e}", cst.chat_id, True, True)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"❌ Lỗi xử lý dòng sheet: {e}", exc_info=True)
    
    # Tổng kết
    logger.info(f"✅ Hoàn thành scan - Đã xử lý {processed_count} symbol")

while True:
    try:
        resync_exchange_time(exchange)  # [Fix1] chống clock drift -> hết -1021
        do_it()
        sys.stdout.flush()
    except Exception as e:
        if '-1021' in str(e) or 'recvWindow' in str(e):
            resync_exchange_time(exchange, min_interval=0)  # [Fix4] ép resync ccxt ngay
        print(f"Tổng Lỗi: {e}", flush=True)
        logger.error(f"Tổng lỗi: {e}", exc_info=True)
    time.sleep(cst.delay_vao_lenh_123)