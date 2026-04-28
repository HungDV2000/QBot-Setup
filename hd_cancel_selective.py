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
    except Exception as e:
        logger.error(f"Lỗi khi gọi Binance API trực tiếp ({method} {endpoint}): {e}")
        return None


def get_all_algo_orders_for_symbol(symbol):
    """
    Lấy TẤT CẢ algo orders cho một symbol (bao gồm cả NEW, TRIGGERED, FINISHED, CANCELED)
    """
    try:
        symbol_clean = symbol.replace('/', '').replace(':USDT', '')
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
        logger.error(f"Lỗi khi lấy algo orders cho {symbol}: {e}", exc_info=True)
        return []


def get_active_algo_orders(symbol):
    """
    Lấy algo orders đang active (NEW) cho một symbol
    """
    all_orders = get_all_algo_orders_for_symbol(symbol)
    return [o for o in all_orders if o.get('algoStatus', '').upper() == 'NEW']


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

        # Đọc dữ liệu từ sheet "Chờ và khớp" (cột A-O, hàng 3-100)
        # Cột A: Symbol, M: Xóa lệnh 1, N: Xóa cặp 2-3, O: Xóa lệnh đơn
        sheet_data = gg_sheet_factory.get_cho_va_khop("A3:O100")

        if not sheet_data:
            print("⚠️  Không có dữ liệu từ sheet", flush=True)
            logger.warning("Không có dữ liệu từ sheet 'Chờ và khớp'")
            return

        # Danh sách symbols cần update sau khi xóa
        symbols_to_clear_mno = []

        # Đếm tổng
        total_delete_1 = 0
        total_delete_23 = 0
        total_delete_23_remain = 0
        symbols_processed = 0

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

                # Kiểm tra cột M (index 12) - Xóa lệnh 1 (entry order)
                col_m = row[12] if len(row) > 12 else None
                delete_lenh_1 = has_tick(col_m)

                # Kiểm tra cột N (index 13) - Xóa cặp lệnh 2-3 (SL + TP)
                col_n = row[13] if len(row) > 13 else None
                delete_cap_23 = has_tick(col_n)

                # Kiểm tra cột O (index 14) - Xóa lệnh đơn 2-3 sót lại
                col_o = row[14] if len(row) > 14 else None
                delete_don_23 = has_tick(col_o)

                logger.info(f"[{row_idx}] {symbol_raw}: M(delete_1)={delete_lenh_1}, N(delete_cap_23)={delete_cap_23}, O(delete_don_23)={delete_don_23}")

                # Nếu không có tick nào, bỏ qua
                if not (delete_lenh_1 or delete_cap_23 or delete_don_23):
                    print(f"   ⏭️  Không có tick xóa, bỏ qua", flush=True)
                    continue

                symbols_processed += 1
                has_any_deletion = False

                # === XÓA LỆNH 1 (Entry Order) ===
                if delete_lenh_1:
                    print(f"   🗑️  [M] Xóa lệnh 1 (entry order)...", flush=True)
                    logger.info(f"[{symbol_raw}] Bắt đầu xóa lệnh 1 (entry order)")

                    # Entry order = open orders thông thường (không phải algo orders)
                    open_orders = get_open_orders(symbol_ccxt)
                    deleted_count = 0

                    for order in open_orders:
                        order_id = order.get('id')
                        order_type = order.get('type', 'N/A')
                        if order_id:
                            if cancel_open_order(symbol_ccxt, order_id):
                                deleted_count += 1
                                total_delete_1 += 1
                                has_any_deletion = True

                    print(f"   ✅ Đã xóa {deleted_count} lệnh entry cho {symbol_raw}", flush=True)
                    logger.info(f"[{symbol_raw}] Đã xóa {deleted_count} lệnh entry")

                # === XÓA CẶP LỆNH 2-3 (SL + TP - Algo Orders) ===
                if delete_cap_23:
                    print(f"   🗑️  [N] Xóa cặp lệnh 2-3 (SL + TP)...", flush=True)
                    logger.info(f"[{symbol_raw}] Bắt đầu xóa cặp lệnh 2-3 (SL + TP)")

                    # SL và TP đều là algo orders
                    active_algo = get_active_algo_orders(symbol_ccxt)
                    deleted_count = 0

                    for algo in active_algo:
                        algo_id = algo.get('algoId')
                        algo_type = algo.get('algoType', 'N/A')
                        algo_status = algo.get('algoStatus', 'N/A')

                        if algo_id:
                            if cancel_algo_order(symbol_ccxt, algo_id, algo_type):
                                deleted_count += 1
                                total_delete_23 += 1
                                has_any_deletion = True

                    print(f"   ✅ Đã xóa {deleted_count} algo orders (SL+TP) cho {symbol_raw}", flush=True)
                    logger.info(f"[{symbol_raw}] Đã xóa {deleted_count} algo orders (SL+TP)")

                # === XÓA LỆNH ĐƠN 2-3 SÓT LẠI ===
                if delete_don_23:
                    print(f"   🗑️  [O] Xóa lệnh đơn 2-3 sót lại...", flush=True)
                    logger.info(f"[{symbol_raw}] Bắt đầu xóa lệnh đơn 2-3 sót lại")

                    # Lệnh đơn 2-3 có thể là algo orders còn lại (không phải cặp SL+TP)
                    # Lấy tất cả algo orders (bao gồm cả đã trigger)
                    all_algo = get_all_algo_orders_for_symbol(symbol_ccxt)

                    # Lọc orders có thể xóa: NEW hoặc TRIGGERED (không phải FINISHED/CANCELED)
                    removable_orders = [
                        o for o in all_algo
                        if o.get('algoStatus', '').upper() in ['NEW', 'TRIGGERED']
                    ]

                    deleted_count = 0
                    for algo in removable_orders:
                        algo_id = algo.get('algoId')
                        algo_type = algo.get('algoType', 'N/A')

                        if algo_id:
                            if cancel_algo_order(symbol_ccxt, algo_id, algo_type):
                                deleted_count += 1
                                total_delete_23_remain += 1
                                has_any_deletion = True

                    print(f"   ✅ Đã xóa {deleted_count} lệnh đơn sót lại cho {symbol_raw}", flush=True)
                    logger.info(f"[{symbol_raw}] Đã xóa {deleted_count} lệnh đơn sót lại")

                # Nếu có xóa gì đó, đánh dấu symbol để clear M,N,O sau
                if has_any_deletion:
                    symbols_to_clear_mno.append(row_idx)

            except Exception as e:
                logger.error(f"Lỗi xử lý dòng {row_idx}: {e}", exc_info=True)
                print(f"   ❌ Lỗi xử lý dòng {row_idx}: {e}", flush=True)
                continue

        # === CẬP NHẬT SHEET: Xóa tick ở cột M, N, O sau khi đã xóa lệnh ===
        if symbols_to_clear_mno:
            print(f"\n📤 Cập nhật sheet - Xóa tick M, N, O cho {len(symbols_to_clear_mno)} symbols...", flush=True)
            logger.info(f"Cập nhật sheet - Xóa tick M, N, O cho {len(symbols_to_clear_mno)} symbols")

            for row_num in symbols_to_clear_mno:
                try:
                    # Xóa giá trị ở cột M (13), N (14), O (15)
                    gg_sheet_factory.update_single_value(
                        gg_sheet_factory.tab_cho_va_khop,
                        f"M{row_num}",
                        ""
                    )
                    gg_sheet_factory.update_single_value(
                        gg_sheet_factory.tab_cho_va_khop,
                        f"N{row_num}",
                        ""
                    )
                    gg_sheet_factory.update_single_value(
                        gg_sheet_factory.tab_cho_va_khop,
                        f"O{row_num}",
                        ""
                    )
                except Exception as e:
                    logger.error(f"Lỗi khi update sheet cho row {row_num}: {e}")

        # === GỬI THÔNG BÁO TELEGRAM ===
        if symbols_processed > 0:
            total_deleted = total_delete_1 + total_delete_23 + total_delete_23_remain
            msg = f"""✅ <b>XÓA LỆNH CÓ CHỌN LỌC</b>

<b>Đã xử lý:</b> {symbols_processed} symbols
<b>Đã xóa lệnh 1 (entry):</b> {total_delete_1}
<b>Đã xóa cặp 2-3 (SL+TP):</b> {total_delete_23}
<b>Đã xóa lệnh đơn sót lại:</b> {total_delete_23_remain}
<b>Tổng cộng:</b> {total_deleted} lệnh
<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            telegram_factory.send_tele(msg, cst.chat_id, True, True)
            print(f"\n📤 Đã gửi thông báo Telegram", flush=True)
        else:
            print(f"\nℹ️  Không có symbol nào được tick xóa", flush=True)

        # Tổng kết
        print(f"\n{'='*80}", flush=True)
        print(f"✅ Hoàn thành! Đã xử lý {symbols_processed} symbols", flush=True)
        print(f"   Xóa lệnh 1: {total_delete_1}", flush=True)
        print(f"   Xóa cặp 2-3: {total_delete_23}", flush=True)
        print(f"   Xóa lệnh đơn sót lại: {total_delete_23_remain}", flush=True)
        print(f"{'='*80}\n", flush=True)
        logger.info(f"Hoàn thành cancel có chọn lọc - Đã xử lý {symbols_processed} symbols")

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
