import logging
import os
import platform
import time
from datetime import datetime
from pathlib import Path

import ccxt

import cst
import gg_sheet_factory

file_name = os.path.basename(os.path.abspath(__file__))

# Set title theo OS (Windows/macOS/Linux)
if platform.system() == "Windows":
    os.system(f"title {file_name} - {cst.key_name}")
else:
    print(f"\033]0;{file_name} - {cst.key_name}\007", end="", flush=True)

# Tạo thư mục logs/ nếu chưa có
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Tạo tên file log với timestamp: hd_update_price_dd_mm_yyyy_H_M_S.txt
log_timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
log_filename = logs_dir / f"hd_update_price_{log_timestamp}.txt"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False

_log_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(_log_formatter)
console_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler(log_filename, encoding="utf-8")
file_handler.setFormatter(_log_formatter)
file_handler.setLevel(logging.INFO)

logger.handlers.clear()
logger.addHandler(console_handler)
logger.addHandler(file_handler)

exchange_id = "binance"
exchange_class = getattr(ccxt, exchange_id)
# Chỉ lấy giá public (fetch_tickers) — không cần apiKey/secret.
# Nếu truyền apiKey, CCXT gọi /sapi/v1/capital/config/getall khi load_markets()
# và sẽ lỗi -2008 khi key trong config.ini sai/hết hạn.
exchange = exchange_class(
    {
        "enableRateLimit": True,
        "options": {
            "defaultType": "future",
            "fetchCurrencies": False,
        },
    }
)
exchange.setSandboxMode(False)


def normalize_symbol(sym: str) -> str:
    sym = str(sym).strip().upper()
    if sym.endswith(":USDT"):
        return sym
    if sym.endswith("/USDT"):
        return f"{sym}:USDT"
    if "/" not in sym and sym.endswith("USDT"):
        return f"{sym[:-4]}/USDT:USDT"
    if "/" not in sym:
        return f"{sym}/USDT:USDT"
    return sym


def is_title_row(raw_value: str) -> bool:
    return "trong 24h" in str(raw_value).lower()


def fetch_tickers_with_retry(max_retries: int = 3, retry_delay: int = 5):
    for attempt in range(1, max_retries + 1):
        try:
            return exchange.fetch_tickers()
        except Exception as e:
            if attempt < max_retries:
                logger.warning(
                    f"fetch_tickers lỗi lần {attempt}/{max_retries}: {e}. "
                    f"Đợi {retry_delay}s rồi thử lại."
                )
                time.sleep(retry_delay)
            else:
                logger.error(f"fetch_tickers lỗi sau {max_retries} lần thử: {e}", exc_info=True)
                raise
    return None


def do_it():
    start_time = time.time()
    logger.info("=" * 72)
    logger.info(f"BẮT ĐẦU UPDATE PRICE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tickers = fetch_tickers_with_retry()
    if not tickers:
        logger.warning("Không thể lấy dữ liệu tickers, bỏ qua lần chạy này.")
        return
    logger.info(f"Đã lấy tickers: {len(tickers)} symbols")

    sheet_rows = gg_sheet_factory.get_100_ma("A3:A500")
    logger.info(f"Đã đọc danh sách mã từ sheet A3:A500: {len(sheet_rows)} dòng")

    output_rows = []
    stats = {"ok": 0, "blank": 0, "title": 0, "missing": 0, "invalid": 0}
    missing_symbols = []

    for row in sheet_rows:
        raw_value = ""
        try:
            if row and len(row) > 0 and row[0] is not None:
                raw_value = str(row[0]).strip()

            if not raw_value:
                output_rows.append([])
                stats["blank"] += 1
                continue

            if is_title_row(raw_value):
                output_rows.append([])
                stats["title"] += 1
                continue

            symbol = normalize_symbol(raw_value)
            ticker_data = tickers.get(symbol)
            if not ticker_data:
                output_rows.append([])
                stats["missing"] += 1
                if len(missing_symbols) < 10:
                    missing_symbols.append(symbol)
                continue

            last_price = ticker_data.get("last")
            if last_price is None:
                output_rows.append([])
                stats["invalid"] += 1
                continue

            output_rows.append([last_price])
            stats["ok"] += 1
        except Exception as e:
            output_rows.append([])
            stats["invalid"] += 1
            logger.error(f"Lỗi xử lý symbol '{raw_value}': {e}", exc_info=True)

    logger.info(
        "Tổng kết parse mã: "
        f"ok={stats['ok']}, blank={stats['blank']}, title={stats['title']}, "
        f"missing={stats['missing']}, invalid={stats['invalid']}"
    )
    if missing_symbols:
        logger.warning(f"Ví dụ mã không có trong tickers: {missing_symbols}")

    logger.info(f"Đang update {len(output_rows)} dòng vào cột Y...")
    gg_sheet_factory.update_multi(gg_sheet_factory.tab_list_all_ma, 1, output_rows, "Y")

    execution_time = time.time() - start_time
    logger.info(f"HOÀN TẤT UPDATE PRICE - thời gian: {execution_time:.2f}s")
    logger.info("=" * 72)


print("\n" + "=" * 72, flush=True)
print("HD_UPDATE_PRICE - BOT CẬP NHẬT CỘT GIÁ Y", flush=True)
print(f"Log file: {log_filename}", flush=True)
print(f"Delay: {cst.delay_update_price}s", flush=True)
print("=" * 72 + "\n", flush=True)

logger.info("Khởi động hd_update_price")
logger.info(f"Log file: {log_filename}")
logger.info(f"Delay giữa các lần chạy: {cst.delay_update_price} giây")

while True:
    try:
        do_it()
    except Exception as e:
        logger.error(f"Tổng lỗi vòng lặp: {e}", exc_info=True)

    logger.info(f"Chờ {cst.delay_update_price} giây trước lần cập nhật tiếp theo...")
    time.sleep(cst.delay_update_price)
