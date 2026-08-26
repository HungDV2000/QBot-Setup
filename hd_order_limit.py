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
import utils
import binance_utils
import telegram_factory
from pathlib import Path
from binance_order_helper import BinanceOrderHelper, cancel_all_open_orders_with_retry
import requests
import hmac
import hashlib
import urllib.parse
import json
from googleapiclient.errors import HttpError  # ✅ Thêm import HttpError để handle lỗi Google API
from binance_futures_direct import fetch_algo_orders_for_symbol, resync_exchange_time

# Cấu hình stdout để output realtime (unbuffered)
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

file_name = os.path.basename(os.path.abspath(__file__))  
os.system(f"title {file_name} - {cst.key_name}")

# Tạo thư mục logs/ nếu chưa có
logs_dir = cst.account_dir('logs')  # [MULTI-ACC] tách theo tài khoản
logs_dir.mkdir(exist_ok=True)

# Tạo tên file log với timestamp: hd_order_limit_dd_mm_yyyy_H_M_S.txt
log_timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
log_filename = logs_dir / f'hd_order_limit_{log_timestamp}.txt'

# Cải thiện logging với timestamp và UTF-8 encoding
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

# Tạo order logger riêng để track tất cả orders
order_logger = logging.getLogger('order')
order_logger.setLevel(logging.INFO)
order_log_path = logs_dir / 'order.log'
order_handler = logging.FileHandler(order_log_path, encoding='utf-8')
order_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
order_logger.addHandler(order_handler)

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

# [FIX 1] Bắt buộc tải lại thông tin Precision mới nhất từ Binance để tránh lỗi làm tròn sai
print("⏳ Đang cập nhật thông tin thị trường (Precision/TickSize)...", flush=True)
try:
    exchange.load_markets(True) # True = Force reload
    print("✅ Đã cập nhật xong thông tin thị trường.", flush=True)
except Exception as e:
    print(f"⚠️ Lỗi cập nhật markets: {e}", flush=True)

# Khởi tạo order helper
order_helper = BinanceOrderHelper(exchange)

# ===================================================================
# LOCAL ORDER CACHE - Chống lặp đơn khi Binance API lỗi/timeout
# Cache lưu {symbol: {'algo_id': str, 'placed_at': float}}
# Được persist vào file để giữ qua lần restart bot
# ===================================================================
_order_cache: dict = {}
_cache_lock = threading.Lock()
_CACHE_FILE = cst.account_dir('data') / 'order_cache_limit.json'  # [MULTI-ACC]
_CACHE_TTL_SECONDS = 86400  # 24 giờ - thời gian order còn có thể valid


def _load_order_cache():
    """Load cache từ file JSON khi bot khởi động"""
    global _order_cache
    try:
        _CACHE_FILE.parent.mkdir(exist_ok=True)
        if _CACHE_FILE.exists():
            with open(_CACHE_FILE, 'r', encoding='utf-8') as f:
                _order_cache = json.load(f)
            logger.info(f"[CACHE] Đã load {len(_order_cache)} entries từ {_CACHE_FILE}")
            print(f"✅ [CACHE] Đã load {len(_order_cache)} symbol từ cache file", flush=True)
        else:
            _order_cache = {}
            logger.info("[CACHE] Chưa có cache file, khởi tạo rỗng")
    except Exception as e:
        logger.error(f"[CACHE] Lỗi load cache: {e}", exc_info=True)
        _order_cache = {}


def _save_order_cache():
    """Lưu cache ra file JSON (gọi bên trong _cache_lock)"""
    try:
        _CACHE_FILE.parent.mkdir(exist_ok=True)
        with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_order_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[CACHE] Lỗi save cache: {e}", exc_info=True)


def add_to_order_cache(symbol: str, algo_id: str):
    """Thêm order vừa đặt thành công vào cache"""
    with _cache_lock:
        _order_cache[symbol] = {
            'algo_id': str(algo_id),
            'placed_at': time.time()
        }
        _save_order_cache()
    logger.info(f"[CACHE] Đã thêm {symbol} (algoId={algo_id}) vào cache")


def remove_from_order_cache(symbol: str):
    """Xóa symbol khỏi cache khi API xác nhận không còn order"""
    with _cache_lock:
        if symbol in _order_cache:
            del _order_cache[symbol]
            _save_order_cache()
            logger.info(f"[CACHE] Đã xóa {symbol} khỏi cache (API xác nhận hết order)")


def is_in_order_cache(symbol: str) -> tuple:
    """
    Kiểm tra symbol có trong cache và còn hiệu lực không.
    Returns: (True/False, algo_id hoặc None)
    """
    with _cache_lock:
        if symbol not in _order_cache:
            return False, None
        entry = _order_cache[symbol]
        age = time.time() - entry.get('placed_at', 0)
        if age > _CACHE_TTL_SECONDS:
            del _order_cache[symbol]
            _save_order_cache()
            logger.info(f"[CACHE] {symbol} đã hết hạn cache ({age/3600:.1f}h), xóa")
            return False, None
        return True, entry.get('algo_id')


def is_same_pair(sym1, sym2):
    """
    So sánh 2 symbols có giống nhau không (bỏ qua format)
    VD: HOME/USDT:USDT == HOMEUSDT == HOME/USDT
    """
    # Chuẩn hóa về dạng HOMEUSDT (chỉ giữ base+quote)
    sym1 = sym1.replace("/", "").replace(":USDT", "").upper().strip()
    sym2 = sym2.replace("/", "").replace(":USDT", "").upper().strip()
    return sym1 == sym2

def get_algo_orders_for_symbol(symbol):
    """
    Lấy algo orders (open + lịch sử 24h). openAlgoOrders trước để tránh 400 allAlgoOrders.

    Returns:
        None  → Lỗi mạng/API thật (không parse được)
        []    → Không có order / symbol không có algo
        [..]  → Có danh sách orders
    """
    try:
        return fetch_algo_orders_for_symbol(symbol, history_hours=24)
    except Exception as e:
        logger.error(f"Lỗi khi lấy algo orders cho {symbol}: {e}", exc_info=True)
        return None

def cancel_all_open_orders(symbol):
    open_orders = exchange.fetch_open_orders(symbol)

    if open_orders:
        for order in open_orders:
            order_id = order['id']
            cancel_result = exchange.cancel_order(order_id, symbol)
            print(f"Hủy lệnh {order_id} kết quả: {cancel_result}", flush=True)
            msg = f"Đã Hủy lệnh Chờ: {order['symbol']}"
            telegram_factory.send_tele(msg,cst.chat_id, True , True)
    else:
        print(f"Không có lệnh mở nào cho {symbol}", flush=True)



def normalize_symbol(symbol):
    """
    Chuẩn hóa symbol về format CCXT Binance Futures (có dấu / và :USDT)
    VD: BTCUSDT -> BTC/USDT:USDT, BTC/USDT -> BTC/USDT:USDT
    """
    symbol = symbol.strip().upper()
    
    # Nếu đã có :USDT, giữ nguyên
    if ':USDT' in symbol:
        return symbol
    
    # Nếu có dấu / nhưng chưa có :USDT
    if '/' in symbol:
        # BID/USDT -> BID/USDT:USDT
        if symbol.endswith('/USDT'):
            return f"{symbol}:USDT"
        return symbol
    
    # Tự động thêm /USDT:USDT nếu chưa có
    if symbol.endswith('USDT'):
        base = symbol[:-4]
        return f"{base}/USDT:USDT"
    
    # Fallback: thêm /USDT:USDT vào cuối
    return f"{symbol}/USDT:USDT"

def is_symbol_tradeable(symbol):
    """
    Kiểm tra symbol có cho phép giao dịch không
    Returns: (True/False, error_message, normalized_symbol)
    """
    try:
        # Chuẩn hóa symbol
        original_symbol = symbol
        symbol = normalize_symbol(symbol)
        
        if symbol != original_symbol:
            logger.info(f"Đã chuẩn hóa symbol: {original_symbol} -> {symbol}")
        
        # Kiểm tra symbol có tồn tại trong markets không
        # Vì exchange đã config defaultType='future', nên exchange.markets CHỈ chứa futures
        if symbol not in exchange.markets:
            # Thử tìm các symbol tương tự
            similar = [s for s in exchange.markets.keys() if original_symbol.replace('/', '').upper() in s.replace('/', '').upper()]
            if similar:
                suggestion = f"Có thể bạn muốn: {', '.join(similar[:3])}"
            else:
                suggestion = "Không tìm thấy symbol tương tự trên Binance Futures"
            return False, f"Symbol {symbol} không tồn tại trên Binance Futures. {suggestion}", symbol
        
        market = exchange.markets[symbol]
        
        # Kiểm tra trạng thái active
        if not market.get('active', False):
            return False, f"Symbol {symbol} đang bị tạm ngưng giao dịch (inactive)", symbol
        
        # Kiểm tra info từ Binance (status)
        info = market.get('info', {})
        status = info.get('status', '').upper()
        contract_status = info.get('contractStatus', '').upper()
        
        # TRADING = cho phép giao dịch bình thường
        # Các trạng thái khác: BREAK, HALT, AUCTION_MATCH, PENDING_TRADING...
        if status and status != 'TRADING':
            return False, f"Symbol {symbol} status={status} (không phải TRADING)", symbol
        
        # PENDING_TRADING = chưa mở giao dịch
        # TRADING = đang giao dịch bình thường
        # PRE_DELIVERING, DELIVERING, DELIVERED = đang/đã giao hàng (delisting)
        if contract_status and contract_status not in ['TRADING', '']:
            return False, f"Symbol {symbol} contractStatus={contract_status}", symbol
        
        return True, "", symbol
        
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra tradeable cho {symbol}: {e}", exc_info=True)
        return False, f"Lỗi kiểm tra: {str(e)}", symbol

def has_position(sym):
    """Kiểm tra symbol đã có vị thế (đã vào lệnh) chưa"""
    try:
        balance = exchange.fetch_balance()
        if not balance or 'info' not in balance:
            logger.warning(f"fetch_balance() trả về dữ liệu không hợp lệ cho {sym}")
            return False
        positions = balance['info'].get('positions', [])
        for position in positions:
            symbol = position.get('symbol', '')
            position_amt = position.get('positionAmt', '0')
            if is_same_pair(symbol, sym) and float(position_amt) != 0:
                return True
        return False
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra vị thế cho {sym}: {e}", exc_info=True)
        return False

def get_position_amt(sym):
    """
    Trả về positionAmt (signed float) của symbol.
    > 0 = LONG, < 0 = SHORT, 0 = không có vị thế.
    Raise nếu API lỗi → caller sẽ bỏ qua dòng để tránh đặt trùng lệnh.
    """
    balance = exchange.fetch_balance()
    if not balance or 'info' not in balance:
        logger.warning(f"fetch_balance() không hợp lệ cho {sym}")
        raise RuntimeError("fetch_balance trả về dữ liệu không hợp lệ")
    positions = balance['info'].get('positions', [])
    for position in positions:
        symbol = position.get('symbol', '')
        if is_same_pair(symbol, sym):
            return float(position.get('positionAmt', '0') or 0)
    return 0.0

def has_pending_reverse_limit_order(symbol, reverse_side):
    """
    Kiểm tra đã có LỆNH NGƯỢC (LIMIT reduce_only) cùng side chưa.
    reverse_side: side của lệnh ngược (LONG->'sell', SHORT->'buy').
    Raise nếu API lỗi → caller bỏ qua dòng (tránh đặt trùng lệnh ngược).
    """
    open_orders = exchange.fetch_open_orders(symbol)
    if not open_orders:
        return False
    for order in open_orders:
        o_type = str(order.get('type', '')).upper()
        o_side = str(order.get('side', '')).lower()
        info = order.get('info', {}) if isinstance(order.get('info'), dict) else {}
        reduce_only = order.get('reduceOnly', False) or info.get('reduceOnly', False) \
            or str(info.get('reduceOnly', 'false')).lower() == 'true'
        if o_type == 'LIMIT' and o_side == reverse_side.lower() and reduce_only:
            return True
    return False

def has_pending_stop_market_order(symbol, sl_side):
    """
    Kiểm tra đã có LỆNH CẮT LỖ (STOP_MARKET reduce_only) cùng side chưa.
    sl_side: side của lệnh cắt lỗ (LONG->'sell', SHORT->'buy').
    Raise nếu API lỗi → caller bỏ qua để tránh đặt trùng lệnh SL.
    """
    open_orders = exchange.fetch_open_orders(symbol)
    if not open_orders:
        return False
    for order in open_orders:
        o_type = str(order.get('type', '')).upper()
        o_side = str(order.get('side', '')).lower()
        info = order.get('info', {}) if isinstance(order.get('info'), dict) else {}
        reduce_only = order.get('reduceOnly', False) or info.get('reduceOnly', False) \
            or str(info.get('reduceOnly', 'false')).lower() == 'true'
        # STOP_MARKET (CCXT có thể trả 'STOP_MARKET' hoặc 'STOP')
        if 'STOP' in o_type and o_side == sl_side.lower() and reduce_only:
            return True
    return False

def has_pending_limit_order(symbol, side):
    """
    Kiểm tra symbol đã có OPEN LIMIT ORDER (lệnh vào) cùng chiều chưa.

    Lệnh LIMIT là open order thường (không phải algo order), nên phải dùng
    fetch_open_orders() thay vì fetch_algo_orders.

    Chỉ tính lệnh entry (reduceOnly=False) cùng side → bỏ qua lệnh ngược
    reduce_only do bot khác đặt.

    Fail-safe (giống bản trailing stop):
    - API OK + có limit entry cùng side → CHẶN
    - API OK + không có → CHO PHÉP (xóa cache)
    - API lỗi (Exception) + có cache → CHẶN
    - API lỗi (Exception) + không cache → CHO PHÉP (tránh chặn oan do timeout)
    """
    try:
        logger.info(f"[CHECK PENDING] {symbol}: Đang kiểm tra open LIMIT orders (side={side})...")
        open_orders = exchange.fetch_open_orders(symbol)

        # ── API THÀNH CÔNG + KHÔNG CÓ ORDERS ───────────────────────────
        if not open_orders:
            remove_from_order_cache(symbol)  # Xóa cache lỗi thời nếu có
            logger.info(f"[CHECK PENDING] {symbol}: Không có open orders → Cho phép tạo lệnh mới")
            return False

        # ── API THÀNH CÔNG + CÓ ORDERS → Lọc LIMIT entry cùng side ─────
        matched = []
        for order in open_orders:
            o_type = str(order.get('type', '')).upper()
            o_side = str(order.get('side', '')).lower()
            # reduceOnly có thể nằm ở top-level hoặc trong info
            info = order.get('info', {}) if isinstance(order.get('info'), dict) else {}
            reduce_only = order.get('reduceOnly', False) or info.get('reduceOnly', False) \
                or str(info.get('reduceOnly', 'false')).lower() == 'true'

            if o_type == 'LIMIT' and o_side == side.lower() and not reduce_only:
                matched.append(order.get('id', 'N/A'))

        if matched:
            logger.info(f"✅ {symbol} đã có {len(matched)} LIMIT entry order(s) cùng side {side}: {matched}")
            print(f"⏭️  {symbol} đã có {len(matched)} lệnh LIMIT chờ (side={side}), bỏ qua", flush=True)
            return True

        # Có open orders nhưng không phải LIMIT entry cùng side (vd lệnh ngược reduce_only)
        remove_from_order_cache(symbol)
        logger.info(f"[CHECK PENDING] {symbol}: Không có LIMIT entry cùng side {side} → Cho phép tạo lệnh mới")
        return False

    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra open orders cho {symbol}: {e}", exc_info=True)
        in_cache, cached_algo_id = is_in_order_cache(symbol)
        if in_cache:
            logger.warning(f"[CHECK PENDING] {symbol}: API lỗi + có cache (id={cached_algo_id}) → CHẶN")
            print(f"⛔ {symbol}: Lỗi kiểm tra + có cache → CHẶN để tránh lặp đơn", flush=True)
            return True
        logger.warning(f"[CHECK PENDING] {symbol}: API lỗi + không cache → cho phép đặt lệnh")
        return False

def execute_command(commands):
    try:
        
        subprocess.run(commands, shell=True, check=True)
    except Exception as e:
        print(e, flush=True)

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
    
STATE_STOP = "STOP"
STATE_SHORT = "SHORT"
STATE_LONG  = "LONG"
STATE_CHO  = "CHỜ"
LENH_CHO = "LỆNH CHỜ"

# ===================================================================
# CHẾ ĐỘ ĐẶT LỆNH NGƯỢC:
#   Không dùng ô công tắc riêng. Cơ chế bật/tắt theo TỪNG DÒNG:
#     - Cột G (TP) CÓ giá  → bot đặt lệnh ngược (chốt lời) cho dòng đó
#     - Cột G (TP) TRỐNG   → bot chỉ đặt lệnh 1 (không đặt lệnh ngược)
# ===================================================================

# ── CHỐNG 429: cache trạng thái B2 (xem rate_guard.py) ───────────────────────
import rate_guard
STATE_CACHE_TTL = rate_guard.read_ttl(cst.config)

_state_box = rate_guard.new_box()

def get_current_state(force=False):
  """Đọc trạng thái B2 — CÓ CACHE ngắn hạn để không vượt hạn mức Google Sheets.
  force=True → bỏ qua cache, đọc thật (dùng ở đầu/cuối mỗi vòng quét)."""
  return rate_guard.cached_state(_state_box, _fetch_current_state,
                                 STATE_CACHE_TTL, force)

def invalidate_state_cache():
  rate_guard.clear(_state_box)

def _fetch_current_state():
  """
  Đọc trạng thái B2 hiện tại từ Google Sheet
  Returns: (state_value, timestamp)
  """
  try:
    result = gg_sheet_factory.get_dat_lenh("B2:B2")
    
    # ✅ Kiểm tra result có phải là HttpError không (trường hợp version cũ của gg_sheet_factory return HttpError)
    if isinstance(result, HttpError):
      logger.error(f"HttpError được return (không phải raise) từ get_dat_lenh: {result}")
      print(f"❌ Lỗi Google Sheets API: {result}", flush=True)
      return STATE_CHO, datetime.now()
    
    # Kiểm tra result có phải là list hợp lệ không
    if not isinstance(result, list):
      logger.error(f"Result không phải list: type={type(result)}, value={result}")
      print(f"❌ Dữ liệu trả về không hợp lệ (không phải list): {type(result)}", flush=True)
      return STATE_CHO, datetime.now()
    
    # Kiểm tra result có data không
    if len(result) == 0:
      logger.warning("B2 trống hoặc không có dữ liệu")
      return STATE_CHO, datetime.now()
    
    if len(result[0]) == 0:
      logger.warning("B2 không có giá trị")
      return STATE_CHO, datetime.now()
    
    state_value = result[0][0].strip().upper()
    return state_value, datetime.now()
    
  except HttpError as e:
    logger.error(f"HttpError khi đọc trạng thái từ B2: {e}", exc_info=True)
    print(f"❌ Lỗi Google Sheets API khi đọc B2: {e}", flush=True)
    return STATE_CHO, datetime.now()
  except TypeError as e:
    # TypeError: 'HttpError' object has no len() hoặc is not subscriptable
    logger.error(f"TypeError (có thể do HttpError được return thay vì raise): {e}", exc_info=True)
    print(f"❌ TypeError khi xử lý B2: {e}", flush=True)
    return STATE_CHO, datetime.now()
  except (IndexError, KeyError, AttributeError) as e:
    logger.error(f"Lỗi parse dữ liệu B2: {e}", exc_info=True)
    print(f"❌ Lỗi parse dữ liệu B2: {e}", flush=True)
    return STATE_CHO, datetime.now()
  except Exception as e:
    logger.error(f"Lỗi không xác định khi đọc B2: {e}", exc_info=True)
    print(f"❌ Lỗi không xác định khi đọc B2: {e}", flush=True)
    return STATE_CHO, datetime.now()


def get_capital_config():
  """
  Đọc cấu hình vốn từ Google Sheet
  - D1: % tỷ lệ vốn (ví dụ: 3.00%)
  - D2: Vốn mặc định (tối thiểu 10 USDT)
  - E2: Vốn tổng
  
  Returns: (d1_percent, d2_default, e2_total, has_error)
  """
  try:
    # Đọc D1:E2 (2 dòng x 2 cột)
    result = gg_sheet_factory.get_dat_lenh("D1:E2")
    
    # ✅ Kiểm tra result có phải là HttpError không
    if isinstance(result, HttpError):
      logger.error(f"HttpError được return từ get_dat_lenh: {result}")
      print(f"❌ Lỗi Google Sheets API: {result}", flush=True)
      return None, None, None, True
    
    # Kiểm tra result có phải là list hợp lệ không
    if not isinstance(result, list):
      logger.error(f"Result không phải list: type={type(result)}, value={result}")
      print(f"❌ Dữ liệu trả về không hợp lệ: {type(result)}", flush=True)
      return None, None, None, True
    
    # Kiểm tra có đủ 2 dòng không
    if len(result) < 2:
      logger.warning(f"Không đủ dữ liệu (cần 2 dòng D1:E2, chỉ có {len(result)})")
      return None, None, None, True
    
    # Parse D1 (% tỷ lệ vốn)
    d1_percent = None
    try:
      if len(result[0]) > 0 and result[0][0]:
        d1_str = str(result[0][0]).strip().replace("%", "")
        if d1_str and d1_str not in ["#DIV/0!", "#VALUE!", "#ERROR!", "#N/A"]:
          d1_percent = float(d1_str) / 100  # Convert % sang decimal (3.00% -> 0.03)
          logger.info(f"D1 (% vốn): {d1_str}% = {d1_percent}")
    except (ValueError, TypeError) as e:
      logger.warning(f"Không parse được D1: {e}")
    
    # Parse D2 (vốn mặc định)
    d2_default = None
    try:
      if len(result[1]) > 0 and result[1][0]:
        d2_str = str(result[1][0]).strip()
        if d2_str and d2_str not in ["#DIV/0!", "#VALUE!", "#ERROR!", "#N/A"]:
          d2_default = float(d2_str)
          logger.info(f"D2 (vốn mặc định): {d2_default} USDT")
    except (ValueError, TypeError) as e:
      logger.warning(f"Không parse được D2: {e}")
    
    # Parse E2 (vốn tổng)
    e2_total = None
    try:
      if len(result[1]) > 1 and result[1][1]:
        e2_str = str(result[1][1]).strip()
        if e2_str and e2_str not in ["#DIV/0!", "#VALUE!", "#ERROR!", "#N/A"]:
          e2_total = float(e2_str)
          logger.info(f"E2 (vốn tổng): {e2_total} USDT")
    except (ValueError, TypeError) as e:
      logger.warning(f"Không parse được E2: {e}")
    
    return d1_percent, d2_default, e2_total, False
    
  except HttpError as e:
    logger.error(f"HttpError khi đọc cấu hình vốn: {e}", exc_info=True)
    print(f"❌ Lỗi Google Sheets API: {e}", flush=True)
    return None, None, None, True
  except TypeError as e:
    logger.error(f"TypeError khi xử lý cấu hình vốn: {e}", exc_info=True)
    print(f"❌ TypeError: {e}", flush=True)
    return None, None, None, True
  except Exception as e:
    logger.error(f"Lỗi không xác định khi đọc cấu hình vốn: {e}", exc_info=True)
    print(f"❌ Lỗi: {e}", flush=True)
    return None, None, None, True

def do_it():
  print(f"{datetime.now()}. Scan Vào Lệnh----------------------------------------------------", flush=True)
  sys.stdout.flush()  # Flush ngay sau khi bắt đầu scan
  logger.info(f"{datetime.now()}. Scan Vào Lệnh----------------------------------------------------")

  # Đọc trạng thái hệ thống từ B2 (theo quy trình thực tế)
  state_value, read_time = get_current_state(force=True)
  print(f"📌 Trạng thái: {state_value} (đọc lúc {read_time.strftime('%H:%M:%S')})", flush=True)
  logger.info(f"[SCAN START] Đọc trạng thái từ B2: {state_value} (timestamp: {read_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]})")

  # Đọc cấu hình vốn từ D1, D2, E2
  d1_percent, d2_default, e2_total, has_error = get_capital_config()
  
  if has_error:
    print(f"⚠️ Lỗi đọc cấu hình vốn (D1/D2/E2)", flush=True)
    logger.warning("Lỗi đọc cấu hình vốn, không thể đặt lệnh")
    d1_percent = None
    d2_default = None
    e2_total = None
  
  # Kiểm tra nếu E2 và D2 đều rỗng → KHÔNG đặt lệnh
  if e2_total is None and d2_default is None:
    print(f"⚠️ E2 và D2 đều rỗng → Không đặt lệnh (cần ít nhất 1 trong 2)", flush=True)
    logger.warning("E2 và D2 đều rỗng → Không đặt lệnh")
  else:
    # Log cấu hình
    print(f"💰 Cấu hình vốn:", flush=True)
    if d1_percent is not None:
      print(f"   D1 (% vốn): {d1_percent*100:.2f}%", flush=True)
    else:
      print(f"   D1 (% vốn): Không có", flush=True)
    
    if d2_default is not None:
      print(f"   D2 (vốn mặc định): {d2_default} USDT", flush=True)
    else:
      print(f"   D2 (vốn mặc định): Không có", flush=True)
    
    if e2_total is not None:
      print(f"   E2 (vốn tổng): {e2_total} USDT", flush=True)
    else:
      print(f"   E2 (vốn tổng): Không có", flush=True)
    
    logger.info(f"Cấu hình vốn: D1={d1_percent}, D2={d2_default}, E2={e2_total}")

  if state_value == STATE_STOP:
    logger.warning("🛑 LỆNH STOP ĐƯỢC KÍCH HOẠT!")
    msg = "🛑 <b>LỆNH STOP KÍCH HOẠT</b>\n\n<b>Trạng thái:</b> Đang xử lý..."
    telegram_factory.send_tele(msg, cst.chat_id, True, True)
    
    # Đóng tất cả vị thế
    positions = exchange.fetch_positions()
    closed_positions = 0
    
    for position in positions:
        if float(position['info']['positionAmt']) != 0:
            symbol = position['symbol']
            amount = float(position['info']['positionAmt'])
            if amount != 0:
                try:
                    if amount > 0:
                        order = exchange.create_market_sell_order(symbol, amount)
                        logger.info(f"✅ Đã đóng vị thế LONG cho {symbol}: {order}")
                    elif amount < 0:
                        order = exchange.create_market_buy_order(symbol, abs(amount))
                        logger.info(f"✅ Đã đóng vị thế SHORT cho {symbol}: {order}")
                    closed_positions += 1
                except Exception as e:
                    logger.error(f"❌ Lỗi khi đóng vị thế {symbol}: {e}")
    
    # Hủy tất cả lệnh chờ
    try:
        all_open_orders = exchange.fetch_open_orders()
        cancelled_orders = 0
        for order in all_open_orders:
            try:
                exchange.cancel_order(order['id'], order['symbol'])
                cancelled_orders += 1
            except Exception as e:
                logger.error(f"Lỗi hủy lệnh {order['id']}: {e}")
        
        msg = f"✅ <b>HOÀN TẤT STOP</b>\n\n<b>Vị thế đã đóng:</b> {closed_positions}\n<b>Lệnh đã hủy:</b> {cancelled_orders}\n<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        telegram_factory.send_tele(msg, cst.chat_id, True, True)
        logger.warning("✅ Hoàn tất lệnh STOP")
    except Exception as e:
        logger.critical(f"🔴 Lỗi nghiêm trọng khi thực hiện STOP: {e}")

  elif state_value == "XÓA CHỜ":
    logger.info("🔄 Thực hiện lệnh XÓA CHỜ - Hủy tất cả lệnh pending, giữ vị thế")
    
    try:
        all_open_orders = exchange.fetch_open_orders()
        cancelled_count = 0
        
        for order in all_open_orders:
            try:
                exchange.cancel_order(order['id'], order['symbol'])
                cancelled_count += 1
                logger.info(f"Đã hủy lệnh {order['id']} cho {order['symbol']}")
            except Exception as e:
                logger.error(f"Lỗi hủy lệnh {order['id']}: {e}")
        
        msg = f"✅ <b>ĐÃ HỦY TẤT CẢ LỆNH CHỜ</b>\n\n<b>Số lệnh đã hủy:</b> {cancelled_count}\n<b>Vị thế:</b> Giữ nguyên\n<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        telegram_factory.send_tele(msg, cst.chat_id, True, True)
        logger.info(f"✅ Đã hủy {cancelled_count} lệnh chờ")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi thực hiện XÓA CHỜ: {e}")
        msg = f"🚨 <b>LỖI XÓA CHỜ</b>\n\n<b>Lỗi:</b> {str(e)}"
        telegram_factory.send_tele(msg, cst.chat_id, True, True)

  elif state_value == "XÓA VỊ THẾ":
    logger.info("🔄 Thực hiện lệnh XÓA VỊ THẾ - Đóng tất cả positions, giữ lệnh chờ")
    
    try:
        positions = exchange.fetch_positions()
        closed_count = 0
        
        for position in positions:
            if float(position['info']['positionAmt']) != 0:
                symbol = position['symbol']
                amount = float(position['info']['positionAmt'])
                
                try:
                    if amount > 0:
                        order = exchange.create_market_sell_order(symbol, amount)
                        logger.info(f"Đã đóng vị thế LONG: {symbol}")
                    elif amount < 0:
                        order = exchange.create_market_buy_order(symbol, abs(amount))
                        logger.info(f"Đã đóng vị thế SHORT: {symbol}")
                    closed_count += 1
                except Exception as e:
                    logger.error(f"Lỗi đóng vị thế {symbol}: {e}")
        
        msg = f"✅ <b>ĐÃ ĐÓNG TẤT CẢ VỊ THẾ</b>\n\n<b>Số vị thế đã đóng:</b> {closed_count}\n<b>Lệnh chờ:</b> Giữ nguyên\n<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        telegram_factory.send_tele(msg, cst.chat_id, True, True)
        logger.info(f"✅ Đã đóng {closed_count} vị thế")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi thực hiện XÓA VỊ THẾ: {e}")
        msg = f"🚨 <b>LỖI XÓA VỊ THẾ</b>\n\n<b>Lỗi:</b> {str(e)}"
        telegram_factory.send_tele(msg, cst.chat_id, True, True)

  elif state_value == STATE_CHO:
    print("💤 Trạng thái CHỜ - Không làm gì...", flush=True)
    logger.info("Trạng thái CHỜ - Không làm gì...")
  
  # ⚠️ Kiểm tra điều kiện đặt lệnh: E2 và D2 không được đều rỗng
  elif e2_total is None and d2_default is None:
    print("⏭️  Bỏ qua scan - E2 và D2 đều rỗng", flush=True)
    logger.warning("Bỏ qua scan - Không có cấu hình vốn hợp lệ")
  
  else:
    
    if state_value == STATE_LONG:
      start_row = 4
      end_row = 53
      type = "BUY"

    elif state_value == STATE_SHORT:
      start_row = 55
      end_row = 104
      type = "SHORT"

    don_bay = gg_sheet_factory.get_dat_lenh(f"A{start_row}:H{end_row}")  # Chỉ cần đọc A-H
    print(f"🔍 Scan {state_value} từ hàng {start_row} đến {end_row}", flush=True)
    logger.info(f"Scan {state_value} từ hàng {start_row} đến {end_row}")
    
    print(f"📊 Đã đọc được {len(don_bay)} dòng từ sheet", flush=True)
    logger.info(f"Đã đọc được {len(don_bay)} dòng từ sheet")
    
    row_count = 0
    for d in don_bay:
        row_count += 1
        print(f"📝 Đang xử lý dòng {row_count}/{len(don_bay)}", flush=True)
        sys.stdout.flush()  # Đảm bảo flush ngay lập tức
        # Cấu trúc CỐ ĐỊNH: A=Symbol, B=Leverage, D=Giá entry, F=Giá SL, G=Giá TP, H=Capital
        # Lệnh 1 (entry LIMIT) giá cột D.
        # Khi có vị thế: TP (LIMIT reduce_only) giá cột G; SL (STOP_MARKET reduce_only) giá cột F.
        # Cột C=Callback KHÔNG dùng trong bot LIMIT.
        leverage_idx = 1    # Cột B
        activation_idx = 3  # Cột D (giá entry limit)
        sl_idx = 5          # Cột F (giá SL - cắt lỗ STOP_MARKET reduce only)
        reverse_idx = 6     # Cột G (giá TP - chốt lời LIMIT reduce only)
        capital_idx = 7     # Cột H
        
        # Validation: B ≠ "N" và B ≠ 0 và B là số hợp lệ
        if len(d) <= leverage_idx or not d[leverage_idx]:
            logger.debug(f"Dòng {row_count}: Không có leverage (cột B), bỏ qua")
            continue
            
        leverage_value = str(d[leverage_idx]).strip()
        
        # Kiểm tra leverage hợp lệ
        if leverage_value == "N" or leverage_value == "0":
            logger.debug(f"Dòng {row_count}: Leverage = '{leverage_value}' (N hoặc 0), bỏ qua")
            continue
        
        if not is_number(leverage_value):
            logger.debug(f"Dòng {row_count}: Leverage = '{leverage_value}' không phải số, bỏ qua")
            continue
            
        try:
            lev_float = float(leverage_value)
            if lev_float <= 0:
                logger.debug(f"Dòng {row_count}: Leverage = {lev_float} <= 0, bỏ qua")
                continue
        except (ValueError, TypeError):
            logger.debug(f"Dòng {row_count}: Lỗi convert leverage '{leverage_value}' sang float, bỏ qua")
            continue
        
        # Kiểm tra activation là số hợp lệ
        if len(d) <= activation_idx or not d[activation_idx]:
            logger.debug(f"Dòng {row_count}: Không có activation price (cột D), bỏ qua")
            continue
        if not is_number(d[activation_idx]):
            logger.debug(f"Dòng {row_count}: Activation price không phải số, bỏ qua")
            continue

        try:
            if len(d) == 0 or not d[0]:
                logger.debug(f"Dòng {row_count}: Không có symbol (cột A), bỏ qua")
                continue
                
            sym = d[0]
            
            # Validate symbol
            if not sym or not str(sym).strip():
                logger.debug(f"Dòng {row_count}: Symbol rỗng, bỏ qua")
                continue
        
            sym = str(sym).strip()
            
            # Bước 0: Kiểm tra symbol có cho phép giao dịch không
            print(f"🔍 [{row_count}] Kiểm tra trạng thái symbol {sym}...", flush=True)
            is_tradeable, error_msg, normalized_sym = is_symbol_tradeable(sym)
            if not is_tradeable:
                print(f"⏭️  {sym} KHÔNG THỂ GIAO DỊCH: {error_msg}, bỏ qua", flush=True)
                logger.warning(f"{sym} không thể giao dịch: {error_msg}")
                continue
            
            # Cập nhật symbol đã chuẩn hóa
            if normalized_sym != sym:
                logger.info(f"Symbol đã được chuẩn hóa: {sym} -> {normalized_sym}")
                sym = normalized_sym
            
            symbol = sym  # symbol đã normalize (BTC/USDT:USDT)

            # Xác định side entry theo trạng thái (LONG->buy, SHORT->sell)
            # (side lệnh ngược được suy từ dấu vị thế thực tế ở NHÁNH A)
            if type == "SELL" or type == "SHORT":
                entry_side = "sell"
            else:  # BUY / LONG / COVER
                entry_side = "buy"

            # Bước 1: Lấy vị thế hiện tại (signed). != 0 ⇒ entry đã khớp
            print(f"🔍 [{row_count}] Kiểm tra vị thế cho {symbol}...", flush=True)
            try:
                pos_amt = get_position_amt(symbol)
            except Exception as e:
                print(f"⚠️  Lỗi khi kiểm tra vị thế cho {symbol}: {e}", flush=True)
                logger.error(f"Lỗi khi kiểm tra vị thế cho {symbol}: {e}", exc_info=True)
                continue

            # ══════════════════════════════════════════════════════════════
            # NHÁNH A: ĐÃ CÓ VỊ THẾ → Đặt TP (LIMIT) và SL (STOP_MARKET), đều reduce_only
            #   - TP: giá cột G (LIMIT)          → cột G trống thì bỏ qua TP
            #   - SL: giá cột F (STOP_MARKET)    → cột F trống thì bỏ qua SL
            #   Hai lệnh độc lập, cột nào có giá thì đặt cột đó (nếu chưa có sẵn).
            # ══════════════════════════════════════════════════════════════
            if pos_amt != 0:
                # side đóng vị thế (LONG->sell, SHORT->buy). Dùng chung cho cả TP và SL.
                close_side = "sell" if pos_amt > 0 else "buy"
                # Khối lượng đóng = toàn bộ vị thế (làm tròn theo precision)
                try:
                    close_amount = float(exchange.amount_to_precision(symbol, abs(pos_amt)))
                except Exception:
                    close_amount = abs(pos_amt)

                print(f"🔍 [{row_count}] {symbol} đã có vị thế ({pos_amt}) → kiểm tra TP/SL (side đóng={close_side})...", flush=True)

                if close_amount <= 0:
                    print(f"⚠️  {symbol}: Khối lượng đóng không hợp lệ ({close_amount}), bỏ qua", flush=True)
                    continue

                # ---------- TP: LỆNH NGƯỢC CHỐT LỜI (LIMIT reduce_only) - cột G ----------
                if len(d) > reverse_idx and d[reverse_idx] and is_number(str(d[reverse_idx]).replace('%', '')):
                    try:
                        tp_exists = has_pending_reverse_limit_order(symbol, close_side)
                    except Exception as e:
                        print(f"⚠️  Lỗi kiểm tra TP {symbol}: {e}", flush=True)
                        logger.error(f"Lỗi kiểm tra TP {symbol}: {e}", exc_info=True)
                        tp_exists = True  # lỗi API → coi như đã có, không đặt để tránh trùng

                    if tp_exists:
                        print(f"⏭️  {symbol} đã có lệnh TP, bỏ qua TP", flush=True)
                    else:
                        tp_price_raw = float(str(d[reverse_idx]).replace('%', ''))
                        if tp_price_raw <= 0:
                            print(f"⚠️  {symbol}: Giá TP = {tp_price_raw} (phải > 0), bỏ qua TP", flush=True)
                        else:
                            try:
                                tp_price = float(exchange.price_to_precision(symbol, tp_price_raw))
                            except Exception:
                                tp_price = tp_price_raw
                            if tp_price > 0:
                                try:
                                    print(f"📤 Tạo TP (LIMIT reduce_only): {symbol} {close_side} {close_amount} @ {tp_price}", flush=True)
                                    tp_order = order_helper.create_limit_order(
                                        symbol=symbol, side=close_side, amount=close_amount,
                                        limit_price=tp_price, reduce_only=True
                                    )
                                    order_logger.info(f"LỆNH NGƯỢC (TP, reduceOnly) | {symbol} | {close_side} | Limit: {tp_price} | Amount: {close_amount} | Order ID: {tp_order.get('id', 'N/A')}")
                                    printf(symbol, tp_order)
                                    msg = f"🔁 <b>LỆNH TP (LIMIT reduce_only)</b>\n\n<b>Mã:</b> {symbol}\n<b>Side:</b> {close_side.upper()}\n<b>Giá TP:</b> {tp_price}\n<b>Khối lượng:</b> {close_amount}"
                                    telegram_factory.send_tele(msg, cst.chat_id, True, True)
                                    print(f"✅ Đã tạo TP cho {symbol}", flush=True)
                                except Exception as e:
                                    print(f"❌ Lỗi tạo TP {symbol}: {e}", flush=True)
                                    logger.error(f"Lỗi tạo TP {symbol}: {e}", exc_info=True)
                else:
                    logger.info(f"{symbol}: cột G (TP) rỗng → không đặt TP")

                # ---------- SL: CẮT LỖ (STOP_MARKET reduce_only) - cột F ----------
                if len(d) > sl_idx and d[sl_idx] and is_number(str(d[sl_idx]).replace('%', '')):
                    try:
                        sl_exists = has_pending_stop_market_order(symbol, close_side)
                    except Exception as e:
                        print(f"⚠️  Lỗi kiểm tra SL {symbol}: {e}", flush=True)
                        logger.error(f"Lỗi kiểm tra SL {symbol}: {e}", exc_info=True)
                        sl_exists = True  # lỗi API → coi như đã có, không đặt để tránh trùng

                    if sl_exists:
                        print(f"⏭️  {symbol} đã có lệnh SL, bỏ qua SL", flush=True)
                    else:
                        sl_price_raw = float(str(d[sl_idx]).replace('%', ''))
                        if sl_price_raw <= 0:
                            print(f"⚠️  {symbol}: Giá SL = {sl_price_raw} (phải > 0), bỏ qua SL", flush=True)
                        else:
                            try:
                                sl_price = float(exchange.price_to_precision(symbol, sl_price_raw))
                            except Exception:
                                sl_price = sl_price_raw
                            if sl_price > 0:
                                try:
                                    print(f"📤 Tạo SL (STOP_MARKET reduce_only): {symbol} {close_side} {close_amount} @ stop={sl_price}", flush=True)
                                    sl_order = order_helper.create_stop_market_order(
                                        symbol=symbol, side=close_side, amount=close_amount,
                                        stop_price=sl_price, reduce_only=True
                                    )
                                    order_logger.info(f"LỆNH SL (STOP_MARKET, reduceOnly) | {symbol} | {close_side} | Stop: {sl_price} | Amount: {close_amount} | Order ID: {sl_order.get('id', 'N/A')}")
                                    printf(symbol, sl_order)
                                    msg = f"🛑 <b>LỆNH SL (STOP_MARKET reduce_only)</b>\n\n<b>Mã:</b> {symbol}\n<b>Side:</b> {close_side.upper()}\n<b>Giá SL:</b> {sl_price}\n<b>Khối lượng:</b> {close_amount}"
                                    telegram_factory.send_tele(msg, cst.chat_id, True, True)
                                    print(f"✅ Đã tạo SL cho {symbol}", flush=True)
                                except Exception as e:
                                    print(f"❌ Lỗi tạo SL {symbol}: {e}", flush=True)
                                    logger.error(f"Lỗi tạo SL {symbol}: {e}", exc_info=True)
                else:
                    logger.info(f"{symbol}: cột F (SL) rỗng → không đặt SL")

                continue

            # ══════════════════════════════════════════════════════════════
            # NHÁNH B: CHƯA CÓ VỊ THẾ → Đặt LỆNH 1 (entry LIMIT)
            # ══════════════════════════════════════════════════════════════
            side = entry_side

            # Bước 2: Kiểm tra symbol đã có LIMIT ENTRY pending cùng side chưa
            print(f"🔍 [{row_count}] Kiểm tra pending LIMIT entry cho {symbol} (side={side})...", flush=True)
            try:
                if has_pending_limit_order(symbol, side):
                    print(f"⏭️  {symbol} đã có lệnh chờ LIMIT entry, bỏ qua", flush=True)
                    logger.info(f"{symbol} Đã có lệnh chờ LIMIT entry, bỏ qua")
                    continue
            except Exception as e:
                print(f"⚠️  Lỗi khi kiểm tra pending orders cho {symbol}: {e}", flush=True)
                logger.error(f"Lỗi khi kiểm tra pending orders cho {symbol}: {e}", exc_info=True)
                continue

            # ⚠️ BƯỚC 3: KIỂM TRA LẠI B2 TRƯỚC KHI TẠO LỆNH (Safety Check)
            # Nếu B2 đã chuyển sang CHỜ/STOP trong khi đang scan, dừng ngay lập tức
            current_state, check_time = get_current_state()
            if current_state != state_value:
                print(f"⚠️ CẢNH BÁO: Trạng thái B2 đã thay đổi từ '{state_value}' -> '{current_state}' (lúc {check_time.strftime('%H:%M:%S')})", flush=True)
                logger.warning(f"[STATE CHANGED] B2 đã thay đổi từ '{state_value}' (lúc {read_time.strftime('%H:%M:%S')}) -> '{current_state}' (lúc {check_time.strftime('%H:%M:%S')})")
                logger.warning(f"Dừng scan để tránh tạo lệnh sai trạng thái. Đã xử lý {row_count-1}/{len(don_bay)} dòng")
                print(f"🛑 Dừng scan ngay lập tức! Đã xử lý {row_count-1}/{len(don_bay)} dòng", flush=True)
                break  # Thoát khỏi vòng lặp ngay lập tức

            print(f"🎯 Vào lệnh 1 {state_value}: {sym} (Leverage {d[leverage_idx]}x)", flush=True)
            logger.info(f"--- Vào lệnh 1 {state_value}: {sym} LIMIT đòn bẩy: {d[leverage_idx]} [B2 confirmed: {current_state} @ {check_time.strftime('%H:%M:%S')}]")

            # ✅ Logic tính vốn mới (theo thứ tự ưu tiên):
            # 1. Cột H (nếu có) → Dùng ngay
            # 2. E2 có giá trị → capitalMoney = D1 * E2 (min 10)
            # 3. E2 rỗng → capitalMoney = D2
            # 4. E2 và D2 đều rỗng → Đã check ở trên (không chạy vào đây)
            
            capitalMoney = None
            
            # Ưu tiên 1: Cột H (capital riêng cho dòng này)
            try:
                if len(d) > capital_idx and d[capital_idx]:
                    h_value = str(d[capital_idx]).strip()
                    if h_value and h_value not in ["#DIV/0!", "#VALUE!", "#ERROR!", "#N/A"]:
                        capitalMoney = float(h_value)
                        logger.info(f"{sym}: Dùng vốn từ cột H = {capitalMoney} USDT")
            except (ValueError, TypeError) as e:
                logger.warning(f"{sym}: Lỗi parse cột H: {e}")
            
            # Ưu tiên 2 & 3: Tính từ D1/D2/E2
            if capitalMoney is None:
                if e2_total is not None:
                    # E2 có giá trị → capitalMoney = D1 * E2 (min 10)
                    if d1_percent is not None:
                        capitalMoney = d1_percent * e2_total
                        if capitalMoney < 10:
                            logger.info(f"{sym}: D1*E2 = {capitalMoney:.2f} < 10, dùng 10 USDT")
                            capitalMoney = 10
                        else:
                            logger.info(f"{sym}: Dùng vốn = D1*E2 = {d1_percent*100:.2f}% * {e2_total} = {capitalMoney:.2f} USDT")
                    else:
                        # E2 có nhưng D1 rỗng → Dùng D2
                        if d2_default is not None:
                            capitalMoney = d2_default
                            logger.info(f"{sym}: E2 có nhưng D1 rỗng, dùng D2 = {capitalMoney} USDT")
                        else:
                            # E2 có, D1 và D2 đều rỗng → Không đặt lệnh
                            print(f"⏭️  {sym}: E2 có nhưng D1 và D2 rỗng → Bỏ qua", flush=True)
                            logger.warning(f"{sym}: Bỏ qua - E2={e2_total} nhưng không có D1 và D2")
                            continue
                else:
                    # E2 rỗng → Dùng D2
                    if d2_default is not None:
                        capitalMoney = d2_default
                        logger.info(f"{sym}: E2 rỗng, dùng D2 = {capitalMoney} USDT")
                    else:
                        # E2 và D2 đều rỗng → Không đặt lệnh (đã check ở trên, nhưng double check)
                        print(f"⏭️  {sym}: E2 và D2 đều rỗng → Bỏ qua", flush=True)
                        logger.warning(f"{sym}: Bỏ qua - Không có vốn")
                        continue
            
            # Validate capitalMoney >= 10
            if capitalMoney < 10:
                print(f"⏭️  {sym}: Vốn = {capitalMoney:.2f} USDT < 10 USDT (tối thiểu) → Bỏ qua", flush=True)
                logger.warning(f"{sym}: Bỏ qua - Vốn {capitalMoney:.2f} < 10 USDT")
                continue
            
            print(f"💰 {sym}: Vốn = {capitalMoney:.2f} USDT", flush=True)

            # symbol & side đã được xác định ở NHÁNH B phía trên

            # Set leverage
            try:
                leverage = int(float(d[leverage_idx]))
                if leverage > 0:
                    exchange.setLeverage(leverage, symbol)
                    logger.info(f"Đã thiết lập đòn bẩy {leverage} cho cặp giao dịch {symbol}")
            except Exception as e:
                print(f"⚠️ Không thể set leverage cho {symbol}: {e}", flush=True)
                logger.warning(f"Không thể set leverage: {e}")
                leverage = 1
                
            # LỆNH LIMIT: cột D là giá đặt limit (biến activation_price giữ tên cũ để tối thiểu thay đổi)
            activation_price_raw = float(str(d[activation_idx]).replace("%", ""))
            
            # Log giá trị raw trước khi làm tròn
            logger.info(f"[ACTIVATION PRICE] {symbol} - Giá gốc từ sheet: {activation_price_raw}")
            print(f"📊 {symbol} - Giá kích hoạt gốc: {activation_price_raw}", flush=True)
            
            # Validate activation_price > 0 TRƯỚC KHI làm tròn
            if activation_price_raw <= 0:
                print(f"⚠️  {symbol}: Activation price = {activation_price_raw} (phải > 0), bỏ qua", flush=True)
                logger.warning(f"{symbol}: Activation price = {activation_price_raw} (phải > 0), bỏ qua")
                continue
            
            # Sử dụng exchange.price_to_precision() để làm tròn đúng theo quy tắc Binance
            try:
                activation_price_str = exchange.price_to_precision(symbol, activation_price_raw)
                activation_price = float(activation_price_str)
                logger.info(f"[ACTIVATION PRICE] {symbol} - Sau khi price_to_precision(): {activation_price} (từ string: '{activation_price_str}')")
                print(f"📊 {symbol} - Giá sau khi làm tròn (price_to_precision): {activation_price}", flush=True)
            except Exception as e:
                # Fallback: dùng round nếu price_to_precision lỗi
                try:
                    precision = binance_utils.get_price_precision(symbol)
                    activation_price = round(activation_price_raw, precision)
                    logger.warning(f"Sử dụng round() fallback cho {symbol}: {e}")
                except Exception as e2:
                    print(f"⚠️  {symbol}: Không thể làm tròn activation price: {e2}, bỏ qua", flush=True)
                    logger.error(f"{symbol}: Không thể làm tròn activation price: {e2}", exc_info=True)
                    continue
            
            # Validate activation_price > 0 SAU KHI làm tròn (có thể bị làm tròn thành 0 nếu quá nhỏ)
            if activation_price <= 0:
                print(f"⚠️  {symbol}: Activation price sau khi làm tròn = {activation_price} (phải > 0), bỏ qua. Giá gốc: {activation_price_raw}", flush=True)
                logger.warning(f"{symbol}: Activation price sau khi làm tròn = {activation_price} (phải > 0), bỏ qua. Giá gốc: {activation_price_raw}")
                continue
            
            # Tính amount và notional
            ticker = exchange.fetch_ticker(symbol)
            lastPrice = ticker["last"]
            amountUsdt = float(capitalMoney)
            
            # [VALIDATION] Kiểm tra activation price logic với giá hiện tại
            # BUY (LONG): activation_price phải < lastPrice (chờ giá giảm xuống)
            # SELL (SHORT): activation_price phải > lastPrice (chờ giá tăng lên)
            if side == "buy":
                if activation_price >= lastPrice:
                    print(f"⚠️  {symbol}: BUY với activation_price={activation_price} >= giá hiện tại={lastPrice} → Sẽ kích hoạt ngay! Bỏ qua", flush=True)
                    logger.warning(f"{symbol}: BUY activation_price={activation_price} >= lastPrice={lastPrice} (Order would immediately trigger)")
                    continue
            elif side == "sell":
                if activation_price <= lastPrice:
                    print(f"⚠️  {symbol}: SELL với activation_price={activation_price} <= giá hiện tại={lastPrice} → Sẽ kích hoạt ngay! Bỏ qua", flush=True)
                    logger.warning(f"{symbol}: SELL activation_price={activation_price} <= lastPrice={lastPrice} (Order would immediately trigger)")
                    continue
            
            # [FIX] Lệnh LIMIT khớp tại GIÁ LIMIT → khối lượng tính theo activation_price
            # (không dùng lastPrice, tránh lệch vốn/notional so với ý định)
            raw_amount = amountUsdt / activation_price
            try:
                amount = float(exchange.amount_to_precision(symbol, raw_amount))
                logger.info(f"[AMOUNT FIX] {symbol}: Raw={raw_amount} -> Rounded={amount}")
            except Exception as e:
                print(f"⚠️ Lỗi làm tròn số lượng cho {symbol}: {e}", flush=True)
                amount = raw_amount # Fallback

            # Tính notional = activation_price * amount (Binance tính notional dựa trên activation_price)
            notional = activation_price * amount
            
            # Validate notional >= 5 USDT (yêu cầu tối thiểu của Binance)
            if notional < 5:
                print(f"⚠️  {symbol}: Notional = {notional:.4f} USDT < 5 USDT (activation_price={activation_price}, amount={amount:.4f}, vốn={amountUsdt} USDT), bỏ qua", flush=True)
                logger.warning(f"{symbol}: Notional = {notional:.4f} USDT < 5 USDT (activation_price={activation_price}, amount={amount:.4f}, vốn={amountUsdt} USDT), bỏ qua")
                continue
            
            # Cột D (activation_price) giờ là GIÁ ĐẶT LIMIT. Cột C (Callback) không còn dùng.
            limit_price = activation_price

            print(f"📤 Tạo Limit: {symbol} {side} @ {limit_price}", flush=True)
            logger.info(f"Tạo Limit: {symbol} {side} @ {limit_price}")

            order = order_helper.create_limit_order(
                symbol=symbol,
                side=side,
                amount=amount,          # Số lượng đã được làm tròn
                limit_price=limit_price,
                reduce_only=False        # Lệnh VÀO (entry), không reduce only
            )
            
            # Log chi tiết order data để debug
            logger.info(f"[ORDER DATA] {symbol} - Order structure: id={order.get('id', 'N/A')}, symbol={order.get('symbol', 'N/A')}, side={order.get('side', 'N/A')}, status={order.get('status', 'N/A')}")
            if 'info' in order and isinstance(order['info'], dict):
                info_keys = list(order['info'].keys())
                logger.info(f"[ORDER DATA] {symbol} - info keys: {info_keys}")
                if 'algoId' in order['info']:
                    logger.info(f"[ORDER DATA] {symbol} - algoId: {order['info']['algoId']}")
                if 'activatePrice' in order['info']:
                    logger.info(f"[ORDER DATA] {symbol} - activatePrice from info: {order['info']['activatePrice']}")
                if 'callbackRate' in order['info']:
                    logger.info(f"[ORDER DATA] {symbol} - callbackRate from info: {order['info']['callbackRate']}")
                if 'algoStatus' in order['info']:
                    logger.info(f"[ORDER DATA] {symbol} - algoStatus: {order['info']['algoStatus']}")
            
            msg = f"✅ <b>LỆNH CHỜ (LIMIT)</b>\n\n<b>Mã:</b> {symbol}\n<b>Side:</b> {type}\n<b>Giá đặt:</b> {limit_price}\n<b>Đòn bẩy:</b> {leverage}x\n<b>Vốn:</b> {capitalMoney} USDT"

            # Log vào order.log
            order_logger.info(f"LỆNH 1 (Entry LIMIT) | {symbol} | {type} | Limit: {limit_price} | Leverage: {leverage}x | Capital: {capitalMoney} USDT | Order ID: {order.get('id', 'N/A')}")
            
            printf(symbol, order)
            print(f"✅ Đã tạo lệnh LIMIT cho {symbol}", flush=True)
            logger.info(f"✅ Lệnh LIMIT đã được tạo thành công cho {symbol} (Order ID: {order.get('id', 'N/A')})")

            # Cập nhật local cache ngay sau khi đặt lệnh thành công
            _cached_algo_id = order.get('info', {}).get('algoId') or order.get('id', 'unknown')
            add_to_order_cache(sym, _cached_algo_id)

            telegram_factory.send_tele(msg, cst.chat_id, True, True)

        except Exception as e:
            print(f"❌ Lỗi xử lý dòng {row_count} (symbol: {sym if 'sym' in locals() else 'N/A'}): {e}", flush=True)
            logger.error(f"Lỗi khi xử lý dòng {row_count}: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            continue
    
    # Kiểm tra lại B2 sau khi scan xong
    final_state, final_time = get_current_state(force=True)
    print(f"✅ Hoàn thành scan {state_value} - Đã xử lý {row_count}/{len(don_bay)} dòng", flush=True)
    logger.info(f"[SCAN END] Hoàn thành scan {state_value} - Đã xử lý {row_count}/{len(don_bay)} dòng")
    
    # Cảnh báo nếu B2 đã thay đổi trong quá trình scan
    if final_state != state_value:
        print(f"⚠️ LƯU Ý: B2 đã thay đổi trong quá trình scan: '{state_value}' -> '{final_state}'", flush=True)
        print(f"   Thời gian bắt đầu: {read_time.strftime('%H:%M:%S')}", flush=True)
        print(f"   Thời gian kết thúc: {final_time.strftime('%H:%M:%S')}", flush=True)
        logger.warning(f"[STATE CHANGED DURING SCAN] B2: '{state_value}' ({read_time.strftime('%H:%M:%S')}) -> '{final_state}' ({final_time.strftime('%H:%M:%S')})")
    else:
        logger.info(f"[B2 STABLE] Trạng thái B2 không đổi trong suốt quá trình scan: {state_value}")

def printf(name, data):
    """Lưu thông tin order vào file"""
    try:
        print(data, flush=True)
        pathDir = str(Path().absolute()).replace("\\", "/")
        
        # Tìm order ID từ nhiều nguồn có thể (theo thứ tự ưu tiên)
        order_id = None
        
        # Ưu tiên 1: data['id'] (CCXT standard)
        if 'id' in data:
            order_id = str(data['id'])
        
        # Ưu tiên 2: data['info']['algoId'] (Binance algo orders)
        elif 'info' in data and isinstance(data['info'], dict):
            if 'algoId' in data['info']:
                order_id = str(data['info']['algoId'])
            elif 'orderId' in data['info']:
                order_id = str(data['info']['orderId'])
            elif 'id' in data['info']:
                order_id = str(data['info']['id'])
            elif 'order_id' in data['info']:
                order_id = str(data['info']['order_id'])
        
        # Nếu không tìm thấy order ID, dùng timestamp
        if not order_id:
            order_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            logger.warning(f"Không tìm thấy order ID trong response cho {name}, dùng timestamp: {order_id}")
        
        filename = str(cst.account_dir("order") / str(name) / (str(order_id) + ".txt"))  # [MULTI-ACC]
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Ghi file với UTF-8 encoding
        with open(filename, "w", encoding='utf-8') as f:
            f.write(str(data))
            
    except Exception as e:
        logger.error(f"Lỗi trong printf() cho {name}: {e}", exc_info=True)
        print(f"⚠️ Lỗi khi lưu order file cho {name}: {e}", flush=True)    

print(f"🚀 Khởi động bot - Chạy mỗi {cst.delay_vao_lenh} giây", flush=True)
logger.info(f"Khởi động bot - Chạy mỗi {cst.delay_vao_lenh} giây")

# ✅ Khởi tạo Google Sheets API trước khi bắt đầu
print("🔄 Đang khởi tạo Google Sheets API...", flush=True)
try:
    gg_sheet_factory.init_sheet_api()
    print("✅ Google Sheets API đã sẵn sàng", flush=True)
except Exception as e:
    print(f"⚠️ Lỗi khởi tạo Google Sheets API: {e}", flush=True)
    logger.error(f"Lỗi khởi tạo Google Sheets API: {e}", exc_info=True)

# ✅ Load order cache từ file (chống lặp đơn qua restart)
_load_order_cache()

# ✅ Khởi động Telegram Command Bot (chỉ khi run_tele_command = true; mặc định false nếu chưa cấu hình)
if getattr(cst, 'run_tele_command', False):
    try:
        import tele_command
        tele_command.start_tele_command_thread()
        print("✅ Telegram command bot đã khởi động", flush=True)
        logger.info("Telegram command bot đã khởi động")
    except Exception as e:
        print(f"⚠️ Lỗi khởi động Telegram command bot: {e}", flush=True)
        logger.error(f"Lỗi khởi động tele_command: {e}", exc_info=True)
else:
    print("⏭️ Telegram command bot tắt (run_tele_command = false)", flush=True)
    logger.info("Telegram command bot không chạy (run_tele_command = false)")

while True:
    try:
        resync_exchange_time(exchange)  # [Fix1] chống clock drift -> hết -1021
        do_it()
        print(f"⏳ Chờ {cst.delay_vao_lenh} giây trước lần scan tiếp theo...", flush=True)
        sys.stdout.flush()  # Đảm bảo flush trước khi sleep
        
    except Exception as e:
        if '-1021' in str(e) or 'recvWindow' in str(e):
            resync_exchange_time(exchange, min_interval=0)  # [Fix4] ép resync ccxt ngay
        print(f"❌ Tổng Lỗi: {e}", flush=True)
        logger.error(f"Tổng lỗi: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        print(f"⏳ Chờ {cst.delay_vao_lenh} giây trước khi thử lại...", flush=True)
        sys.stdout.flush()

    time.sleep(cst.delay_vao_lenh)