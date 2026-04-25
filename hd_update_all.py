import gg_sheet_factory
import ccxt 
import time
import datetime
from enum import Enum
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import cst
import time
import logging
import pandas as pd
import ctypes
import utils
import numpy as np
import json
import os
import re
import math
import requests
from data_collector import DataCollector, get_data_collector

file_name = os.path.basename(os.path.abspath(__file__))  
os.system(f"title {file_name} - {cst.key_name}")

# Tạo thư mục logs/ và logs/data/ nếu chưa có
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)
data_logs_dir = logs_dir / 'data'
data_logs_dir.mkdir(exist_ok=True)

# Tạo tên file log với timestamp: hd_update_all_dd_mm_yyyy_H_M_S.txt
log_timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
log_filename = logs_dir / f'hd_update_all_{log_timestamp}.txt'

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

# Thêm file handler cho error.log (giữ lại cho tương thích)
error_log_path = logs_dir / 'error.log'
error_handler = logging.FileHandler(error_log_path, encoding='utf-8')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(error_handler)

is_test_mode = False
ENABLE_DEBUG_DATA = True  # Ghi file logs/data/<SYMBOL>_dd_mm_yyyy.txt — tắt khi không cần debug

# ─────────────────────────────────────────────────────────────────────────────
# DEBUG: Tên cột theo thứ tự A→AK (khớp với header_row trong do_it)
# ─────────────────────────────────────────────────────────────────────────────
_DEBUG_COL_NAMES = [
    "Mã",                              # A
    "% 24h",                           # B
    "Giá trị hiện thời",               # C
    "BB1h trên",                       # D
    "BB1h dưới",                       # E
    "BB4h trên",                       # F
    "BB4h dưới",                       # G
    "BB1 ngày trên",                   # H
    "BB1 ngày dưới",                   # I
    "Biên độ 1h max tăng tuần",        # J
    "Biên độ 1h max giảm tuần",        # K
    "Max 40 ngày",                     # L
    "Min 40 ngày",                     # M
    "Max tăng 4h/60 ngày",             # N
    "Max giảm 4h/60 ngày",             # O
    "Giá Cao Nhất (BB1w trên)",        # P
    "Giá Thấp Nhất (BB1w dưới)",       # Q
    "Biên độ 30d tăng",                # R
    "Biên độ 30d giảm",                # S
    "Volume 24h",                      # T
    "RSI 14",                          # U
    "(trống V)",                       # V
    "Min/Min40 (BB1w dưới / Min40)",   # W
    "% đến BB1h trên",                 # X
    "% đến BB1h dưới",                 # Y
    "Vol 1h",                          # Z
    "Vol 4h",                          # AA
    "Futures (trạng thái)",            # AB — exchangeInfo USDT-M
    "Spot (trạng thái)",               # AC — exchangeInfo spot
    "Biên độ giá ngày lớn nhất (%)",   # AD
    "Ngày biên độ lớn nhất",           # AE
    "BB width 1d (3 ngày trước)",      # AF
    "BB width 1d (hiện tại)",          # AG
    "RSI 14 (4h)",                     # AH
    "Vol 1h (hiện tại)",               # AI
    "Vol 1h MA20",                     # AJ
    "Cảnh báo delist sắp tới",         # AK — API delist-current-month + thông báo Support (CMS)
]


def _col_letter(idx: int) -> str:
    """Chuyển index 0-based → chữ cột (A, B, …, Z, AA, AB, …)."""
    if idx < 26:
        return chr(ord("A") + idx)
    return "A" + chr(ord("A") + idx - 26)


def write_symbol_debug_log(symbol: str, row: list) -> None:
    """
    Ghi file logs/data/<SYMBOL>_dd_mm_yyyy.txt chứa giá trị từng cột.
    Ví dụ: logs/data/BTC_USDT_02_04_2026.txt
    Ghi đè mỗi lần chạy trong ngày (append nếu chạy nhiều lần).
    """
    try:
        # Chuẩn hoá tên file: BTC/USDT:USDT → BTC_USDT
        safe_name = symbol.replace("/", "_").replace(":", "_").replace("USDT_USDT", "USDT").rstrip("_")
        date_str = datetime.now().strftime("%d_%m_%Y")
        filepath = data_logs_dir / f"{safe_name}_{date_str}.txt"

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"{'='*60}",
            f"  {symbol}  —  {now_str}",
            f"{'='*60}",
        ]

        for i, col_name in enumerate(_DEBUG_COL_NAMES):
            letter = _col_letter(i)
            value = row[i] if i < len(row) else "(thiếu)"
            # Format số thực: giữ tối đa 6 chữ số thập phân
            if isinstance(value, float):
                if math.isfinite(value):
                    formatted = f"{value:,.6f}".rstrip("0").rstrip(".")
                else:
                    formatted = str(value)   # nan / inf
            else:
                formatted = str(value) if value != "" else "(trống)"
            lines.append(f"  {letter:<3} | {col_name:<35} : {formatted}")

        lines.append("")  # dòng trống cuối

        # append — nếu chạy nhiều lần trong ngày sẽ có nhiều block
        with open(filepath, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    except Exception as e:
        logger.warning(f"[write_symbol_debug_log] Không ghi được file debug cho {symbol}: {e}")

calculate_high_low_day_total = 40


def set_cmd_title(title):
    ctypes.windll.kernel32.SetConsoleTitleW(title)

class RequestType(Enum):
    GET_PRICE = 1
    GET_BB = 2
    GET_BIEN_DO_MAX = 3
    GET_THOI_GIAN_MAX = 4
    GET_BIEN_DO_THEO_GIO = 5

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
# Tránh treo vĩnh viễn khi Binance/mạng không phản hồi (mặc định ccxt có thể không timeout)
exchange.timeout = 30000

# Một lần fetch 1d đủ cho BB1d + Min/Max 40d + RSI 1d + biên độ 30d + BB width AF-AG
_OHLCV_1D_LIMIT = 450


def _listing_status_cell(market, max_len=200):
    """
    Chuỗi ngắn cho cột sheet: trạng thái niêm yết Binance (từ market['info'] + active).
    Dùng cho AB (Futures) và AC (Spot).
    """
    if not market:
        return ""
    info = market.get("info") or {}
    parts: list[str] = []
    st = info.get("status")
    if st is not None and st != "":
        parts.append(str(st))
    else:
        parts.append("ACTIVE" if market.get("active") else "INACTIVE")
    ctype = info.get("contractType")
    if ctype:
        parts.append(str(ctype))
    for key, label in (("deliveryDate", "delivery"), ("onboardDate", "listed")):
        raw = info.get(key)
        if raw is None or str(raw) in ("0", "", "None"):
            continue
        try:
            ms = int(raw)
            if ms <= 0:
                continue
            if ms < 1_000_000_000_000:  # giây vs ms
                sec = ms
            else:
                sec = ms // 1000
            parts.append(f"{label} {datetime.fromtimestamp(sec).strftime('%Y-%m-%d')}")
        except (TypeError, ValueError, OSError):
            parts.append(f"{label} {raw}")
    s = " | ".join(parts)
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s


# Binance Support — Delisting (catalogId=161), API dùng bởi trang announcement
_BINANCE_CMS_LIST = "https://www.binance.com/bapi/apex/v1/public/apex/cms/article/list/query"
_BINANCE_DELIST_CATALOG_ID = 161
_CMS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "lang": "en",
    "Accept-Language": "en",
    "clienttype": "web",
    "Referer": "https://www.binance.com/en/support/announcement/list/161",
}


def _venue_from_delist_title(title: str) -> str:
    t = title.lower()
    if "binance futures" in t or "futures will delist" in t or "usdt-m" in t or "usdⓈ-m" in t:
        return "FUT"
    if "margin" in t and "futures" not in t and "futures will" not in t:
        return "MG"
    return "SPOT"


def _extract_dates_from_text(text: str) -> list:
    return re.findall(r"\d{4}-\d{2}-\d{2}", text or "")


def _pick_delist_date_for_article(dates, today_d):
    """
    Ưu tiên: ngày trong tiêu đề >= hôm nay (mốc sắp tới gần nhất).
    Fallback: nếu không còn mốc tương lai, lấy ngày lớn nhất trong tiêu đề
    nếu vẫn trong vòng 120 ngày gần đây (thông báo / delist vừa diễn ra — tránh cột AK trống hoàn toàn).
    """
    if not dates:
        return None
    parsed = []
    for d in dates:
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            parsed.append((dt, d))
        except ValueError:
            continue
    if not parsed:
        return None
    future = [(dt, s) for dt, s in parsed if dt >= today_d]
    if future:
        future.sort(key=lambda x: x[0])
        return future[0][1]
    # Không còn mốc tương lai: dùng ngày gần đây nhất (max) nếu trong 120 ngày
    parsed.sort(key=lambda x: x[0])
    last_dt, last_s = parsed[-1]
    if (today_d - last_dt).days <= 120:
        return last_s
    return None


def _symbol_tokens_from_delist_title(title: str) -> set:
    """
    Cố lấy mã base từ tiêu đề thông báo (USDT Perp: XXXUSDT; Spot: A, B, C; …).
    Lưu ý: \\b trước USDT không khớp RVVUSDT (V và U cùng \\w) — dùng lookaround.
    """
    t = (title or "").upper()
    bases: set = set()
    for m in re.finditer(r"(?<![A-Z0-9])([A-Z0-9]{2,32})USDT(?![A-Z0-9])", t):
        b = m.group(1)
        if b in ("USD", "USDC"):
            continue
        bases.add(b)
    for m in re.finditer(r"(?<![A-Z0-9])([A-Z0-9]{2,20})USD(?![A-Z0-9])", t):
        b = m.group(1)
        if b in ("USD", "USDT", "BUSD", "TUSD", "USDC", "USDD"):
            continue
        bases.add(b)
    m = re.search(
        r"(?:BINANCE )?WILL DELIST\s+(.+?)(?:\s+ON\s+\d{4}-\d{2}-\d{2}|\s+ON\s+\(|\(|\Z)",
        t,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        chunk = m.group(1)
        chunk = re.sub(r"\s+", " ", chunk)
        for noise in [
            "MULTIPLE", "CONTRACTS", "PERPETUAL", "MARGIN", "LOAN", "SUPPORT", "REBRAND",
            "AIRDROP", "PLAN", "USDT", "U.S.", "DOLLAR",
        ]:
            chunk = re.sub(rf"\b{noise}\b", " ", chunk, flags=re.I)
        for part in re.split(r"[,;]|\s+AND\s+|\s+FROM\s+", chunk):
            part = re.sub(r"[\(\)\[\]—\-]", " ", part).strip()
            if not part:
                continue
            tok = re.sub(r"[^A-Z0-9]", "", part) if part else ""
            if 2 <= len(tok) <= 20 and tok.isalnum() and not tok.isdigit():
                bases.add(tok)
    noise2 = {
        "BINANCE", "FUTURES", "SPOT", "WILL", "NOTIFY", "NOTICE", "MARGIN", "REMOVAL",
        "TRADING", "USDT", "USDC", "BUSD", "LOAN", "PAIR", "PAIRS", "DELIST", "SUPPORT", "ON",
    }
    bases = {b for b in bases if b not in noise2}
    return bases


def _build_upcoming_delist_by_pair() -> dict:
    """
    Trả về map: 'BASE/USDT' -> chuỗi hiển thị (FUT/SPOT/MG + ngày).
    Chỉ dùng thông tin có trong tiêu đề; bài 'Multiple…' không tách được mã → bỏ qua.
    """
    today_d = datetime.now().date()
    by_pair_venue: dict = {}  # pair -> {FUT: set(dates), SPOT: set(), MG: set()}

    try:
        r = requests.get(
            _BINANCE_CMS_LIST,
            params={
                "type": 1,
                "pageNo": 1,
                "pageSize": 200,
                "catalogId": _BINANCE_DELIST_CATALOG_ID,
            },
            headers=_CMS_HEADERS,
            timeout=45,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") not in (None, "000000", 0, "0"):
            logger.warning(f"binance delist: API code={data.get('code')} msg={data.get('message')}")
            return {}
        arts = (data.get("data") or {}).get("catalogs")
        if not arts:
            logger.warning("binance delist: không có catalogs")
            return {}
        articles = arts[0].get("articles") or []
        logger.info(f"binance delist: đọc được {len(articles)} bài catalog 161")
    except Exception as e:
        logger.warning(f"binance delist: không tải được CMS: {e}")
        return {}

    articles_matched = 0
    for art in articles:
        title = (art.get("title") or "").strip()
        if not title:
            continue
        if re.search(r"Delist|Delisting|REMOVAL|Remove\s+(?:of|Spot|Margin)", title, re.I) is None:
            continue
        if re.search(
            r"multiple|several|various",
            title,
            re.I,
        ) and not re.search(r"(?<![A-Z0-9])([A-Z0-9]{2,32})USDT(?![A-Z0-9])", title, re.I):
            continue
        dates = _extract_dates_from_text(title)
        d_use = _pick_delist_date_for_article(dates, today_d)
        if not d_use:
            continue
        venue = _venue_from_delist_title(title)
        syms = _symbol_tokens_from_delist_title(title)
        if not syms:
            continue
        articles_matched += 1
        for b in syms:
            pkey = f"{b.upper()}/USDT"
            by_pair_venue.setdefault(pkey, {})
            by_pair_venue[pkey].setdefault(venue, set()).add(d_use)

    logger.info(f"binance delist: {articles_matched} bài có mã + ngày hợp lệ → {len(by_pair_venue)} cặp")
    flat: dict = {}
    for pkey, venues in by_pair_venue.items():
        parts: list = []
        for v in ("FUT", "MG", "SPOT"):
            if v not in venues:
                continue
            d_sorted = sorted(venues[v])[:3]
            parts.append(f"{v} {', '.join(d_sorted)}")
        if parts:
            s = " | ".join(parts)
            flat[pkey] = s[: 320] if len(s) > 320 else s
    return flat


def _delist_warn_lookup(dmap, pair):
    """Khớp cặp BASE/USDT với map (không phân biệt hoa thường)."""
    if not dmap or not pair:
        return ""
    if pair in dmap:
        return dmap[pair]
    pu = pair.upper()
    if pu in dmap:
        return dmap[pu]
    for k, v in dmap.items():
        if str(k).upper() == pu:
            return v
    return ""


_DELIST_API_URL = "https://n8n.deepview.win/webhook/delist-current-month"


def _normalize_delist_base_symbol(raw_symbol: str) -> str:
    """
    Chuẩn hoá symbol từ API về BASE:
    - BOBUSDT -> BOB
    - WLDUSD -> WLD
    - DEGEN -> DEGEN
    """
    s = str(raw_symbol or "").strip().upper()
    if not s:
        return ""
    if s.endswith("USDT") and len(s) > 4:
        return s[:-4]
    if s.endswith("USD") and len(s) > 3:
        return s[:-3]
    return s


def _parse_delist_datetime_utc(raw: str):
    """
    Parse định dạng từ API: 'YYYY-MM-DD HH:MM UTC'
    Trả về datetime naive theo UTC (để so sánh tương đối).
    """
    txt = str(raw or "").strip()
    if not txt:
        return None
    for fmt in ("%Y-%m-%d %H:%M UTC", "%Y-%m-%d %H:%M:%S UTC"):
        try:
            return datetime.strptime(txt, fmt)
        except ValueError:
            continue
    return None


def _load_future_delist_by_pair_from_api() -> dict:
    """
    Đọc API delist-current-month của n8n.
    Chỉ giữ mốc delist_datetime trong tương lai.
    Trả về map: 'BASE/USDT' -> cảnh báo có thời gian delist rõ ràng.
    """
    try:
        r = requests.get(_DELIST_API_URL, timeout=30)
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        logger.warning(f"Không tải được delist API: {e}")
        return {}

    if not isinstance(payload, dict):
        logger.warning("Delist API trả dữ liệu không phải object")
        return {}
    if payload.get("success") is False:
        logger.warning(f"Delist API báo lỗi: {payload}")
        return {}

    items = payload.get("data")
    if not isinstance(items, list):
        logger.warning("Delist API thiếu trường data dạng list")
        return {}

    now_utc = datetime.utcnow()
    event_type_label = {
        "futures": "FUT",
        "spot": "SPOT",
        "spot_pair_removal": "SPOT",
        "margin": "MG",
        "loan": "LOAN",
    }
    # pair -> (dt, message)
    best: dict = {}

    for it in items:
        if not isinstance(it, dict):
            continue
        base = _normalize_delist_base_symbol(it.get("symbol"))
        dt_txt = str(it.get("delist_datetime") or "").strip()
        if not base or not dt_txt:
            continue

        dt_utc = _parse_delist_datetime_utc(dt_txt)
        if dt_utc is None:
            logger.debug(f"Delist API: bỏ qua mốc không parse được: {dt_txt!r}")
            continue
        if dt_utc <= now_utc:
            continue

        pair_key = f"{base}/USDT"
        et = str(it.get("event_type") or "").strip().lower()
        et_lbl = event_type_label.get(et, et.upper() if et else "DELIST")
        label = f"⚠️ {et_lbl} DELIST: {dt_txt}"
        prev = best.get(pair_key)
        if prev is None or dt_utc < prev[0]:
            best[pair_key] = (dt_utc, label)

    out = {k: v[1] for k, v in best.items()}
    logger.info(f"Delist API: {len(out)} cặp có mốc delist trong tương lai")
    return out


def _merge_delist_warn_api_and_cms(api_map: dict, cms_map: dict) -> dict:
    """Gộp cảnh báo từ API delist (ưu tiên hiển thị trước) và catalog Support (FUT/SPOT/MG + ngày)."""
    keys = set(api_map or {}) | set(cms_map or {})
    merged: dict = {}
    for k in keys:
        parts = []
        if api_map and k in api_map and api_map[k]:
            parts.append(api_map[k])
        if cms_map and k in cms_map and cms_map[k]:
            parts.append(f"Support: {cms_map[k]}")
        if parts:
            s = " | ".join(parts)
            merged[k] = s[: 400] if len(s) > 400 else s
    return merged


def _bb_upper_lower_from_closes(closing_prices, multiplier=2.0):
    """BB(20, multiplier) từ danh sách close (cùng logic get_bb)."""
    if len(closing_prices) < 20:
        return float("nan"), float("nan")
    arr = np.array(closing_prices[-20:], dtype=float)
    ma = float(np.mean(arr))
    std = float(np.std(arr))
    return ma + multiplier * std, ma - multiplier * std


def _rsi_simple_from_closes(closes, period=14):
    """RSI SMA gain/loss — dùng cho cột S (1d RSI) / data_collector."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        gains.append(max(0.0, ch))
        losses.append(max(0.0, -ch))
    ag = float(np.mean(gains))
    al = float(np.mean(losses))
    rs = ag / al if al != 0 else 0
    return float(100 - (100 / (1 + rs)))


def _rsi_wilder_from_closes(closes, period=14):
    """RSI Wilder's Smoothed EMA — khớp với TradingView RSI 14.
    Cần ít nhất period*3 nến để warmup đủ chính xác.
    """
    if len(closes) < period + 1:
        return None
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(0.0, c) for c in changes]
    losses = [max(0.0, -c) for c in changes]

    # Wilder: SMA cho period đầu tiên, sau đó EMA với alpha = 1/period
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def _max_daily_volatility_from_ohlcv(ohlcv):
    """(max_vol_pct, date_str) từ list nến 1d — thay fetch riêng trong get_row_result."""
    if not ohlcv or len(ohlcv) == 0:
        return 0.0, "N/A"
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    op = df["open"].replace(0, np.nan)
    vp = (df["high"] - df["low"]) / op * 100
    if not np.isfinite(vp).any():
        return 0.0, "N/A"
    imax = int(np.nanargmax(vp.values))
    ts = int(df.iloc[imax]["timestamp"])
    return round(float(vp.iloc[imax]), 2), datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")


def _amplitude_range_from_ohlcv_slice(ohlcv_slice):
    """Giống calculate_price_range nhưng không fetch — dùng cho P/Q 30d từ cache 1d."""
    if not ohlcv_slice or len(ohlcv_slice) == 0:
        return float("nan"), float("nan")
    df = pd.DataFrame(ohlcv_slice, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["price_change"] = df["close"] - df["open"]
    df["direction"] = df["price_change"].apply(
        lambda x: "Tăng" if x > 0 else "Giảm" if x < 0 else "Đứng giá"
    )
    max_price = df.apply(
        lambda row: max(row["close"], row["open"]) if row["direction"] == "Giảm" else min(row["close"], row["open"]),
        axis=1,
    )
    df["amplitude_percent"] = (df["high"] - df["low"]) / max_price * 100
    inc = df[df["direction"] == "Tăng"]["amplitude_percent"].max()
    dec = df[df["direction"] == "Giảm"]["amplitude_percent"].max()
    max_inc = round(float(inc), 2) if pd.notna(inc) else float("nan")
    max_dec = round(float(dec), 2) if pd.notna(dec) else float("nan")
    return max_inc, max_dec


def _bb_width_3d_and_now_from_ohlcv(ohlcv_1d, period=20, std_dev=2):
    """(width 3 phiên trước, width hiện tại) — (U-L)/Mid khung 1d.
    Dùng nến đã đóng (bỏ nến đang hình thành) + population std (ddof=0) để khớp TradingView.
    """
    # Loại nến đang hình thành (phần tử cuối): chỉ bỏ nếu có đủ nến để tính
    ohlcv_closed = ohlcv_1d[:-1] if ohlcv_1d and len(ohlcv_1d) > period + 3 else ohlcv_1d
    if not ohlcv_closed or len(ohlcv_closed) < period + 3:
        return None, None
    df = pd.DataFrame(ohlcv_closed, columns=["timestamp", "open", "high", "low", "close", "volume"])
    close = df["close"]
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std(ddof=0)  # population std — khớp TradingView
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    mid = sma.replace(0, np.nan)
    width = (upper - lower) / mid
    cur, ago = width.iloc[-1], width.iloc[-4]

    def _ok(x):
        try:
            fx = float(x)
            return math.isfinite(fx)
        except (TypeError, ValueError):
            return False

    return (float(ago) if _ok(ago) else None), (float(cur) if _ok(cur) else None)


def calculate_max_increase_decrease_4h(pair, timeframe='4h', days=cst.max_increase_decrease_4h_day_count):
    
    candles_per_day = 24 // 4
    length = days * candles_per_day

    
    ohlcv_data = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=length)

    
    df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    
    df['change_percent'] = (df['close'] - df['open']) / df['open'] * 100

    
    max_increase = round(df['change_percent'].max(), 2)

    
    max_decrease = round(df['change_percent'].min(), 2)

    return max_increase, max_decrease



def calculate_price_thoi_gian_max(pair):

    
    
    
    

    now = exchange.milliseconds()
    start_time = now - (3 * 24 * 60 * 60 * 1000)
    end_time = now

    
    ohlcv_day = exchange.fetch_ohlcv(pair, timeframe = '1d', since=start_time, limit=10,  params={'endTime':  end_time})
    max_candle_day = max(ohlcv_day, key=lambda x: x[2])
    min_candle_day = min(ohlcv_day, key=lambda x: x[3])

    
    ohlcv_minute_high = exchange.fetch_ohlcv(pair, timeframe = '1m', since=max_candle_day[0], limit=1444, params={'endTime':  max_candle_day[0] + (24 * 60 * 60 * 1000)})
    print(len(ohlcv_minute_high))
    max_high_candle_minute = max(ohlcv_minute_high, key=lambda x: x[2])
    highest_price = max_high_candle_minute[2]
    highest_price_time = max_high_candle_minute[0]
    
    time_delta_highest =  round((now - highest_price_time) / (1000 * 60) )

    
    ohlcv_minute_low = exchange.fetch_ohlcv(pair, timeframe = '1m', since=min_candle_day[0], limit=1444, params={'endTime':  min_candle_day[0]  + (24 * 60 * 60 * 1000)})
    print(len(ohlcv_minute_low))

    min_low_candle_minute = min(ohlcv_minute_low, key=lambda x: x[3])
    lowest_price = min_low_candle_minute[3]
    lowest_price_time = min_low_candle_minute[0]
    
    time_delta_lowest =  round((now - lowest_price_time) / (1000 * 60))
    
    return highest_price, utils.convert_unix_timestamp(highest_price_time/1000), time_delta_highest, lowest_price, utils.convert_unix_timestamp(lowest_price_time/1000), time_delta_lowest

def calculate_bien_do_theo_gio(pair, timeframe):

    length = 6  
    
    length = int(length)

    
    ohlcv_data = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=length)

    
    df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    
    df['price_change'] = df['close'] - df['open']
    df['direction'] = df['price_change'].apply(lambda x: 'Tăng' if x > 0 else 'Giảm' if x < 0 else 'Đứng giá')

    max_price = df.apply(lambda row: max(row['close'], row['open']) if row['direction'] == 'Giảm' else min(row['close'], row['open']), axis=1)

    
    
    df['amplitude_percent'] = ((df['high'] - df['low']) / max_price) * 100
    
    
    

    return df['amplitude_percent'] .values


def get_bien_do_theo_gio(pair):
    rounded_arr = np.round(calculate_bien_do_theo_gio(pair,  '1h')[::-1], decimals=2)
    return rounded_arr.tolist()
    

def get_thoi_gian_max_min(pair):
    print(f"max tthoi gian: {pair}")
    res = []
    highest_price, time_delta_highest, lowest_price, time_delta_lowest = calculate_price_thoi_gian_max(pair, 3)
    res.append(time_delta_highest)
    res.append(highest_price)
    res.append(time_delta_lowest)
    res.append(lowest_price)
    
    return res

def calculate_price_range(pair, num_days, timeframe):
    if timeframe == '15m':
        length = num_days * 24 * 60 / 15  
    elif timeframe == '1h':
        length = num_days * 24  
    elif timeframe == '1d':
        length = num_days  
    
    length = int(length)

    
    ohlcv_data = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=length)

    
    df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    

    
    df['price_change'] = df['close'] - df['open']
    df['direction'] = df['price_change'].apply(lambda x: 'Tăng' if x > 0 else 'Giảm' if x < 0 else 'Đứng giá')

    max_price = df.apply(lambda row: max(row['close'], row['open']) if row['direction'] == 'Giảm' else min(row['close'], row['open']), axis=1)

    
    
    df['amplitude_percent'] = ((df['high'] - df['low']) / max_price) * 100

    
    amplitude_increase = df[df['direction'] == 'Tăng']['amplitude_percent'].max()
    amplitude_decrease = df[df['direction'] == 'Giảm']['amplitude_percent'].max()

    
    max_price_increase =round(amplitude_increase, 2)

    
    max_price_decrease = round(amplitude_decrease, 2)

    return max_price_increase, max_price_decrease

def calculate_high_low_30d(pair, timeframe='1d'):
    num_days = calculate_high_low_day_total
    length = num_days  

    
    ohlcv_data = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=length)

    
    df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    
    highest_price = df['high'].max()
    lowest_price = df['low'].min()

    return highest_price, lowest_price

def calculate_max_daily_volatility(pair, lookback_days=365):
    """
    Tính biên độ giá ngày lớn nhất trong lịch sử
    
    Args:
        pair: Cặp giao dịch (VD: BTC/USDT:USDT)
        lookback_days: Số ngày nhìn lại (mặc định 365)
    
    Returns:
        Tuple (max_volatility_percent, max_volatility_date)
    """
    try:
        # Lấy dữ liệu nến 1d
        now = exchange.milliseconds()
        start_time = now - (lookback_days * 24 * 60 * 60 * 1000)
        
        ohlcv = exchange.fetch_ohlcv(
            pair,
            timeframe='1d',
            since=start_time,
            limit=lookback_days + 10
        )
        
        if not ohlcv or len(ohlcv) == 0:
            return 0.0, "N/A"
        
        # Chuyển sang DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Tính biên độ % = (High - Low) / Open * 100
        df['volatility_percent'] = ((df['high'] - df['low']) / df['open']) * 100
        
        # Tìm ngày có biên độ lớn nhất
        max_idx = df['volatility_percent'].idxmax()
        max_row = df.loc[max_idx]
        
        max_volatility = round(max_row['volatility_percent'], 2)
        max_date = datetime.fromtimestamp(max_row['timestamp'] / 1000).strftime('%Y-%m-%d')
        
        return max_volatility, max_date
        
    except Exception as e:
        logger.error(f"Lỗi tính biên độ giá ngày lớn nhất cho {pair}: {e}", exc_info=True)
        return 0.0, "ERROR"


def get_bien_do_max(pair):
    res = []

    
    

    max_price_increase_month, max_price_decrease_month = calculate_price_range(pair, 7, '15m')
    res.append(max_price_increase_month)
    res.append(max_price_decrease_month)

    
    

    max_price_increase_month1, max_price_decrease_month1 = calculate_price_range(pair, 7, '1h')
    res.append(max_price_increase_month1)
    res.append(max_price_decrease_month1)

    
    

    max_price_increase_month2, max_price_decrease_month2 = calculate_price_range(pair, 30, '1d')
    res.append(max_price_increase_month2)
    res.append(max_price_decrease_month2)

    return res


def get_bb(pair, timeframes):
    bb = []
    length = 20
    multiplier = 2

    
    for timeframe in timeframes:
        
        ohlcv_data = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=length)

        
        closing_prices = [ohlcv[4] for ohlcv in ohlcv_data]

        
        moving_average = np.mean(closing_prices)

        
        standard_deviation = np.std(closing_prices)

        
        upper_band = moving_average + multiplier * standard_deviation
        lower_band = moving_average - multiplier * standard_deviation
        bb.append(upper_band)
        bb.append(lower_band)
        if cst.is_print_mode:
            print(f"Giá trị của dải Bollinger cho khung thời gian {timeframe}:")
            print(f"- Upper Band: {upper_band}")
            print(f"- Lower Band: {lower_band}")
    return bb


def get_price_last5m(pair):
    prices = []
    current_timestamp = int(time.time())
    for minutes_ago in range(1,6):
        timestamp = current_timestamp - minutes_ago * 60
        ohlcv_data = exchange.fetch_ohlcv(pair, timeframe='1m', since=timestamp * 1000, limit=1)
        if ohlcv_data:
            closing_price = ohlcv_data[0][4]
            prices.append(closing_price)
        else:
            if prices:
                prices.append(prices[-1])
            else:
                prices.append(None)
    return  prices


def get_result(pair, request_type):
    try:
        
        
            if request_type == RequestType.GET_PRICE:
                result_array = get_price_last5m(pair)
            elif request_type == RequestType.GET_BB:
                result_array = get_bb(pair,    timeframes = ['15m', '1h', '1d', '1w', '1M'])
            elif request_type == RequestType.GET_BIEN_DO_MAX:
                result_array = get_bien_do_max(pair)
            elif request_type == RequestType.GET_THOI_GIAN_MAX:
                result_array = get_thoi_gian_max_min(pair)
            elif request_type == RequestType.GET_BIEN_DO_THEO_GIO:
                result_array = get_bien_do_theo_gio(pair)

            return  result_array
        
        
    except ccxt.NetworkError as e:
        return f"Lỗi mạng: {e}"
    except ccxt.ExchangeError as e:
        return f"Lỗi sàn giao dịch: {e}"
    except Exception as e:
        return f"Lỗi: {e}"
    
def get_results(pairs, request_type):
    try:
        result_arrs = []
        for pair_arr in pairs:
            pair = pair_arr[0]

            if request_type == RequestType.GET_PRICE:
                result_array = get_price_last5m(pair)
            elif request_type == RequestType.GET_BB:
                result_array = get_bb(pair,  timeframes = ['15m', '1h', '1d'])
            elif request_type == RequestType.GET_BIEN_DO_MAX:
                result_array = get_bien_do_max(pair)
            elif request_type == RequestType.GET_THOI_GIAN_MAX:
                result_array = get_thoi_gian_max_min(pair)
            elif request_type == RequestType.GET_BIEN_DO_THEO_GIO:
                result_array = get_bien_do_theo_gio(pair)


            result_arrs.append(result_array)
            

        return  result_arrs
    except ccxt.NetworkError as e:
        return f"Lỗi mạng: {e}"
    except ccxt.ExchangeError as e:
        return f"Lỗi sàn giao dịch: {e}"
    except Exception as e:
        return f"Lỗi: {e}"
    
from datetime import datetime,timezone
def get_volumes(symbol):
    
    timeframes = ['15m', '1h']
    volumes = {}

    for timeframe in timeframes:
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe)
        
        
        last_candle = ohlcv[-1]
        volume = last_candle[5]
        
        
        timestamp = last_candle[0] / 1000  
        datetime_str = datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        volumes[timeframe] = {
            'time': datetime_str,
            'volume': volume
        }

    return volumes

def is_valid_for_trading(symbol, tickers):
    """
    Kiểm tra mã có đủ dữ liệu lịch sử để giao dịch (loại bỏ mã mới listing hoặc không hoạt động)
    
    Args:
        symbol: Symbol cần kiểm tra (VD: BTC/USDT:USDT)
        tickers: Dict tickers từ exchange.fetch_tickers()
    
    Returns:
        Tuple (is_valid: bool, reason: str)
    """
    try:
        pair = symbol.replace(":USDT", "")
        
        # Check 1: Volume 24h phải > 100k USDT (thanh khoản tối thiểu)
        vol_24h = tickers[symbol].get('quoteVolume', 0)
        if vol_24h < 100000:
            return False, f"Volume 24h quá thấp ({vol_24h:,.0f} USDT < 100k)"
        
        # Check 2: BB 1h không được trùng nhau (phải có đủ 20 nến historical)
        try:
            bb_1h = get_bb(pair, timeframes=['1h'])
            # Nếu BB upper ≈ BB lower (sai số < 0.01%) → không có đủ data
            if abs(bb_1h[0] - bb_1h[1]) < (bb_1h[0] * 0.0001):
                return False, "Không có đủ historical data (BB1h trùng nhau)"
        except:
            return False, "Lỗi lấy BB (có thể mã mới listing)"
        
        # Check 3: High/Low 40 ngày phải khác nhau (có biến động)
        try:
            high_40d, low_40d = calculate_high_low_30d(pair, timeframe='1d')  # ✅ FIX: dùng pair
            # Nếu High ≈ Low (sai số < 0.01%) → mới listing, chưa dao động
            if abs(high_40d - low_40d) < (high_40d * 0.0001):
                return False, "Mã mới listing (High 40d ≈ Low 40d)"
        except Exception as e:
            return False, f"Lỗi lấy High/Low 40d: {str(e)}"
        
        return True, "OK"
        
    except Exception as e:
        return False, f"Lỗi kiểm tra: {e}"


# Hai mã tham chiếu: luôn đứng đầu mỗi khối (giảm / tăng) trên sheet — yêu cầu khách hàng
SHEET_LEADER_SYMBOLS = ("BTC/USDT:USDT", "BTCDOM/USDT:USDT")


def merge_top_list_with_sheet_leaders(sorted_candidates, tickers, top_count, leaders=SHEET_LEADER_SYMBOLS):
    """
    Đặt leaders (có trong tickers) lên đầu, phần sau lấy từ sorted_candidates đã loại trùng.
    Tổng độ dài = min(top_count, len(front) + len(rest)).
    """
    front = [s for s in leaders if s in tickers]
    for s in leaders:
        if s not in tickers:
            logger.warning(f"Mã cố định đầu sheet không có trong tickers: {s}")
    rest = [s for s in sorted_candidates if s not in front]
    need = max(0, top_count - len(front))
    return front + rest[:need]


def do_it():
    print(f"\n{'='*80}", flush=True)
    print(f"🚀 BẮT ĐẦU CẬP NHẬT SHEET 100 MÃ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"{'='*80}\n", flush=True)
    
    logger.info("========================================")
    logger.info("BẮT ĐẦU CẬP NHẬT DỮ LIỆU SHEET 100 MÃ")
    logger.info("========================================")
    start_time = time.time()

    # Fix: Khởi tạo data_collector ngay đầu hàm
    data_collector = get_data_collector(exchange)
    logger.info("Đã khởi tạo data_collector")
    
    logger.info("Đang lấy tickers từ Binance...")
    tickers = exchange.fetch_tickers()
    logger.info(f"Đã lấy {len(tickers)} tickers từ Binance")
    print(f"✅ Đã lấy {len(tickers)} tickers — đang lọc USDT futures...", flush=True)

    # Bước 1: Lấy tất cả futures USDT
    logger.info("Bước 1: Lọc symbols Futures USDT...")
    all_futures_usdt = [
        symbol for symbol in tickers.keys()
        if '/USDT' in symbol 
        and "-" not in symbol
        and tickers[symbol].get('percentage') is not None
    ]
    print(f"📊 Tổng số futures USDT trên Binance: {len(all_futures_usdt)}", flush=True)
    logger.info(f"Tổng số futures USDT trên Binance: {len(all_futures_usdt)}")
    
    # Bước 2: Đọc whitelist (với error handling) — có thể lâu nếu Google Sheet chậm / mạng
    logger.info("Bước 2: Đọc whitelist từ sheet 'list'...")
    try:
        white_list = set(gg_sheet_factory.get_white_list())
        print(f"📝 Whitelist từ sheet 'list': {len(white_list)} mã", flush=True)
        logger.info(f"Whitelist từ sheet 'list': {len(white_list)} mã")
        if white_list:
            print(f"   Nội dung (10 mã đầu): {list(white_list)[:10]}", flush=True)
            logger.info(f"Nội dung whitelist (10 mã đầu): {list(white_list)[:10]}")
    except Exception as e:
        print(f"⚠️  Không đọc được whitelist từ sheet 'list': {e}", flush=True)
        print(f"   💡 Sẽ sử dụng TẤT CẢ MÃ từ Binance", flush=True)
        logger.warning(f"Không đọc được whitelist từ sheet 'list': {e}")
        logger.info("Sẽ sử dụng TẤT CẢ MÃ từ Binance")
        white_list = set()  # Whitelist rỗng = lấy tất cả
    
    # Bước 3: Lọc theo whitelist (nếu có)
    logger.info("Bước 3: Lọc theo whitelist...")
    if white_list:
        futures_symbols = [
            symbol for symbol in all_futures_usdt
            if symbol in white_list
        ]
        print(f"✅ Số mã sau khi lọc whitelist: {len(futures_symbols)}", flush=True)
        logger.info(f"Số mã sau khi lọc whitelist: {len(futures_symbols)}")
        
        # Warning nếu không có mã nào match
        if len(futures_symbols) == 0:
            print(f"⚠️  CẢNH BÁO: Không có mã nào trong whitelist match với Binance!", flush=True)
            print(f"   💡 Kiểm tra lại sheet 'list' - có thể mã không tồn tại hoặc format sai", flush=True)
            print(f"   📝 Ví dụ 5 mã đúng trên Binance: {all_futures_usdt[:5]}", flush=True)
            print(f"   🔄 Chuyển sang dùng TẤT CẢ MÃ...", flush=True)
            logger.warning("Không có mã nào trong whitelist match với Binance - chuyển sang dùng TẤT CẢ MÃ")
            futures_symbols = all_futures_usdt  # Fallback: dùng tất cả mã
    else:
        # Whitelist trống → dùng tất cả mã
        print(f"💡 Whitelist trống → Sử dụng TẤT CẢ {len(all_futures_usdt)} mã từ Binance", flush=True)
        logger.info(f"Whitelist trống → Sử dụng TẤT CẢ {len(all_futures_usdt)} mã từ Binance")
        futures_symbols = all_futures_usdt
    
    # Bước 4: Lọc nhanh từ tickers — không gọi API thêm
    # Loại bỏ:
    #   - Volume 24h < 100k USDT (thanh khoản quá thấp)
    #   - last = None / 0 / NaN  → pre-launch, expired, index contract (PORT3, RVV, BSW, SKATE…)
    # Không dùng bid: fetch_tickers() Binance Futures thường không trả về bid trong snapshot
    logger.info(f"Bước 4: Lọc nhanh {len(futures_symbols)} mã (volume + giá hợp lệ)...")
    before = len(futures_symbols)
    futures_symbols = [
        s for s in futures_symbols
        if (tickers[s].get("quoteVolume") or 0) >= 100_000
        and (tickers[s].get("last") or 0) > 0
    ]
    removed = before - len(futures_symbols)
    print(
        f"✅ Số mã hợp lệ sau lọc: {len(futures_symbols)}"
        f" (loại {removed} mã không có giá / thanh khoản thấp)",
        flush=True,
    )
    logger.info(f"Tiếp tục xử lý với {len(futures_symbols)} mã (đã loại {removed} mã)")

    # Bước 4b: load markets một lần — AB (Futures) / AC (Spot) từ exchangeInfo qua CCXT
    spot_markets_by_pair = {}
    try:
        spot_ex = exchange_class(
            {
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            }
        )
        spot_ex.timeout = 30000
        spot_ex.load_markets()
        for sym, m in spot_ex.markets.items():
            if not m or m.get("quote") != "USDT":
                continue
            if m.get("spot") and ":" not in sym and sym.endswith("/USDT"):
                spot_markets_by_pair[sym] = m
        print(f"📋 Spot USDT markets (cho cột AC): {len(spot_markets_by_pair)} cặp", flush=True)
        logger.info(f"Đã tải spot markets: {len(spot_markets_by_pair)} cặp USDT")
    except Exception as e:
        logger.warning(f"Không tải được spot markets (cột AC): {e}")

    try:
        exchange.load_markets()
        logger.info(f"Đã tải futures markets: {len(exchange.markets)} entries")
    except Exception as e:
        logger.warning(f"load_markets futures: {e}")

    print("📣 Đang tải cảnh báo delist (n8n API + Binance Support catalog 161)...", flush=True)
    delist_from_api = _load_future_delist_by_pair_from_api()
    delist_from_cms = _build_upcoming_delist_by_pair()
    delist_warn_by_pair = _merge_delist_warn_api_and_cms(delist_from_api, delist_from_cms)
    print(
        f"   └─ API (tương lai): {len(delist_from_api)} cặp | "
        f"CMS: {len(delist_from_cms)} cặp | gộp AK: {len(delist_warn_by_pair)} cặp",
        flush=True,
    )
    logger.info(
        f"Delist AK: api_future={len(delist_from_api)} cms={len(delist_from_cms)} merged={len(delist_warn_by_pair)}"
    )

    def get_row_result(symbol):
        """
        Gộp fetch OHLCV để giảm ~15+ request/mã (rate limit Binance) xuống còn vài request,
        tránh “đơ” lâu giữa các dòng log.
        """
        price = float(tickers[symbol].get("last") or 0)
        pct   = float(tickers[symbol].get("percentage") or 0)
        pair  = symbol.replace(":USDT", "")

        # Guard: symbol không có giá hợp lệ → trả về row trống, log cảnh báo
        if price <= 0:
            logger.warning(f"[{symbol}] last price = {price} — bỏ qua")
            empty = [""] * len(_DEBUG_COL_NAMES)
            empty[0] = pair
            empty[1] = pct
            empty[-1] = _delist_warn_lookup(delist_warn_by_pair, pair)
            return empty

        print(f"🔄 {symbol} - %24h: {pct:.2f}%, giá: {price}", flush=True)
        logger.info(f"get_row_result bắt đầu: {symbol}")
        row = [pair, pct, price]

        # --- 1) Một lần 1d: BB1d + Min/Max 40d + RSI 1d + P/Q 30d + AD-AE ---
        ohlcv_1d = []
        try:
            ohlcv_1d = exchange.fetch_ohlcv(pair, "1d", limit=_OHLCV_1D_LIMIT)
        except Exception as e:
            logger.warning(f"[{pair}] fetch_ohlcv 1d: {e}")

        closes_1d = [x[4] for x in ohlcv_1d] if ohlcv_1d else []
        # BB1d: dùng nến ĐÃ ĐÓNG (loại nến đang hình thành) để khớp TradingView.
        # Với coin crash mạnh trong ngày (như STO -86%), nến đang hình thành kéo BB xuống sai.
        closes_1d_closed = closes_1d[:-1] if len(closes_1d) > 20 else closes_1d
        bb1d_u, bb1d_l = _bb_upper_lower_from_closes(closes_1d_closed) if len(closes_1d_closed) >= 20 else (float("nan"), float("nan"))

        # --- 2) Một lần 1h (20 nến): BB1h + Vol X + AG/AH ---
        ohlcv_1h = []
        try:
            ohlcv_1h = exchange.fetch_ohlcv(pair, "1h", limit=20)
        except Exception as e:
            logger.warning(f"[{pair}] fetch_ohlcv 1h: {e}")

        closes_1h = [x[4] for x in ohlcv_1h] if ohlcv_1h else []
        bb1h_u, bb1h_l = _bb_upper_lower_from_closes(closes_1h) if len(closes_1h) >= 20 else (float("nan"), float("nan"))
        result_bb_array = [bb1h_u, bb1h_l]  # dùng cho % đến BB1h (cột V/W)

        # Cập nhật giá tươi từ nến 1h gần nhất (nến đang hình thành = live price)
        # Tránh giá bị trễ 10-15 phút khi tickers[] được fetch 1 lần ở đầu cho 100 mã
        if ohlcv_1h:
            price = float(ohlcv_1h[-1][4])
            row[2] = price  # cập nhật col C với giá tươi hơn
            logger.debug(f"[{pair}] Giá cập nhật từ 1h close: {price}")

        # Zombie coin guard: BB1h upper ≈ BB1h lower → giá đóng băng (token đang delist)
        # Binance giữ các token này trong fetch_tickers() với last>0 và volume cũ còn cao,
        # nhưng ohlcv chỉ trả về nến có giá cố định → std=0 → upper=lower=last
        # Không cần API call thêm vì ohlcv_1h đã có sẵn ở trên
        if (math.isfinite(bb1h_u) and math.isfinite(bb1h_l)
                and bb1h_u > 0
                and abs(bb1h_u - bb1h_l) < bb1h_u * 0.0001):
            logger.warning(f"[{symbol}] BB1h upper≈lower ({bb1h_u:.6f}) — zombie/delisted coin, bỏ qua")
            print(f"⏭️  [{symbol}] BB1h trùng nhau → token đang delist, bỏ qua", flush=True)
            empty = [""] * len(_DEBUG_COL_NAMES)
            empty[0] = pair
            empty[1] = pct
            empty[-1] = _delist_warn_lookup(delist_warn_by_pair, pair)
            return empty

        # Một lần 4h (20 nến): tái dùng cho Vol Y / RSI AF
        ohlcv_4h = []
        try:
            # 100 nến để Wilder's RSI (14) có đủ warmup (~50+ nến extra)
            ohlcv_4h = exchange.fetch_ohlcv(pair, "4h", limit=100)
        except Exception as e:
            logger.warning(f"[{pair}] fetch_ohlcv 4h: {e}")
        closes_4h = [x[4] for x in ohlcv_4h] if ohlcv_4h else []

        # D-E BB1h, F-G BB4h, H-I BB1d → tổng 36 cột A-AJ khớp header
        bb4h_u, bb4h_l = _bb_upper_lower_from_closes(closes_4h) if len(closes_4h) >= 20 else (float("nan"), float("nan"))
        row.extend([bb1h_u, bb1h_l, bb4h_u, bb4h_l, bb1d_u, bb1d_l])

        # J-K: biên độ 1h tuần (vẫn cần fetch 7d 1h)
        try:
            max_price_increase_month1, max_price_decrease_month1 = calculate_price_range(pair, 7, "1h")
            max_price_increase_month1 = "" if pd.isna(max_price_increase_month1) else max_price_increase_month1
            max_price_decrease_month1 = "" if pd.isna(max_price_decrease_month1) else max_price_decrease_month1
        except Exception as e:
            logger.warning(f"[{pair}] calculate_price_range 7d/1h: {e}")
            max_price_increase_month1, max_price_decrease_month1 = "", ""
        row.append(max_price_increase_month1)
        row.append(max_price_decrease_month1)

        # L-M: cao/thấp N ngày từ cache 1d (thay fetch riêng)
        nhl = min(calculate_high_low_day_total, len(ohlcv_1d))
        if nhl >= 1:
            sl = ohlcv_1d[-nhl:]
            high = max(c[2] for c in sl)
            low = min(c[3] for c in sl)
        else:
            high, low = 0.0, 0.0
        row.append(high)
        row.append(low)

        try:
            increase, decrease = calculate_max_increase_decrease_4h(pair)
        except Exception as e:
            logger.warning(f"[{pair}] calculate_max_increase_decrease_4h: {e}")
            increase, decrease = "", ""
        row.append(increase)
        row.append(decrease)

        try:
            bb_1w = get_bb(pair, timeframes=["1w"])
        except Exception as e:
            logger.warning(f"[{pair}] get_bb 1w: {e}")
            bb_1w = [float("nan"), float("nan")]
        row.extend(bb_1w)

        # R-S: biên độ 30d từ 30 nến 1d cuối (không gọi get_bien_do_max cho 1d)
        try:
            if len(ohlcv_1d) >= 30:
                p30, q30 = _amplitude_range_from_ohlcv_slice(ohlcv_1d[-30:])
            else:
                p30, q30 = calculate_price_range(pair, 30, "1d")
        except Exception as e:
            logger.warning(f"[{pair}] biên độ 30d: {e}")
            p30, q30 = float("nan"), float("nan")
        row.append("" if pd.isna(p30) else p30)
        row.append("" if pd.isna(q30) else q30)

        try:
            volume_24h = tickers[symbol].get("quoteVolume", 0)
            row.append(volume_24h)
            rsi_1d = _rsi_simple_from_closes(closes_1d, period=14) if len(closes_1d) >= 15 else None
            row.append(round(rsi_1d, 2) if rsi_1d is not None else "")
        except Exception:
            row.extend([0, 0])

        row.append("")

        if low != 0:
            row.append(round((bb_1w[1] / low), 4))
        else:
            row.append("")

        distance_to_bb_up = round(((result_bb_array[0] - price) / price) * 100, 2) if price != 0 else 0
        distance_to_bb_down = round(((price - result_bb_array[1]) / price) * 100, 2) if price != 0 else 0
        row.append(distance_to_bb_up)
        row.append(distance_to_bb_down)

        # Z: vol nến 1h hiện tại (USDT); AA: vol 4h (USDT) — base × close price
        vol_1h_last = round(float(ohlcv_1h[-1][5]) * float(ohlcv_1h[-1][4]), 2) if ohlcv_1h else 0.0
        row.append(vol_1h_last)

        vol_4h_last = round(float(ohlcv_4h[-1][5]) * float(ohlcv_4h[-1][4]), 2) if ohlcv_4h else 0.0
        row.append(vol_4h_last)

        # AB: Futures (symbol đúng dạng BTC/USDT:USDT) | AC: Spot cùng base (BTC/USDT)
        fut_m = exchange.markets.get(symbol) if getattr(exchange, "markets", None) else None
        row.append(_listing_status_cell(fut_m))
        spot_m = spot_markets_by_pair.get(pair)
        row.append(_listing_status_cell(spot_m) if spot_m else "Không có spot")

        try:
            cutoff_ms = exchange.milliseconds() - 365 * 24 * 60 * 60 * 1000
            ohlcv_ab = [c for c in ohlcv_1d if c[0] >= cutoff_ms] or ohlcv_1d
            max_vol, max_date = _max_daily_volatility_from_ohlcv(ohlcv_ab)
            logger.info(f"✅ [{pair}] Biên độ lớn nhất: {max_vol}% vào {max_date}")
            print(f"   └─ AD={max_vol}%, AE={max_date}", flush=True)
            row.append(max_vol)
            row.append(max_date)
        except Exception as e:
            logger.error(f"❌ [{pair}] Lỗi AD-AE (biên độ ngày): {e}", exc_info=True)
            print(f"   └─ ❌ Lỗi AD-AE: {e}", flush=True)
            row.extend([0, "N/A"])

        bw_3d, bw_now = _bb_width_3d_and_now_from_ohlcv(ohlcv_1d)
        row.append(round(bw_3d * 100, 2) if bw_3d is not None else "")   # AF: BB Width 3d trước (%)
        row.append(round(bw_now * 100, 2) if bw_now is not None else "")  # AG: BB Width hiện tại (%)

        rsi_4h = _rsi_wilder_from_closes(closes_4h, period=14)
        row.append(round(rsi_4h, 2) if rsi_4h is not None else "")

        if ohlcv_1h and len(ohlcv_1h) >= 20:
            # Vol 1h tính bằng USDT: base_vol × close_price của từng nến
            vols_usdt = [float(x[5]) * float(x[4]) for x in ohlcv_1h]
            row.append(round(vols_usdt[-1], 2))           # AI: Vol 1h hiện tại (USDT)
            row.append(round(float(np.mean(vols_usdt)), 2))  # AJ: Vol 1h MA20 (USDT)
        else:
            row.extend(["", ""])

        # AK: API delist-current-month (mốc tương lai, có ⚠️) + catalog Support (FUT/SPOT/MG + ngày)
        row.append(_delist_warn_lookup(delist_warn_by_pair, pair))

        logger.info(f"get_row_result xong: {symbol}")
        if ENABLE_DEBUG_DATA:
            write_symbol_debug_log(symbol, row)
        return row


    logger.info("Bước 5: Tạo top lists...")

    tab_100_ma_2d_arr = []
    title1 = f"Top {cst.top_count} có % giảm giá nhiều nhất trong 24h"
    title2 = f"Top {cst.top_count} có % tăng giá nhiều nhất trong 24h"
    empty_row = [""] * 37  # A-AK

    # ── Hàng 3 & 4: BTCDOM và BTC cố định (luôn hiển thị bất kể tăng/giảm) ──
    # Thứ tự: BTCDOM trước (hàng 3), BTC sau (hàng 4)
    logger.info("Bước 6a: Lấy dữ liệu BTC/BTCDOM cố định (hàng 3-4)...")
    print(f"\n{'='*60}", flush=True)
    print(f"📌 XỬ LÝ 2 MÃ CỐ ĐỊNH: BTCDOM (hàng 3) + BTC (hàng 4)", flush=True)
    print(f"{'='*60}\n", flush=True)

    for fixed_sym in ("BTCDOM/USDT:USDT", "BTC/USDT:USDT"):
        if fixed_sym in tickers:
            print(f"📌 Lấy dữ liệu {fixed_sym}...", flush=True)
            tab_100_ma_2d_arr.append(get_row_result(fixed_sym))
        else:
            logger.warning(f"{fixed_sym} không có trong tickers, ghi dòng trống")
            tab_100_ma_2d_arr.append(empty_row)

    # ── Danh sách giảm / tăng: loại BTC và BTCDOM ra (đã có ở hàng 3-4) ──
    excluded = set(SHEET_LEADER_SYMBOLS)
    giam_symbols = [s for s in futures_symbols
                    if tickers[s]['percentage'] < 0 and s not in excluded]
    tang_symbols = [s for s in futures_symbols
                    if tickers[s]['percentage'] > 0 and s not in excluded]

    print(f"📊 Phân loại: {len(giam_symbols)} mã giảm, {len(tang_symbols)} mã tăng (không gồm BTC/BTCDOM)", flush=True)
    logger.info(f"Phân loại: {len(giam_symbols)} mã giảm, {len(tang_symbols)} mã tăng")

    list_giam_nhieu_nhat = sorted(giam_symbols, key=lambda x: tickers[x]["percentage"])[:cst.top_count]
    list_tang_nhieu_nhat = sorted(tang_symbols, reverse=True, key=lambda x: tickers[x]["percentage"])[:cst.top_count]

    if list_giam_nhieu_nhat:
        print(f"✅ Top giảm: {len(list_giam_nhieu_nhat)} mã | "
              f"Phạm vi %: {tickers[list_giam_nhieu_nhat[0]]['percentage']:.2f}% → "
              f"{tickers[list_giam_nhieu_nhat[-1]]['percentage']:.2f}%", flush=True)
    else:
        print(f"⚠️  Không có mã giảm giá!", flush=True)

    if list_tang_nhieu_nhat:
        print(f"✅ Top tăng: {len(list_tang_nhieu_nhat)} mã | "
              f"Phạm vi %: {tickers[list_tang_nhieu_nhat[0]]['percentage']:.2f}% → "
              f"{tickers[list_tang_nhieu_nhat[-1]]['percentage']:.2f}%", flush=True)
    else:
        print(f"⚠️  Không có mã tăng giá!", flush=True)

    logger.info(f"Top giảm: {len(list_giam_nhieu_nhat)} mã | Top tăng: {len(list_tang_nhieu_nhat)} mã")

    # list_all.json khớp thứ tự sheet
    list_all = [title1, *list_giam_nhieu_nhat, title2, *list_tang_nhieu_nhat]
    with open("list_all.json", "w") as file:
        json.dump(list_all, file)

    logger.info("Bước 6b: Lấy dữ liệu cho từng symbol...")

    # ── Hàng 5: Tiêu đề GIẢM | Hàng 6-55: Top 50 giảm ──
    print(f"\n{'='*60}", flush=True)
    print(f"📉 BẮT ĐẦU XỬ LÝ {len(list_giam_nhieu_nhat)} MÃ GIẢM GIÁ (hàng 6-55)", flush=True)
    print(f"{'='*60}\n", flush=True)

    title_row_giam = [title1] + [""] * 36  # A + B..AK
    tab_100_ma_2d_arr.append(title_row_giam)  # hàng 5
    logger.info(f"Đang lấy dữ liệu cho {len(list_giam_nhieu_nhat)} mã giảm...")

    giam_data = []
    for idx, symbol in enumerate(list_giam_nhieu_nhat, 1):
        print(f"📉 [{idx}/{len(list_giam_nhieu_nhat)}] Xử lý mã giảm: {symbol}", flush=True)
        logger.info(f"Mã giảm [{idx}/{len(list_giam_nhieu_nhat)}]: {symbol}")
        giam_data.append(get_row_result(symbol))
        if is_test_mode:
            break

    tab_100_ma_2d_arr.extend(giam_data)
    print(f"✅ Đã lấy {len(giam_data)} mã giảm", flush=True)

    # Padding để đủ 50 dòng (hàng 6-55)
    rows_to_pad = cst.top_count - len(giam_data)
    if rows_to_pad > 0:
        if len(giam_data) < cst.top_count:
            print(f"⚠️  Chỉ có {len(giam_data)}/{cst.top_count} mã giảm trên thị trường", flush=True)
            logger.warning(f"Chỉ có {len(giam_data)}/{cst.top_count} mã giảm")
        print(f"   └─ Padding {rows_to_pad} dòng trống (hàng {6+len(giam_data)} → 55)", flush=True)
        logger.info(f"Padding {rows_to_pad} dòng trống cho phần giảm")
        for _ in range(rows_to_pad):
            tab_100_ma_2d_arr.append(empty_row)

    # ── Hàng 56: Tiêu đề TĂNG | Hàng 57-106: Top 50 tăng ──
    print(f"\n{'='*60}", flush=True)
    print(f"📈 BẮT ĐẦU XỬ LÝ {len(list_tang_nhieu_nhat)} MÃ TĂNG GIÁ (hàng 57-106)", flush=True)
    print(f"{'='*60}\n", flush=True)

    title_row_tang = [title2] + [""] * 36
    tab_100_ma_2d_arr.append(title_row_tang)  # hàng 56
    logger.info(f"Đang lấy dữ liệu cho {len(list_tang_nhieu_nhat)} mã tăng...")

    tang_data = []
    for idx, symbol in enumerate(list_tang_nhieu_nhat, 1):
        if is_test_mode:
            break
        print(f"📈 [{idx}/{len(list_tang_nhieu_nhat)}] Xử lý mã tăng: {symbol}", flush=True)
        logger.info(f"Mã tăng [{idx}/{len(list_tang_nhieu_nhat)}]: {symbol}")
        tang_data.append(get_row_result(symbol))

    tab_100_ma_2d_arr.extend(tang_data)
    print(f"✅ Đã lấy {len(tang_data)} mã tăng", flush=True)

    # Padding để đủ 50 dòng (hàng 57-106)
    rows_to_pad = cst.top_count - len(tang_data)
    if rows_to_pad > 0:
        if len(tang_data) < cst.top_count:
            print(f"⚠️  Chỉ có {len(tang_data)}/{cst.top_count} mã tăng trên thị trường", flush=True)
            logger.warning(f"Chỉ có {len(tang_data)}/{cst.top_count} mã tăng")
        print(f"   └─ Padding {rows_to_pad} dòng trống (hàng {57+len(tang_data)} → 106)", flush=True)
        logger.info(f"Padding {rows_to_pad} dòng trống cho phần tăng")
        for _ in range(rows_to_pad):
            tab_100_ma_2d_arr.append(empty_row)

    logger.info("Hoàn thành lấy dữ liệu cho top lists")
    # Cấu trúc: 2 cố định + 1 title_giam + 50 giảm + 1 title_tang + 50 tăng = 104 dòng
    logger.info(f"Tổng số dòng sau khi padding: {len(tab_100_ma_2d_arr)} (mong đợi: 2 cố định + 2 title + 100 data = 104 dòng)")

    # Lấy thông tin tài khoản (data_collector đã được khởi tạo ở đầu hàm)
    logger.info("Đang lấy thông tin tài khoản...")
    balance = exchange.fetch_balance()
    totalMarginBalance= round(float(balance["info"]["totalMarginBalance"]),4)
    totalCrossUnPnl= round(float(balance["info"]["totalCrossUnPnl"]),4)
    totalWalletBalance= round(float(balance["info"]["totalWalletBalance"]),4)
    logger.info(f"Margin: {totalMarginBalance}, Wallet: {totalWalletBalance}, PnL: {totalCrossUnPnl}")
    
    # Không cần Funding Rate trong bản đơn giản

    
    
    


    # Không cần ghi thêm dữ liệu bổ sung cho BTC/BTCDOM vào cột P (BB1w)
    # Tất cả các mã có đủ cột A–AK





    # Hàng 2: Thông tin tài khoản (giống file cũ)
    tab_100_ma_2d_arr = [["Số dư margin/ví/pnl", totalMarginBalance,  totalWalletBalance, totalCrossUnPnl]]  + tab_100_ma_2d_arr

    # Hàng 1: Tiêu đề các cột
    header_row = [
        "Mã",                           # A
        "% 24h",                        # B
        "Giá trị hiện thời",           # C
        "BB1h trên",                    # D
        "BB1h dưới",                    # E
        "BB4h trên",                    # F
        "BB4h dưới",                    # G
        "BB1 ngày trên",                # H
        "BB1 ngày dưới",                # I
        "Biên độ 1h max tăng tuần",    # J
        "Biên độ 1h max giảm tuần",    # K
        "Max 40 ngày",                  # L
        "Min 40 ngày",                  # M
        "Max tăng 4h/60 ngày",         # N
        "Max giảm 4h/60 ngày",         # O
        "Giá Cao Nhất",                # P: BB1w trên
        "Giá Thấp Nhất",               # Q: BB1w dưới
        "Biên độ 30d tăng",            # R
        "Biên độ 30d giảm",            # S
        "Volume 24h",                   # T
        "RSI 14",                       # U
        "",                             # V: Trống
        "Min/Min40",                    # W: BB1w dưới / Min 40 (Q/M)
        "% đến BB1h trên",             # X
        "% đến BB1h dưới",             # Y
        "Vol 1h",                       # Z
        "Vol 4h",                       # AA
        "Futures (trạng thái)",         # AB — Binance USDT-M exchangeInfo
        "Spot (trạng thái)",            # AC — Binance Spot exchangeInfo
        "Biên độ giá ngày lớn nhất (%)", # AD
        "Ngày biên độ lớn nhất",        # AE
        "BB width 1d (3 ngày trước)",   # AF
        "BB width 1d (hiện tại)",       # AG
        "RSI 14 (4h)",                  # AH
        "Vol 1h (hiện tại)",            # AI
        "Vol 1h MA20",                  # AJ
        "Cảnh báo delist sắp tới",      # AK: delist API + Support (CMS)
    ]
    
    # Thêm header vào đầu array
    tab_100_ma_2d_arr = [header_row] + tab_100_ma_2d_arr

    print(f"📊 Tổng số dòng dữ liệu: {len(tab_100_ma_2d_arr)}", flush=True)
    logger.info(f"Tổng số dòng dữ liệu: {len(tab_100_ma_2d_arr)}")
    
    # Ghi tất cả dữ liệu từ hàng 1
    write_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"💾 [{write_start}] Đang ghi {len(tab_100_ma_2d_arr)} dòng vào Google Sheet...", flush=True)
    logger.info(f"Bước 7: Ghi dữ liệu vào Google Sheet (bắt đầu ghi: {write_start})...")
    gg_sheet_factory.update_multi(gg_sheet_factory.tab_list_all_ma, -1, tab_100_ma_2d_arr, "A")
    print(f"✅ Đã ghi xong dữ liệu vào sheet!", flush=True)
    logger.info("Đã ghi dữ liệu vào sheet")
    
    # Ghi timestamp vào A1 — lấy datetime.now() SAU KHI update_multi xong
    # (tránh timestamp bị "cũ" nếu update_multi mất nhiều thời gian do retry/Google API chậm)
    time_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕐 Ghi timestamp {time_string} vào A1...", flush=True)
    gg_sheet_factory.update_single_value(gg_sheet_factory.tab_list_all_ma, "A1", time_string)
    logger.info(f"Đã ghi timestamp vào A1: {time_string}")

    

    end_time = time.time()
    execution_time = end_time - start_time
    print("=" * 80, flush=True)
    print(f"✅ HOÀN TẤT CẬP NHẬT - Thời gian: {execution_time:.2f} giây", flush=True)
    print(f"📊 Tổng số mã đã xử lý: {len(giam_data)} giảm + {len(tang_data)} tăng = {len(giam_data) + len(tang_data)} mã", flush=True)
    print("=" * 80, flush=True)
    logger.info("========================================")
    logger.info(f"HOÀN TẤT CẬP NHẬT - Thời gian: {execution_time:.2f} giây")
    logger.info(f"Tổng số mã đã xử lý: {len(giam_data)} giảm + {len(tang_data)} tăng")
    logger.info("========================================")
 

gg_sheet_factory.init_sheet_api()

# Banner khởi động
print("\n" + "="*80, flush=True)
print("║" + " "*78 + "║", flush=True)
print("║" + "  HD_UPDATE_ALL - BOT CẬP NHẬT SHEET 100 MÃ".center(78) + "║", flush=True)
print("║" + " "*78 + "║", flush=True)
print("="*80, flush=True)
print(f"📄 Log file: {log_filename}", flush=True)
print(f"⏱️  Delay: {cst.delay_update_all}s giữa các lần cập nhật", flush=True)
print(f"🔢 Top count: {cst.top_count} mã giảm + {cst.top_count} mã tăng", flush=True)
print(f"🧪 Test mode: {'BẬT' if is_test_mode else 'TẮT'}", flush=True)
print("="*80 + "\n", flush=True)

# Log thông tin khởi động
logger.info("╔════════════════════════════════════════════════════════════════╗")
logger.info("║         HD_UPDATE_ALL - BOT CẬP NHẬT SHEET 100 MÃ             ║")
logger.info("╚════════════════════════════════════════════════════════════════╝")
logger.info(f"Log file: {log_filename}")
logger.info(f"Delay giữa các lần cập nhật: {cst.delay_update_all} giây")
logger.info(f"Top count: {cst.top_count}")
logger.info(f"Test mode: {is_test_mode}")
logger.info("")







while True:
    try:
        do_it()
        

    except Exception as e:
        print(f"Tổng Lỗi: {e}", flush=True)
        logger.error(f"Tổng lỗi: {e}", exc_info=True)
        import traceback
        traceback.print_exc()

    if is_test_mode:
        logger.info("Test mode - Dừng bot")
        break
    
    # Countdown với output realtime
    print(f"\n⏳ Chờ {cst.delay_update_all} giây trước lần cập nhật tiếp theo...", flush=True)
    logger.info(f"Chờ {cst.delay_update_all} giây trước lần cập nhật tiếp theo...")
    
    # Hiển thị countdown mỗi 30s
    remaining = cst.delay_update_all
    while remaining > 0:
        if remaining % 30 == 0 or remaining <= 10:
            print(f"   ⏱️  Còn {remaining}s...", flush=True)
        time.sleep(1)
        remaining -= 1
    
    print(f"\n{'='*80}", flush=True)
    print(f"🔄 BẮT ĐẦU SCAN MỚI...", flush=True)
    print(f"{'='*80}\n", flush=True)
    logger.info("")



















