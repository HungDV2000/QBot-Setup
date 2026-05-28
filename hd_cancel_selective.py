"""
Bot xóa lệnh có chọn lọc trên Binance
- Đọc sheet "Chờ và khớp"
- Cột J–M (trạng thái xóa):
  - J XOÁ ENTRY → xóa lệnh 1 (entry)
  - K XOÁ SL/TP → xóa cặp lệnh 2–3 (SL + TP)
  - L XOÁ LỆNH SÓT → xóa lệnh đơn 2–3 sót
  - M XOÁ LỆNH NGƯỢC → xóa tất cả khi vị thế ĐÓNG
- Sau xử lý: clear tick tại J–M
"""

import ccxt
import cst
from pathlib import Path
import time
import telegram_factory
import logging
import os
import requests
import hmac
import hashlib
import urllib.parse
import gg_sheet_factory
from datetime import datetime

file_name = os.path.basename(os.path.abspath(__file__))
os.system(f"title {file_name} - {cst.key_name}")

# Tạo thư mục logs/ nếu chưa có
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Tạo tên file log với timestamp
log_timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
log_filename = logs_dir / f'hd_cancel_selective_{log_timestamp}.txt'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# Tạo file handler
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

# Khởi tạo exchange
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

# Load markets để exchange biết các symbols
try:
    exchange.load_markets(True)  # Force reload
    logger.info("✅ Đã load markets thành công")
except Exception as e:
    logger.warning(f"⚠️ Lỗi load markets: {e}")

logger.info("✅ Khởi tạo Binance exchange thành công")


def call_binance_api_direct(method, endpoint, params=None):
    """
    Gọi Binance API trực tiếp bằng requests (để hủy algo orders)
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
        if method.upper() == 'DELETE':
            response = requests.delete(url, params=params, headers=headers, timeout=10)
        elif method.upper() == 'GET':
            response = requests.get(url, params=params, headers=headers, timeout=10)
        else:
            return None

        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        # Chỉ log 400 ở debug level (delivery futures hoặc symbol không hợp lệ)
        if e.response.status_code == 400:
            logger.debug(f"Lỗi 400 cho symbol {params.get('symbol')}: {e}")
        else:
            logger.error(f"Lỗi HTTP khi gọi Binance API ({method} {endpoint}): {e}")
        return None
    except Exception as e:
        logger.error(f"Lỗi khi gọi Binance API trực tiếp ({method} {endpoint}): {e}")
        return None


def get_all_algo_orders_for_symbol(symbol):
    """
    Lấy TẤT CẢ algo orders cho một symbol (bao gồm cả NEW, TRIGGERED, FINISHED, CANCELED)
    """
    try:
        symbol_clean = symbol.replace('/', '').replace(':USDT', '')
        
        # ⚠️ BỎ QUA delivery perpetual futures (symbols có '-', ví dụ: BTCUSDT-260626)
        if '-' in symbol_clean:
            logger.debug(f"Bỏ qua delivery futures: {symbol_clean}")
            return []
        
        params = {'symbol': symbol_clean}

        response = call_binance_api_direct('GET', '/fapi/v1/allAlgoOrders', params)

        if not response:
            return []

        if isinstance(response, list):
            return response
        elif isinstance(response, dict):
            if 'data' in response:
                return response['data']
            return []
        return []

    except Exception as e:
        # Chỉ log lỗi HTTP 400 ở debug level
        if '400' in str(e):
            logger.debug(f"Lỗi 400 cho {symbol} - có thể delivery futures, bỏ qua")
        else:
            logger.error(f"Lỗi khi lấy algo orders cho {symbol}: {e}", exc_info=True)
        return []


def get_order_type_from_algo(algo):
    """
    Phân biệt loại algo order: SL (Stop Loss), TP (Take Profit), ENTRY (Entry Order)

    Dựa vào:
    - reduceOnly: SL/TP đều là reduceOnly=true, Entry thường reduceOnly=false
    - callbackRate: TP (Trailing Stop) có callbackRate > 0, SL có callbackRate = 0
    - algoType: CONDITIONAL/VP/TRAILING_STOP_MARKET thường là TP

    Returns: 'SL', 'TP', 'ENTRY', 'UNKNOWN'
    """
    try:
        # Ưu tiên lấy reduceOnly từ info (Binance API đặt trong info, không phải top-level)
        info = algo.get('info', {})
        reduce_only = info.get('reduceOnly', algo.get('reduceOnly', False))
        callback_rate = float(info.get('callbackRate', algo.get('callbackRate', algo.get('priceRate', 0)) or 0))
        algo_type = algo.get('algoType', info.get('algoType', '')).upper()

        logger.info(
            f"[ORDER TYPE] algoId={algo.get('algoId')}, algoType={algo_type}, "
            f"reduceOnly={reduce_only}, callbackRate={callback_rate}"
        )

        # TP (Take Profit): reduceOnly=true + có callbackRate → Trailing Stop
        if reduce_only and callback_rate > 0:
            return 'TP'

        # SL (Stop Loss): reduceOnly=true + callbackRate=0 → Stop Market thường
        if reduce_only and callback_rate == 0:
            return 'SL'

        # Entry Order: reduceOnly=false hoặc None
        if not reduce_only:
            return 'ENTRY'

        return 'UNKNOWN'

    except Exception as e:
        logger.warning(f"Lỗi phân biệt loại algo order: {e}")
        return 'UNKNOWN'


def classify_algo_orders(orders):
    """
    Phân loại algo orders thành SL, TP, ENTRY

    Returns: dict với keys 'SL', 'TP', 'ENTRY', 'UNKNOWN'
    """
    classified = {
        'SL': [],
        'TP': [],
        'ENTRY': [],
        'UNKNOWN': []
    }

    for algo in orders:
        order_type = get_order_type_from_algo(algo)
        classified[order_type].append(algo)

    return classified


def get_active_algo_orders(symbol):
    """
    Lấy algo orders đang active (NEW) cho một symbol
    """
    all_orders = get_all_algo_orders_for_symbol(symbol)
    active_orders = [o for o in all_orders if o.get('algoStatus', '').upper() == 'NEW']
    
    # Debug: log chi tiết
    logger.debug(f"[get_active_algo_orders] {symbol}: Tổng {len(all_orders)} orders, {len(active_orders)} active (NEW)")
    for o in all_orders[:5]:  # Log tối đa 5 orders đầu
        logger.debug(f"  → algoId={o.get('algoId')}, algoType={o.get('algoType')}, status={o.get('algoStatus')}, reduceOnly={o.get('reduceOnly')}, callbackRate={o.get('callbackRate')}")
    
    return active_orders


def get_removable_algo_orders(symbol):
    """
    Lấy algo orders có thể xóa: NEW hoặc TRIGGERED
    """
    all_orders = get_all_algo_orders_for_symbol(symbol)
    return [o for o in all_orders if o.get('algoStatus', '').upper() in ['NEW', 'TRIGGERED']]


def cancel_algo_order(symbol, algo_id, algo_type=""):
    """
    Hủy một algo order cụ thể
    """
    try:
        symbol_clean = symbol.replace('/', '').replace(':USDT', '')
        params = {
            'symbol': symbol_clean,
            'algoId': algo_id
        }
        response = call_binance_api_direct('DELETE', '/fapi/v1/algoOrder', params)

        if response and str(response.get('code', '')) == '200':
            logger.info(f"✅ Đã hủy algo order {algo_id} [{algo_type}] cho {symbol}")
            return True
        else:
            logger.warning(f"Không thể hủy algo order {algo_id}: {response}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi hủy algo order {algo_id}: {e}")
        return False


def cancel_open_order(symbol, order_id):
    """
    Hủy một open order thông thường
    """
    try:
        exchange.cancel_order(order_id, symbol)
        logger.info(f"✅ Đã hủy open order {order_id} cho {symbol}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi hủy open order {order_id}: {e}")
        return False


def get_open_orders(symbol):
    """
    Lấy open orders cho một symbol
    """
    try:
        return exchange.fetch_open_orders(symbol)
    except Exception as e:
        logger.error(f"Lỗi khi lấy open orders cho {symbol}: {e}")
        return []


def format_symbol_for_api(symbol):
    """Chuẩn hóa symbol về format API: HOMEUSDT"""
    return symbol.replace('/', '').replace(':USDT', '')


def format_symbol_ccxt(symbol):
    """Chuẩn hóa symbol về format CCXT: HOME/USDT:USDT"""
    symbol = symbol.strip().upper()
    if ':USDT' in symbol:
        return symbol
    if '/' in symbol:
        return f"{symbol}:USDT"
    if symbol.endswith('USDT'):
        base = symbol[:-4]
        return f"{base}/USDT:USDT"
    return f"{symbol}/USDT:USDT"


def has_tick(value):
    """Kiểm tra ô có tick (giá trị không rỗng)"""
    if value is None:
        return False
    val_str = str(value).strip()
    return val_str != '' and val_str.upper() not in ['N', 'NO', 'FALSE', '0']


def has_delete_tick(value):
    """
    Tick xóa cho cột J/K/L/M phải rõ ràng để tránh kích hoạt nhầm.
    Chỉ chấp nhận các giá trị mang nghĩa bật rõ ràng.
    """
    if value is None:
        return False
    v = str(value).strip().upper()
    return v in {"Y", "YES", "TRUE", "1", "X", "TICK", "✓", "✔"}


def split_reduce_only_open_orders(open_orders):
    """
    Tách open orders reduceOnly thành SL / TP / UNKNOWN để xóa chính xác theo lựa chọn.
    """
    sl_orders = []
    tp_orders = []
    unknown_orders = []
    for o in open_orders:
        if not o.get('reduceOnly', False):
            continue
        t = str(o.get('type', '') or '').upper()
        if t in ['STOP', 'STOP_LIMIT', 'STOP_MARKET', 'STOP_LOSS', 'STOP_LOSS_LIMIT', 'STOP_LOSS_MARKET']:
            sl_orders.append(o)
        elif 'TAKE_PROFIT' in t or 'TRAILING' in t:
            tp_orders.append(o)
        else:
            unknown_orders.append(o)
    return sl_orders, tp_orders, unknown_orders


def build_ghi_status_from_binance(symbol_ccxt):
    """
    Re-check trạng thái lệnh bảo vệ trên Binance để cập nhật lại G/H/I:
      G = Có SL (Y/N)
      H = Có TP (Y/N)
      I = Số orders đang active (open + algo NEW)
    """
    try:
        open_orders = get_open_orders(symbol_ccxt)
        sl_open_orders, tp_open_orders, _ = split_reduce_only_open_orders(open_orders)
        active_algo_orders = get_active_algo_orders(symbol_ccxt)  # NEW
        classified_algo = classify_algo_orders(active_algo_orders)

        has_sl = bool(sl_open_orders or classified_algo.get('SL'))
        has_tp = bool(tp_open_orders or classified_algo.get('TP'))
        order_count = len(open_orders) + len(active_algo_orders)

        return ("Y" if has_sl else "N", "Y" if has_tp else "N", order_count)
    except Exception as e:
        logger.error(f"Lỗi build G/H/I cho {symbol_ccxt}: {e}", exc_info=True)
        return None


def process_cancellation():
    """
    Đọc sheet, kiểm tra tick cột J–M, xóa lệnh tương ứng.
    """
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*80}", flush=True)
        print(f"[{current_time}] Bắt đầu xóa lệnh có chọn lọc...", flush=True)
        print(f"{'='*80}\n", flush=True)
        logger.info(f"[{current_time}] Bắt đầu cancel orders có chọn lọc")

        # Layout A–P: J–M = tick xóa (XOÁ ENTRY / SL+TP / SÓT / NGƯỢC)
        sheet_data = gg_sheet_factory.get_cho_va_khop("A4:P100")

        if not sheet_data:
            print("⚠️  Không có dữ liệu từ sheet", flush=True)
            logger.warning("Không có dữ liệu từ sheet 'Chờ và khớp'")
            return

        symbols_to_clear_ticks = []
        rows_need_refresh_ghi = {}

        # Đếm tổng
        total_delete_1 = 0
        total_delete_23 = 0
        total_delete_23_remain = 0
        total_delete_closed = 0   # [TASK 2] Xóa tất cả lệnh ngược cho vị thế ĐÓNG
        symbols_processed = 0
        symbol_reports = []

        for row_idx, row in enumerate(sheet_data, start=4):
            try:
                if not row or len(row) == 0:
                    continue

                # Lấy symbol (cột A, index 0)
                symbol_raw = str(row[0]).strip() if len(row) > 0 and row[0] else ""

                # Validate symbol (phải chứa USDT)
                if not symbol_raw or "USDT" not in symbol_raw.upper():
                    continue

                # Format symbol
                symbol_ccxt = format_symbol_ccxt(symbol_raw)
                symbol_api = format_symbol_for_api(symbol_raw)

                print(f"\n🔍 [{row_idx}] Xử lý: {symbol_raw}", flush=True)

                # J(9) XOÁ ENTRY, K(10) XOÁ SL/TP, L(11) XOÁ SÓT, M(12) XOÁ NGƯỢC
                col_j = row[9] if len(row) > 9 else None
                delete_lenh_1 = has_delete_tick(col_j)

                col_k = row[10] if len(row) > 10 else None
                delete_cap_23 = has_delete_tick(col_k)

                col_l = row[11] if len(row) > 11 else None
                delete_don_23 = has_delete_tick(col_l)

                col_m = row[12] if len(row) > 12 else None
                delete_all_closed = has_delete_tick(col_m)

                # Đọc trạng thái D để biết có phải vị thế ĐÓNG không
                col_d_status = str(row[3]).strip().upper() if len(row) > 3 and row[3] else ""
                is_closed_position = col_d_status == "ĐÓNG"

                logger.info(
                    f"[{row_idx}] {symbol_raw}: D={col_d_status} | "
                    f"J(entry)={delete_lenh_1}, K(SL+TP)={delete_cap_23}, L(sót)={delete_don_23}, M(ngược)={delete_all_closed}"
                )

                # Nếu không có tick nào, bỏ qua
                if not (delete_lenh_1 or delete_cap_23 or delete_don_23 or delete_all_closed):
                    print(f"   ⏭️  Không có tick xóa, bỏ qua", flush=True)
                    continue

                if delete_all_closed and not is_closed_position:
                    print(f"   ⚠️  [M] Cột D='{col_d_status}' không phải ĐÓNG — vẫn xử lý theo yêu cầu user", flush=True)
                    logger.warning(f"[{row_idx}] {symbol_raw}: Tick M nhưng D={col_d_status} (expected ĐÓNG)")

                symbols_processed += 1
                selected_tick_cols = []
                if delete_lenh_1:
                    selected_tick_cols.append("J")
                if delete_cap_23:
                    selected_tick_cols.append("K")
                if delete_don_23:
                    selected_tick_cols.append("L")
                if delete_all_closed:
                    selected_tick_cols.append("M")
                symbols_to_clear_ticks.append((row_idx, selected_tick_cols))
                rows_need_refresh_ghi[row_idx] = symbol_ccxt

                row_report = {
                    'symbol': symbol_raw,
                    'row': row_idx,
                    'ccxt': symbol_ccxt,
                    'd_status': col_d_status,
                    'ticks': [],
                    'details': [],
                }
                if delete_lenh_1:
                    row_report['ticks'].append('J — XOÁ ENTRY')
                if delete_cap_23:
                    row_report['ticks'].append('K — XOÁ SL/TP')
                if delete_don_23:
                    row_report['ticks'].append('L — XOÁ LỆNH SÓT')
                if delete_all_closed:
                    row_report['ticks'].append('M — XOÁ LỆNH NGƯỢC')

                # === XÓA LỆNH 1 (Entry Order) ===
                if delete_lenh_1:
                    print(f"   🗑️  [J] Xóa lệnh 1 (entry order)...", flush=True)
                    logger.info(f"[{symbol_raw}] Bắt đầu xóa lệnh 1 (entry order)")

                    deleted_count = 0
                    m_items = []

                    # 1️⃣ XÓA OPEN ORDERS THÔNG THƯỜNG (LIMIT, MARKET, etc.)
                    open_orders = get_open_orders(symbol_ccxt)

                    entry_orders = []
                    other_orders = []
                    for order in open_orders:
                        reduce_only = order.get('reduceOnly', False)
                        if not reduce_only:
                            entry_orders.append(order)
                        else:
                            other_orders.append(order)

                    logger.info(f"[{symbol_raw}] Tìm thấy {len(open_orders)} open orders: {len(entry_orders)} ENTRY, {len(other_orders)} OTHER")

                    for order in entry_orders:
                        order_id = order.get('id')
                        if order_id:
                            if cancel_open_order(symbol_ccxt, order_id):
                                deleted_count += 1
                                total_delete_1 += 1
                                ot = str(order.get('type', '') or '').upper()
                                m_items.append(f"open #{order_id} ({ot or 'ORDER'})")

                    # 2️⃣ XÓA ENTRY ALGO ORDERS (NEW + TRIGGERED, reduceOnly=False)
                    # Dùng get_removable_algo_orders để bắt cả TRIGGERED (trailing đã kích hoạt)
                    removable_algo = get_removable_algo_orders(symbol_ccxt)
                    classified = classify_algo_orders(removable_algo)
                    entry_algo_orders = classified.get('ENTRY', [])

                    logger.info(f"[{symbol_raw}] Tìm thấy {len(entry_algo_orders)} ENTRY algo orders (NEW+TRIGGERED)")

                    for algo in entry_algo_orders:
                        algo_id = algo.get('algoId')
                        if algo_id:
                            if cancel_algo_order(symbol_ccxt, algo_id, "ENTRY"):
                                deleted_count += 1
                                total_delete_1 += 1
                                logger.info(f"[{symbol_raw}] Đã xóa ENTRY algo: algoId={algo_id}, status={algo.get('algoStatus')}")
                                st = str(algo.get('algoStatus', '') or '')
                                m_items.append(f"ENTRY algo #{algo_id} ({st})")

                    print(f"   ✅ Đã xóa {deleted_count} lệnh entry cho {symbol_raw}", flush=True)
                    logger.info(f"[{symbol_raw}] Đã xóa {deleted_count} lệnh entry (open: {len(entry_orders)}, algo: {len(entry_algo_orders)})")
                    line_m = f"<b>Lệnh 1 (J):</b> đã hủy {deleted_count} lệnh"
                    if m_items:
                        line_m += "\n    ▸ " + "\n    ▸ ".join(m_items[:10])
                        if len(m_items) > 10:
                            line_m += f"\n    ▸ … (+{len(m_items) - 10} nữa)"
                    else:
                        line_m += "\n    <i>(Không còn lệnh entry trên sàn)</i>"
                    row_report['details'].append(line_m)

                # === XÓA CẶP LỆNH 2-3 (SL + TP) ===
                if delete_cap_23:
                    print(f"   🗑️  [K] Xóa cặp lệnh 2-3 (SL + TP)...", flush=True)
                    logger.info(f"[{symbol_raw}] Bắt đầu xóa cặp lệnh 2-3 (SL + TP)")

                    deleted_count = 0
                    deleted_sl = 0
                    deleted_tp = 0
                    deleted_unknown = 0
                    n_items = []

                    # 1️⃣ XÓA SL/TP DẠNG OPEN ORDERS THÔNG THƯỜNG (đúng loại SL/TP)
                    open_orders = get_open_orders(symbol_ccxt)
                    sl_open_orders, tp_open_orders, unknown_open_orders = split_reduce_only_open_orders(open_orders)
                    logger.info(
                        f"[{symbol_raw}] Open reduceOnly: SL={len(sl_open_orders)}, TP={len(tp_open_orders)}, UNKNOWN={len(unknown_open_orders)}"
                    )

                    for order in sl_open_orders + tp_open_orders:
                        order_id = order.get('id')
                        order_type_str = order.get('type', 'N/A').upper()
                        if order_id:
                            if cancel_open_order(symbol_ccxt, order_id):
                                deleted_count += 1
                                total_delete_23 += 1
                                logger.info(f"[{symbol_raw}] Đã xóa SL/TP open order: id={order_id}, type={order_type_str}")
                                n_items.append(f"open reduceOnly #{order_id} ({order_type_str})")

                    # 2️⃣ XÓA SL/TP DẠNG ALGO ORDERS (NEW + TRIGGERED)
                    # Dùng get_removable_algo_orders để bắt cả TRIGGERED
                    removable_algo = get_removable_algo_orders(symbol_ccxt)
                    classified = classify_algo_orders(removable_algo)
                    sl_orders = classified['SL']
                    tp_orders = classified['TP']
                    unknown_orders = classified['UNKNOWN']
                    entry_algo_orders = classified['ENTRY']

                    logger.info(f"[{symbol_raw}] Tìm thấy {len(removable_algo)} removable algo orders (NEW+TRIGGERED):")
                    logger.info(f"  → SL: {len(sl_orders)}, TP: {len(tp_orders)}, UNKNOWN: {len(unknown_orders)}, ENTRY: {len(entry_algo_orders)}")
                    for o in sl_orders:
                        logger.info(f"     SL: algoId={o.get('algoId')}, status={o.get('algoStatus')}")
                    for o in tp_orders:
                        logger.info(f"     TP: algoId={o.get('algoId')}, callbackRate={o.get('callbackRate', o.get('info', {}).get('callbackRate', 'N/A'))}, status={o.get('algoStatus')}")
                    for o in unknown_orders:
                        logger.info(f"     UNKNOWN: algoId={o.get('algoId')}, algoType={o.get('algoType')}, reduceOnly={o.get('reduceOnly', o.get('info', {}).get('reduceOnly', 'N/A'))}")
                    for o in entry_algo_orders:
                        logger.info(f"     ENTRY (bỏ qua): algoId={o.get('algoId')}")

                    for algo in sl_orders:
                        algo_id = algo.get('algoId')
                        if algo_id:
                            if cancel_algo_order(symbol_ccxt, algo_id, 'SL'):
                                deleted_count += 1
                                deleted_sl += 1
                                total_delete_23 += 1
                                n_items.append(f"SL algo #{algo_id} ({algo.get('algoStatus', '')})")

                    for algo in tp_orders:
                        algo_id = algo.get('algoId')
                        if algo_id:
                            if cancel_algo_order(symbol_ccxt, algo_id, 'TP'):
                                deleted_count += 1
                                deleted_tp += 1
                                total_delete_23 += 1
                                n_items.append(f"TP algo #{algo_id} ({algo.get('algoStatus', '')})")

                    # K = XÓA SL/TP: KHÔNG đụng UNKNOWN để tránh xóa nhầm lệnh không thuộc SL/TP.

                    print(f"   ✅ Đã xóa {deleted_count} SL/TP orders (open SL/TP:{len(sl_open_orders)+len(tp_open_orders)}, algo SL:{deleted_sl}, TP:{deleted_tp}, UNKNOWN:{deleted_unknown}) cho {symbol_raw}", flush=True)
                    logger.info(f"[{symbol_raw}] Đã xóa {deleted_count} SL/TP orders")
                    line_n = (
                        f"<b>Cặp 2+3 (K):</b> đã hủy {deleted_count} "
                        f"(open SL:{len(sl_open_orders)}, TP:{len(tp_open_orders)}, bỏ qua unknown:{len(unknown_open_orders)}; algo SL:{deleted_sl}, TP:{deleted_tp}, khác:{deleted_unknown})"
                    )
                    if n_items:
                        line_n += "\n    ▸ " + "\n    ▸ ".join(n_items[:10])
                        if len(n_items) > 10:
                            line_n += f"\n    ▸ … (+{len(n_items) - 10} nữa)"
                    else:
                        line_n += "\n    <i>(Không còn SL/TP trên sàn)</i>"
                    row_report['details'].append(line_n)

                # === XÓA LỆNH ĐƠN 2-3 SÓT LẠI ===
                if delete_don_23:
                    print(f"   🗑️  [L] Xóa lệnh đơn 2-3 sót lại...", flush=True)
                    logger.info(f"[{symbol_raw}] Bắt đầu xóa lệnh đơn 2-3 sót lại")

                    deleted_count = 0
                    deleted_sl = 0
                    deleted_tp = 0
                    deleted_unknown = 0
                    o_items = []

                    # 1️⃣ Phân loại open reduceOnly theo SL/TP
                    open_orders = get_open_orders(symbol_ccxt)
                    sl_open_orders, tp_open_orders, unknown_open_orders = split_reduce_only_open_orders(open_orders)
                    logger.info(
                        f"[{symbol_raw}] Open reduceOnly sót: SL={len(sl_open_orders)}, TP={len(tp_open_orders)}, UNKNOWN={len(unknown_open_orders)}"
                    )

                    # 2️⃣ XÓA SL/TP DẠNG ALGO ORDERS SÓT LẠI (NEW + TRIGGERED, không xóa ENTRY) 
                    removable_orders = get_removable_algo_orders(symbol_ccxt)
                    classified = classify_algo_orders(removable_orders)
                    sl_orders = classified['SL']
                    tp_orders = classified['TP']
                    unknown_orders = classified['UNKNOWN']
                    entry_algo_orders = classified['ENTRY']

                    logger.info(f"[{symbol_raw}] Tìm thấy {len(removable_orders)} removable algo orders sót lại:")
                    logger.info(f"  → SL: {len(sl_orders)}, TP: {len(tp_orders)}, UNKNOWN: {len(unknown_orders)}, ENTRY (bỏ qua): {len(entry_algo_orders)}")
                    for o in sl_orders:
                        logger.info(f"     SL: algoId={o.get('algoId')}, status={o.get('algoStatus')}")
                    for o in tp_orders:
                        logger.info(f"     TP: algoId={o.get('algoId')}, status={o.get('algoStatus')}, callbackRate={o.get('callbackRate', o.get('info', {}).get('callbackRate', 'N/A'))}")
                    for o in unknown_orders:
                        logger.info(f"     UNKNOWN: algoId={o.get('algoId')}, status={o.get('algoStatus')}, algoType={o.get('algoType')}")

                    # L = XÓA LỆNH SÓT: chỉ xóa khi THỰC SỰ là lệnh sót 1 phía (chỉ SL hoặc chỉ TP).
                    # AN TOÀN: nếu K cũng đang tick → K đã xử lý cặp SL/TP, L bỏ qua tuyệt đối.
                    if delete_cap_23:
                        logger.warning(
                            f"[{symbol_raw}] Tick K và L cùng lúc → L bỏ qua, K đã xử lý SL/TP"
                        )
                        row_report['details'].append(
                            "<b>Lệnh sót (L):</b> bỏ qua vì K cũng đang tick (K sẽ xử lý SL/TP)."
                        )
                        # Không continue — vẫn cho phép nhánh M chạy nếu tick M
                    else:
                        has_sl_any = (len(sl_open_orders) + len(sl_orders)) > 0
                        has_tp_any = (len(tp_open_orders) + len(tp_orders)) > 0

                        if has_sl_any and has_tp_any:
                            logger.warning(
                                f"[{symbol_raw}] Tick L nhưng đang có đủ cả SL và TP → không xóa để tránh đụng logic K"
                            )
                            row_report['details'].append(
                                "<b>Lệnh sót (L):</b> bỏ qua vì đang có đủ cả SL và TP (dùng K để xóa cặp)."
                            )
                        elif not has_sl_any and not has_tp_any:
                            logger.info(f"[{symbol_raw}] Tick L nhưng không còn SL/TP nào trên sàn → bỏ qua")
                            row_report['details'].append(
                                "<b>Lệnh sót (L):</b> bỏ qua vì không còn lệnh SL/TP nào trên sàn."
                            )
                        else:
                            # Chỉ xóa 1 phía còn sót, bỏ qua UNKNOWN/ENTRY
                            open_to_cancel = sl_open_orders if has_sl_any else tp_open_orders
                            algo_to_cancel = sl_orders if has_sl_any else tp_orders
                            side_name = "SL" if has_sl_any else "TP"

                            logger.info(
                                f"[{symbol_raw}] L: Phát hiện lệnh sót {side_name} → xóa "
                                f"(open:{len(open_to_cancel)}, algo:{len(algo_to_cancel)})"
                            )

                            for order in open_to_cancel:
                                order_id = order.get('id')
                                order_type_str = order.get('type', 'N/A').upper()
                                if order_id and cancel_open_order(symbol_ccxt, order_id):
                                    deleted_count += 1
                                    total_delete_23_remain += 1
                                    if has_sl_any:
                                        deleted_sl += 1
                                    else:
                                        deleted_tp += 1
                                    logger.info(f"[{symbol_raw}] Đã xóa open order sót: id={order_id}, type={order_type_str}")
                                    o_items.append(f"open reduceOnly #{order_id} ({order_type_str})")

                            for algo in algo_to_cancel:
                                algo_id = algo.get('algoId')
                                order_type = get_order_type_from_algo(algo)
                                if algo_id:
                                    if cancel_algo_order(symbol_ccxt, algo_id, order_type):
                                        deleted_count += 1
                                        if order_type == 'SL':
                                            deleted_sl += 1
                                        elif order_type == 'TP':
                                            deleted_tp += 1
                                        else:
                                            deleted_unknown += 1
                                        total_delete_23_remain += 1
                                        logger.info(f"[{symbol_raw}] Đã xóa algo sót {side_name}: algoId={algo_id}")
                                        o_items.append(f"{order_type} algo #{algo_id} ({algo.get('algoStatus', '')})")

                            line_o = (
                                f"<b>Lệnh sót (L):</b> đã hủy {deleted_count} "
                                f"({side_name} sót — open:{len(open_to_cancel)}, algo:{len(algo_to_cancel)})"
                            )
                            if o_items:
                                line_o += "\n    ▸ " + "\n    ▸ ".join(o_items[:10])
                                if len(o_items) > 10:
                                    line_o += f"\n    ▸ … (+{len(o_items) - 10} nữa)"
                            else:
                                line_o += "\n    <i>(Không còn lệnh 2–3 sót trên sàn)</i>"
                            row_report['details'].append(line_o)

                # === [TASK 2] XÓA TẤT CẢ LỆNH NGƯỢC (vị thế ĐÓNG) ===
                if delete_all_closed:
                    print(f"   🗑️  [M] Xóa TẤT CẢ lệnh ngược còn treo (vị thế ĐÓNG)...", flush=True)
                    logger.info(f"[{symbol_raw}] Bắt đầu xóa tất cả lệnh ngược (D={col_d_status})")

                    deleted_count = 0
                    w_items = []

                    # 1) Xóa TẤT CẢ open orders (bất kể reduceOnly, side, type)
                    open_orders = get_open_orders(symbol_ccxt)
                    logger.info(f"[{symbol_raw}] W: Tìm thấy {len(open_orders)} open orders để xóa")
                    for order in open_orders:
                        order_id = order.get('id')
                        order_type_str = str(order.get('type', 'N/A')).upper()
                        reduce_only = order.get('reduceOnly', False)
                        if order_id:
                            if cancel_open_order(symbol_ccxt, order_id):
                                deleted_count += 1
                                total_delete_closed += 1
                                logger.info(f"[{symbol_raw}] W: Đã xóa open order id={order_id}, type={order_type_str}, reduceOnly={reduce_only}")
                                w_items.append(f"open #{order_id} ({order_type_str}{', reduceOnly' if reduce_only else ''})")

                    # 2) Xóa TẤT CẢ algo orders (SL + TP + ENTRY + UNKNOWN, NEW/TRIGGERED)
                    removable_algo = get_removable_algo_orders(symbol_ccxt)
                    classified = classify_algo_orders(removable_algo)
                    all_algo = classified['SL'] + classified['TP'] + classified['UNKNOWN'] + classified['ENTRY']
                    logger.info(f"[{symbol_raw}] W: Tìm thấy {len(all_algo)} algo orders (tất cả loại)")
                    for algo in all_algo:
                        algo_id = algo.get('algoId')
                        order_type = get_order_type_from_algo(algo)
                        if algo_id:
                            if cancel_algo_order(symbol_ccxt, algo_id, order_type):
                                deleted_count += 1
                                total_delete_closed += 1
                                w_items.append(f"{order_type} algo #{algo_id} ({algo.get('algoStatus', '')})")

                    print(f"   ✅ [M] Đã xóa {deleted_count} lệnh ngược cho {symbol_raw} (D={col_d_status})", flush=True)
                    logger.info(f"[{symbol_raw}] M: Đã xóa tổng {deleted_count} lệnh ngược")
                    line_w = (
                        f"<b>Xóa tất cả (M):</b> đã hủy {deleted_count} lệnh (D={col_d_status}) "
                        f"(open:{len(open_orders)}, algo:{len(all_algo)})"
                    )
                    if w_items:
                        line_w += "\n    ▸ " + "\n    ▸ ".join(w_items[:10])
                        if len(w_items) > 10:
                            line_w += f"\n    ▸ … (+{len(w_items) - 10} nữa)"
                    else:
                        line_w += "\n    <i>(Không còn lệnh nào trên sàn)</i>"
                    row_report['details'].append(line_w)

                symbol_reports.append(row_report)

            except Exception as e:
                logger.error(f"Lỗi xử lý dòng {row_idx}: {e}", exc_info=True)
                print(f"   ❌ Lỗi xử lý dòng {row_idx}: {e}", flush=True)
                continue

        if symbols_to_clear_ticks:
            print(f"\n📤 Cập nhật sheet - Xóa các tick đã chọn cho {len(symbols_to_clear_ticks)} symbols (1 API call)...", flush=True)
            logger.info(f"Xóa tick đúng theo cột user đã chọn cho {len(symbols_to_clear_ticks)} symbols")

            ranges_to_clear = []
            for row_num, selected_cols in symbols_to_clear_ticks:
                for col in selected_cols:
                    ranges_to_clear.append(f"{col}{row_num}")

            try:
                gg_sheet_factory.batch_clear_values(
                    gg_sheet_factory.tab_cho_va_khop,
                    ranges_to_clear
                )
                print(f"   ✅ Đã xóa đúng tick đã chọn cho {len(symbols_to_clear_ticks)} rows ({len(ranges_to_clear)} ô) trong 1 API call", flush=True)
            except Exception as e:
                logger.error(f"Lỗi khi batch_clear tick đã chọn: {e}")
                # Fallback: ghi từng ô, có delay để tránh 429
                logger.warning("Fallback: Ghi từng ô với delay 1s")
                for row_num, selected_cols in symbols_to_clear_ticks:
                    for col in selected_cols:
                        try:
                            gg_sheet_factory.update_single_value(
                                gg_sheet_factory.tab_cho_va_khop,
                                f"{col}{row_num}",
                                ""
                            )
                            time.sleep(1)  # Tránh 429 khi fallback
                        except Exception as e2:
                            logger.error(f"Lỗi fallback update {col}{row_num}: {e2}")

        # Sau khi xóa xong: cập nhật lại G/H/I theo trạng thái thực tế trên Binance
        if rows_need_refresh_ghi:
            print(f"\n🔄 Đồng bộ lại cột G/H/I cho {len(rows_need_refresh_ghi)} dòng...", flush=True)
            for row_num, symbol_ccxt in rows_need_refresh_ghi.items():
                ghi = build_ghi_status_from_binance(symbol_ccxt)
                if ghi is None:
                    continue
                g_val, h_val, i_val = ghi
                try:
                    gg_sheet_factory.update_single_value(gg_sheet_factory.tab_cho_va_khop, f"G{row_num}", g_val)
                    gg_sheet_factory.update_single_value(gg_sheet_factory.tab_cho_va_khop, f"H{row_num}", h_val)
                    gg_sheet_factory.update_single_value(gg_sheet_factory.tab_cho_va_khop, f"I{row_num}", i_val)
                    logger.info(f"[SYNC GHI] row={row_num} {symbol_ccxt}: G={g_val}, H={h_val}, I={i_val}")
                except Exception as e:
                    logger.error(f"Lỗi cập nhật G/H/I row {row_num} ({symbol_ccxt}): {e}", exc_info=True)

        # === GỬI THÔNG BÁO TELEGRAM ===
        if symbols_processed > 0:
            total_deleted = total_delete_1 + total_delete_23 + total_delete_23_remain + total_delete_closed
            detail_blocks = []
            for rep in symbol_reports:
                ticks_line = " · ".join(rep.get("ticks", [])) or "—"
                sym_disp = rep.get("symbol", "?")
                ccxt_sym = rep.get("ccxt", "")
                row_n = rep.get("row", "?")
                d_status = rep.get("d_status", "")
                d_tag = f" <code>[D={d_status}]</code>" if d_status else ""
                block = (
                    f"<b>• {sym_disp}</b>"
                    + (f" <code>({ccxt_sym})</code>" if ccxt_sym and ccxt_sym != sym_disp else "")
                    + d_tag
                    + f" — sheet <b>hàng {row_n}</b>\n"
                    f"  <i>Tick:</i> {ticks_line}"
                )
                for dline in rep.get("details", []):
                    block += f"\n{dline}"
                detail_blocks.append(block)

            chi_tiet = "\n\n".join(detail_blocks) if detail_blocks else "<i>(Không có chi tiết)</i>"

            msg = f"""✅ <b>XÓA LỆNH CÓ CHỌN LỌC</b>

<b>Tổng quan</b>
• Đã xử lý: <b>{symbols_processed}</b> dòng (mã)
• Lệnh 1 entry (J): <b>{total_delete_1}</b>
• Cặp 2+3 SL+TP (K): <b>{total_delete_23}</b>
• Lệnh đơn sót (L): <b>{total_delete_23_remain}</b>
• Xóa tất cả ĐÓNG (M): <b>{total_delete_closed}</b>
• <b>Tổng lệnh đã hủy:</b> {total_deleted}
• Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Chi tiết theo mã</b>
{chi_tiet}"""

            logger.info(
                f"[SUMMARY] symbols={symbols_processed}, J={total_delete_1}, "
                f"K={total_delete_23}, L={total_delete_23_remain}, M={total_delete_closed}"
            )

            telegram_factory.send_tele(msg, cst.chat_id, True, True)
            print(f"\n📤 Đã gửi thông báo Telegram", flush=True)
        else:
            print(f"\nℹ️  Không có symbol nào được tick xóa", flush=True)

        # Tổng kết
        print(f"\n{'='*80}", flush=True)
        print(f"✅ Hoàn thành! Đã xử lý {symbols_processed} symbols", flush=True)
        print(f"   J — Xóa lệnh 1 (entry):       {total_delete_1}", flush=True)
        print(f"   K — Xóa cặp 2-3 (SL+TP):      {total_delete_23}", flush=True)
        print(f"   L — Xóa lệnh đơn sót:         {total_delete_23_remain}", flush=True)
        print(f"   M — Xóa tất cả (ĐÓNG):        {total_delete_closed}", flush=True)
        print(f"{'='*80}\n", flush=True)
        logger.info(f"Hoàn thành cancel có chọn lọc - {symbols_processed} symbols")

    except Exception as e:
        print(f"❌ Lỗi trong process_cancellation: {e}", flush=True)
        logger.error(f"Lỗi trong process_cancellation: {e}", exc_info=True)


# Main loop
print(f"🚀 Bot xóa lệnh có chọn lọc khởi động - Chạy mỗi {cst.cancel_orders_minutes} phút", flush=True)
logger.info(f"Khởi động cancel selective bot - chạy mỗi {cst.cancel_orders_minutes} phút")

# Chạy ngay lần đầu
process_cancellation()

# Sau đó chạy theo interval
while True:
    try:
        time.sleep(cst.cancel_orders_minutes * 60)  # Chuyển phút thành giây
        process_cancellation()
    except KeyboardInterrupt:
        print("\n⚠️  Nhận Ctrl+C - Dừng bot...", flush=True)
        logger.info("Bot dừng bởi user (Ctrl+C)")
        break
    except Exception as e:
        print(f"❌ Lỗi trong vòng lặp: {e}", flush=True)
        logger.error(f"Lỗi trong vòng lặp: {e}", exc_info=True)
        time.sleep(60)  # Chờ 1 phút trước khi thử lại

print("👋 Bot đã dừng", flush=True)
logger.info("Bot đã dừng")
