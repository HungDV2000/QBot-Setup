"""
Bot xóa lệnh có chọn lọc trên Binance
- Đọc sheet "Chờ và khớp"
- Kiểm tra cột M, N, O:
  - M = Tick → Xóa lệnh 1 (entry order)
  - N = Tick → Xóa cặp lệnh 2-3 (SL + TP)
  - O = Tick → Xóa lệnh đơn 2-3 sót lại
- Xóa orders tương ứng và cập nhật lại sheet
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
        algo_type = algo.get('algoType', '').upper()
        reduce_only = algo.get('reduceOnly', False)
        callback_rate = algo.get('callbackRate', algo.get('priceRate', 0))

        # Thử lấy từ info chi tiết hơn
        info = algo.get('info', {})
        if info:
            reduce_only = info.get('reduceOnly', reduce_only)
            callback_rate = float(info.get('callbackRate', callback_rate) or 0)

        logger.debug(f"[ORDER TYPE CHECK] algoType={algo_type}, reduceOnly={reduce_only}, callbackRate={callback_rate}")

        # TP (Take Profit): Trailing Stop - reduceOnly=true, có callbackRate
        if reduce_only and callback_rate > 0:
            return 'TP'

        # SL (Stop Loss): Stop Market - reduceOnly=true, không có callbackRate
        if reduce_only and callback_rate == 0:
            return 'SL'

        # Entry Order (không phải reduceOnly)
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


def process_cancellation():
    """
    Hàm chính: Đọc sheet, kiểm tra M/N/O, xóa lệnh tương ứng
    """
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*80}", flush=True)
        print(f"[{current_time}] Bắt đầu xóa lệnh có chọn lọc...", flush=True)
        print(f"{'='*80}\n", flush=True)
        logger.info(f"[{current_time}] Bắt đầu cancel orders có chọn lọc")

        # [TASK 1+2] Đọc sheet "Chờ và khớp" layout 23 cột (A-W)
        #   Cột A: Symbol
        #   Cột D: Trạng thái (Y/N/ĐÓNG)
        #   Cột T (idx 19): Tick xóa lệnh 1 entry (cũ = M)
        #   Cột U (idx 20): Tick xóa cặp SL+TP (cũ = N)
        #   Cột V (idx 21): Tick xóa lệnh sót (cũ = O)
        #   Cột W (idx 22): Tick xóa tất cả lệnh ngược (vị thế ĐÓNG) — MỚI
        sheet_data = gg_sheet_factory.get_cho_va_khop("A3:W100")

        if not sheet_data:
            print("⚠️  Không có dữ liệu từ sheet", flush=True)
            logger.warning("Không có dữ liệu từ sheet 'Chờ và khớp'")
            return

        # Danh sách rows cần clear tick (T/U/V/W)
        symbols_to_clear_ticks = []

        # Đếm tổng
        total_delete_1 = 0
        total_delete_23 = 0
        total_delete_23_remain = 0
        total_delete_closed = 0   # [TASK 2] Xóa tất cả lệnh ngược cho vị thế ĐÓNG
        symbols_processed = 0
        symbol_reports = []

        for row_idx, row in enumerate(sheet_data, start=3):
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

                # [TASK 1+2] Layout 23 cột: tick dịch sang T/U/V, thêm W
                #   Cột T (idx 19) = xóa lệnh 1 (entry)          [cũ: M idx 12]
                #   Cột U (idx 20) = xóa cặp 2-3 (SL+TP)         [cũ: N idx 13]
                #   Cột V (idx 21) = xóa lệnh 2-3 sót            [cũ: O idx 14]
                #   Cột W (idx 22) = xóa TẤT CẢ lệnh ngược (ĐÓNG) [MỚI]
                col_t = row[19] if len(row) > 19 else None
                delete_lenh_1 = has_tick(col_t)

                col_u = row[20] if len(row) > 20 else None
                delete_cap_23 = has_tick(col_u)

                col_v = row[21] if len(row) > 21 else None
                delete_don_23 = has_tick(col_v)

                col_w = row[22] if len(row) > 22 else None
                delete_all_closed = has_tick(col_w)

                # [TASK 2] Đọc trạng thái D để biết có phải vị thế ĐÓNG không
                col_d_status = str(row[3]).strip().upper() if len(row) > 3 and row[3] else ""
                is_closed_position = col_d_status == "ĐÓNG"

                logger.info(
                    f"[{row_idx}] {symbol_raw}: D={col_d_status} | "
                    f"T(entry)={delete_lenh_1}, U(cặp)={delete_cap_23}, V(sót)={delete_don_23}, W(đóng)={delete_all_closed}"
                )

                # Nếu không có tick nào, bỏ qua
                if not (delete_lenh_1 or delete_cap_23 or delete_don_23 or delete_all_closed):
                    print(f"   ⏭️  Không có tick xóa, bỏ qua", flush=True)
                    continue

                # [TASK 2] Cảnh báo khi tick W mà D ≠ ĐÓNG (user có thể xóa nhầm vị thế đang mở)
                if delete_all_closed and not is_closed_position:
                    print(f"   ⚠️  [W] Cột D='{col_d_status}' không phải ĐÓNG — vẫn xử lý theo yêu cầu user", flush=True)
                    logger.warning(f"[{row_idx}] {symbol_raw}: Tick W nhưng D={col_d_status} (expected ĐÓNG)")

                symbols_processed += 1
                symbols_to_clear_ticks.append(row_idx)

                row_report = {
                    'symbol': symbol_raw,
                    'row': row_idx,
                    'ccxt': symbol_ccxt,
                    'd_status': col_d_status,
                    'ticks': [],
                    'details': [],
                }
                if delete_lenh_1:
                    row_report['ticks'].append('T — lệnh 1 (entry)')
                if delete_cap_23:
                    row_report['ticks'].append('U — cặp 2+3 (SL+TP)')
                if delete_don_23:
                    row_report['ticks'].append('V — lệnh 2–3 sót')
                if delete_all_closed:
                    row_report['ticks'].append('W — xóa TẤT CẢ (ĐÓNG)')

                # === XÓA LỆNH 1 (Entry Order) ===
                if delete_lenh_1:
                    print(f"   🗑️  [M] Xóa lệnh 1 (entry order)...", flush=True)
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
                    line_m = f"<b>Lệnh 1 (T):</b> đã hủy {deleted_count} lệnh"
                    if m_items:
                        line_m += "\n    ▸ " + "\n    ▸ ".join(m_items[:10])
                        if len(m_items) > 10:
                            line_m += f"\n    ▸ … (+{len(m_items) - 10} nữa)"
                    else:
                        line_m += "\n    <i>(Không còn lệnh entry trên sàn)</i>"
                    row_report['details'].append(line_m)

                # === XÓA CẶP LỆNH 2-3 (SL + TP) ===
                if delete_cap_23:
                    print(f"   🗑️  [N] Xóa cặp lệnh 2-3 (SL + TP)...", flush=True)
                    logger.info(f"[{symbol_raw}] Bắt đầu xóa cặp lệnh 2-3 (SL + TP)")

                    deleted_count = 0
                    deleted_sl = 0
                    deleted_tp = 0
                    deleted_unknown = 0
                    n_items = []

                    # 1️⃣ XÓA SL/TP DẠNG OPEN ORDERS THÔNG THƯỜNG (STOP_MARKET, STOP_LIMIT qua CCXT)
                    open_orders = get_open_orders(symbol_ccxt)
                    sl_tp_open_orders = [o for o in open_orders if o.get('reduceOnly', False)]
                    logger.info(f"[{symbol_raw}] Tìm thấy {len(sl_tp_open_orders)} SL/TP open orders (reduceOnly=True)")

                    for order in sl_tp_open_orders:
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

                    for algo in unknown_orders:
                        algo_id = algo.get('algoId')
                        if algo_id:
                            if cancel_algo_order(symbol_ccxt, algo_id, 'UNKNOWN'):
                                deleted_count += 1
                                deleted_unknown += 1
                                total_delete_23 += 1
                                n_items.append(f"algo? #{algo_id} type={algo.get('algoType', '')} ({algo.get('algoStatus', '')})")

                    print(f"   ✅ Đã xóa {deleted_count} SL/TP orders (open:{len(sl_tp_open_orders)}, algo SL:{deleted_sl}, TP:{deleted_tp}, UNKNOWN:{deleted_unknown}) cho {symbol_raw}", flush=True)
                    logger.info(f"[{symbol_raw}] Đã xóa {deleted_count} SL/TP orders")
                    line_n = (
                        f"<b>Cặp 2+3 (U):</b> đã hủy {deleted_count} "
                        f"(open reduceOnly: {len(sl_tp_open_orders)} tìm thấy; algo SL:{deleted_sl}, TP:{deleted_tp}, khác:{deleted_unknown})"
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
                    print(f"   🗑️  [O] Xóa lệnh đơn 2-3 sót lại...", flush=True)
                    logger.info(f"[{symbol_raw}] Bắt đầu xóa lệnh đơn 2-3 sót lại")

                    deleted_count = 0
                    deleted_sl = 0
                    deleted_tp = 0
                    deleted_unknown = 0
                    o_items = []

                    # 1️⃣ XÓA SL/TP DẠNG OPEN ORDERS SÓT LẠI (reduceOnly=True)
                    open_orders = get_open_orders(symbol_ccxt)
                    sl_tp_open_orders = [o for o in open_orders if o.get('reduceOnly', False)]
                    logger.info(f"[{symbol_raw}] Tìm thấy {len(sl_tp_open_orders)} SL/TP open orders sót lại (reduceOnly=True)")

                    for order in sl_tp_open_orders:
                        order_id = order.get('id')
                        order_type_str = order.get('type', 'N/A').upper()
                        if order_id:
                            if cancel_open_order(symbol_ccxt, order_id):
                                deleted_count += 1
                                total_delete_23_remain += 1
                                logger.info(f"[{symbol_raw}] Đã xóa SL/TP open order sót: id={order_id}, type={order_type_str}")
                                o_items.append(f"open reduceOnly #{order_id} ({order_type_str})")

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

                    for algo in sl_orders + tp_orders + unknown_orders:
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
                                o_items.append(f"{order_type} algo #{algo_id} ({algo.get('algoStatus', '')})")

                    print(f"   ✅ Đã xóa {deleted_count} lệnh đơn sót lại (open:{len(sl_tp_open_orders)}, algo SL:{deleted_sl}, TP:{deleted_tp}, UNKNOWN:{deleted_unknown}) cho {symbol_raw}", flush=True)
                    logger.info(f"[{symbol_raw}] Đã xóa {deleted_count} lệnh đơn sót lại")
                    line_o = (
                        f"<b>Lệnh sót (V):</b> đã hủy {deleted_count} "
                        f"(algo SL:{deleted_sl}, TP:{deleted_tp}, khác:{deleted_unknown})"
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
                    print(f"   🗑️  [W] Xóa TẤT CẢ lệnh ngược còn treo (vị thế ĐÓNG)...", flush=True)
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

                    print(f"   ✅ [W] Đã xóa {deleted_count} lệnh ngược cho {symbol_raw} (D={col_d_status})", flush=True)
                    logger.info(f"[{symbol_raw}] W: Đã xóa tổng {deleted_count} lệnh ngược")
                    line_w = (
                        f"<b>Xóa tất cả (W):</b> đã hủy {deleted_count} lệnh (D={col_d_status}) "
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

        # === [TASK 1+2] CẬP NHẬT SHEET: Xóa tick ở cột T, U, V, W sau khi đã xử lý ===
        if symbols_to_clear_ticks:
            print(f"\n📤 Cập nhật sheet - Xóa tick T, U, V, W cho {len(symbols_to_clear_ticks)} symbols (1 API call)...", flush=True)
            logger.info(f"Xóa tick T/U/V/W cho {len(symbols_to_clear_ticks)} symbols")

            # Gộp tất cả ranges vào 1 batchClear duy nhất → tránh 429 rate limit
            ranges_to_clear = []
            for row_num in symbols_to_clear_ticks:
                ranges_to_clear.extend([f"T{row_num}", f"U{row_num}", f"V{row_num}", f"W{row_num}"])

            try:
                gg_sheet_factory.batch_clear_values(
                    gg_sheet_factory.tab_cho_va_khop,
                    ranges_to_clear
                )
                print(f"   ✅ Đã xóa tick T/U/V/W cho {len(symbols_to_clear_ticks)} rows ({len(ranges_to_clear)} ô) trong 1 API call", flush=True)
            except Exception as e:
                logger.error(f"Lỗi khi batch_clear T/U/V/W: {e}")
                # Fallback: ghi từng ô, có delay để tránh 429
                logger.warning("Fallback: Ghi từng ô với delay 1s")
                for row_num in symbols_to_clear_ticks:
                    for col in ["T", "U", "V", "W"]:
                        try:
                            gg_sheet_factory.update_single_value(
                                gg_sheet_factory.tab_cho_va_khop,
                                f"{col}{row_num}",
                                ""
                            )
                            time.sleep(1)  # Tránh 429 khi fallback
                        except Exception as e2:
                            logger.error(f"Lỗi fallback update {col}{row_num}: {e2}")

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
• Lệnh 1 entry (T): <b>{total_delete_1}</b>
• Cặp 2+3 SL+TP (U): <b>{total_delete_23}</b>
• Lệnh đơn sót (V): <b>{total_delete_23_remain}</b>
• Xóa tất cả ĐÓNG (W): <b>{total_delete_closed}</b>
• <b>Tổng lệnh đã hủy:</b> {total_deleted}
• Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Chi tiết theo mã</b>
{chi_tiet}"""

            logger.info(
                f"[SUMMARY] symbols={symbols_processed}, T={total_delete_1}, "
                f"U={total_delete_23}, V={total_delete_23_remain}, W={total_delete_closed}"
            )

            telegram_factory.send_tele(msg, cst.chat_id, True, True)
            print(f"\n📤 Đã gửi thông báo Telegram", flush=True)
        else:
            print(f"\nℹ️  Không có symbol nào được tick xóa", flush=True)

        # Tổng kết
        print(f"\n{'='*80}", flush=True)
        print(f"✅ Hoàn thành! Đã xử lý {symbols_processed} symbols", flush=True)
        print(f"   T — Xóa lệnh 1 (entry):       {total_delete_1}", flush=True)
        print(f"   U — Xóa cặp 2-3 (SL+TP):      {total_delete_23}", flush=True)
        print(f"   V — Xóa lệnh đơn sót:         {total_delete_23_remain}", flush=True)
        print(f"   W — Xóa tất cả (ĐÓNG):        {total_delete_closed}", flush=True)
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
