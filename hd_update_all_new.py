#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cập nhật sheet "New 100 mã (50 tăng và 50 giảm)" — cùng cấu trúc hàng với hd_update_all.

Logic lấy số liệu: Binance Futures public REST (giống symbol_data_fetch / feedback khách),
KHÔNG dùng CCXT cho ticker/klines/chỉ báo. CCXT chỉ dùng fetch_balance (hàng số dư).

Chạy: python hd_update_all_new.py
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

import ccxt
import cst
import gg_sheet_factory

file_name = os.path.basename(os.path.abspath(__file__))
os.system(f"title {file_name} - {cst.key_name}")

logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)
log_filename = logs_dir / f"hd_update_all_new_{datetime.now().strftime('%d_%m_%Y_%H_%M_%S')}.txt"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)
file_handler = logging.FileHandler(log_filename, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(file_handler)

is_test_mode = False
SHEET_NUM_COLUMNS = 0  # gán sau khi định nghĩa COL_NAMES
# Hàng 3 = BTCDOM, hàng 4 = BTC (giống hd_update_all.py)
SHEET_LEADER_SYMBOLS = ("BTCDOM/USDT:USDT", "BTC/USDT:USDT")

BASE_FUTURES = "https://fapi.binance.com"
BASE_SPOT = "https://api.binance.com"

exchange_id = "binance"
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    "enableRateLimit": True,
    "apiKey": cst.key_binance,
    "secret": cst.secret_binance,
    "options": {"defaultType": "future"},
})
exchange.setSandboxMode(False)
exchange.timeout = 30000

# Tên cột khớp sheet A→BF (hd_update_all.py)
COL_NAMES = [
    "Mã",
    "% 24h",
    "Giá trị hiện thời",
    "BB1h trên",
    "BB1h dưới",
    "BB4h trên",
    "BB4h dưới",
    "BB1 ngày trên",
    "BB1 ngày dưới",
    "Biên độ 1h max tăng tuần",
    "Biên độ 1h max giảm tuần",
    "Max 40 ngày",
    "Min 40 ngày",
    "Max tăng 4h/60 ngày",
    "Max giảm 4h/60 ngày",
    "Giá Cao Nhất (BB1w trên)",
    "Giá Thấp Nhất (BB1w dưới)",
    "Biên độ 30d tăng",
    "Biên độ 30d giảm",
    "Volume 24h",
    "RSI 14",
    "(trống V)",
    "Min/Min40 (BB1w dưới / Min40)",
    "% đến BB1h trên",
    "% đến BB1h dưới",
    "Vol 1h",
    "Vol 4h",
    "Futures (trạng thái)",
    "Spot (trạng thái)",
    "Biên độ giá ngày lớn nhất (%)",
    "Ngày biên độ lớn nhất",
    "BB width 1d (3 ngày trước)",
    "BB width 1d (hiện tại)",
    "RSI 14 (4h)",
    "Vol 1h (hiện tại)",
    "Vol 1h MA20",
    "Cảnh báo delist sắp tới",
    "MA7 (1h)",
    "MA25 (1h)",
    "MA99 (1h)",
    "MACD (1h)",
    "MACD Signal (1h)",
    "MACD Hist (1h)",
    "Stoch RSI %K (1h)",
    "Stoch RSI %D (1h)",
    "Open Interest (USDT)",
    "OI Δ 24h (%)",
    "L/S Ratio (account)",
    "L/S Ratio (top traders)",
    "Vol 1h / MA20 (ratio)",
    "Score LONG/SHORT (-10..+10)",
    "Gợi ý",
    "Lý do score",
    "Open 1h",
    "High 1h gần đây",
    "Low 1h gần đây",
    "Stoch %K (1h)",
    "Stoch %D (1h)",
]

SHEET_NUM_COLUMNS = len(COL_NAMES)

_EXCHANGE_FUT_CACHE: Optional[dict] = None
_EXCHANGE_SPOT_CACHE: Optional[dict] = None


def _http_get(base: str, path: str, params: Optional[dict] = None, timeout: int = 20) -> Any:
    qs = urllib.parse.urlencode(params or {})
    url = f"{base}{path}" + (f"?{qs}" if qs else "")
    req = urllib.request.Request(url, headers={"User-Agent": "symbol-data-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_symbol(raw: str) -> Tuple[str, str]:
    """
    Chuẩn hóa input → (symbol_binance, pair_display).
    VD: btc, BTC/USDT, BTC/USDT:USDT, BTCUSDT → (BTCUSDT, BTC/USDT)
    """
    s = (raw or "").strip().upper()
    if not s:
        raise ValueError("Symbol không được rỗng")
    s = s.replace(":USDT", "").replace("/", "").replace("-", "").replace("_", "")
    if not s.endswith("USDT"):
        s = f"{s}USDT"
    if not re.fullmatch(r"[A-Z0-9]{2,20}USDT", s):
        raise ValueError(f"Symbol không hợp lệ sau chuẩn hóa: {s}")
    base = s[:-4]
    return s, f"{base}/USDT"


def validate_futures_symbol(symbol_clean: str) -> str:
    """Kiểm tra symbol có trên Binance USDT-M; trả về status hoặc raise."""
    global _EXCHANGE_FUT_CACHE
    if _EXCHANGE_FUT_CACHE is None:
        _EXCHANGE_FUT_CACHE = _http_get(BASE_FUTURES, "/fapi/v1/exchangeInfo")
    for item in _EXCHANGE_FUT_CACHE.get("symbols", []):
        if item.get("symbol") == symbol_clean:
            return item.get("status", "UNKNOWN")
    raise ValueError(f"{symbol_clean} không tồn tại trên Binance Futures USDT-M")


def get_spot_status(symbol_clean: str) -> str:
    global _EXCHANGE_SPOT_CACHE
    if _EXCHANGE_SPOT_CACHE is None:
        try:
            _EXCHANGE_SPOT_CACHE = _http_get(BASE_SPOT, "/api/v3/exchangeInfo")
        except Exception:
            return "Không lấy được spot exchangeInfo"
    for item in _EXCHANGE_SPOT_CACHE.get("symbols", []):
        if item.get("symbol") == symbol_clean:
            return item.get("status", "UNKNOWN")
    return "Không có spot"


def fetch_klines(symbol_clean: str, interval: str, limit: int) -> List[list]:
    data = _http_get(
        BASE_FUTURES,
        "/fapi/v1/klines",
        {"symbol": symbol_clean, "interval": interval, "limit": limit},
    )
    if not isinstance(data, list):
        raise RuntimeError(f"Klines {interval} trả về không hợp lệ")
    return data


def fetch_ticker_24h(symbol_clean: str) -> dict:
    data = _http_get(BASE_FUTURES, "/fapi/v1/ticker/24hr", {"symbol": symbol_clean})
    if not isinstance(data, dict):
        raise RuntimeError("ticker/24hr không hợp lệ")
    return data


def fetch_all_tickers_24h() -> dict:
    """
    GET /fapi/v1/ticker/24hr (toàn bộ) — lọc top tăng/giảm.
    Key giống CCXT: BTC/USDT:USDT → {last, percentage, quoteVolume}.
    """
    rows = _http_get(BASE_FUTURES, "/fapi/v1/ticker/24hr")
    if not isinstance(rows, list):
        raise RuntimeError("ticker/24hr all không hợp lệ")
    out: dict = {}
    for t in rows:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        base = sym[:-4]
        key = f"{base}/USDT:USDT"
        try:
            out[key] = {
                "last": float(t["lastPrice"]),
                "percentage": float(t["priceChangePercent"]),
                "quoteVolume": float(t.get("quoteVolume", 0)),
            }
        except (KeyError, TypeError, ValueError):
            continue
    return out


def parse_ohlcv(rows: List[list]) -> dict:
    """CCXT/Binance kline: 0 time, 1 O, 2 H, 3 L, 4 C, 5 base vol, 7 quote vol."""
    o, h, l, c, bv, qv = [], [], [], [], [], []
    for row in rows:
        o.append(float(row[1]))
        h.append(float(row[2]))
        l.append(float(row[3]))
        c.append(float(row[4]))
        bv.append(float(row[5]))
        qv.append(float(row[7]) if len(row) > 7 else float(row[5]) * float(row[4]))
    return {"open": o, "high": h, "low": l, "close": c, "base_vol": bv, "quote_vol": qv}


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def bb_upper_lower(closes: List[float], period: int = 20, mult: float = 2.0) -> Tuple[Optional[float], Optional[float]]:
    if len(closes) < period:
        return None, None
    window = closes[-period:]
    ma = _mean(window)
    var = sum((x - ma) ** 2 for x in window) / period
    std = math.sqrt(var)
    return ma + mult * std, ma - mult * std


def rsi_series_sma(closes: List[float], period: int = 14) -> List[Optional[float]]:
    """Chuỗi RSI kiểu mẫu chatbot: SMA gain/loss rolling(period) trên từng cửa sổ."""
    n = len(closes)
    out: List[Optional[float]] = [None] * n
    if n < period + 1:
        return out
    for i in range(period, n):
        chunk = [closes[j] - closes[j - 1] for j in range(i - period + 1, i + 1)]
        gains = [max(0.0, x) for x in chunk]
        losses = [max(0.0, -x) for x in chunk]
        ag = _mean(gains)
        al = _mean(losses)
        out[i] = 100.0 if al == 0 else 100.0 - (100.0 / (1.0 + ag / al))
    return out


def rsi_sma_last(closes: List[float], period: int = 14) -> Optional[float]:
    series = rsi_series_sma(closes, period)
    for v in reversed(series):
        if v is not None:
            return float(v)
    return None


def _ewm_pandas(values: List[float], span: int) -> List[float]:
    """pandas.Series.ewm(span=span, adjust=False)"""
    if not values:
        return []
    alpha = 2.0 / (span + 1)
    out = [float(values[0])]
    for i in range(1, len(values)):
        out.append(float(values[i]) * alpha + out[-1] * (1.0 - alpha))
    return out


def compute_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD mẫu chatbot: ema12 - ema26, signal = ewm9(macd), adjust=False."""
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = _ewm_pandas(closes, fast)
    ema_slow = _ewm_pandas(closes, slow)
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
    sig_line = _ewm_pandas(macd_line, signal)
    m, s = macd_line[-1], sig_line[-1]
    return m, s, m - s


def compute_stoch_rsi(closes: List[float], rsi_period: int = 14, stoch_period: int = 14, k_smooth: int = 3, d_smooth: int = 3):
    """Stoch RSI mẫu chatbot: RSI SMA rolling → stoch → SMA k → SMA d."""
    rsi_arr = rsi_series_sma(closes, rsi_period)
    rsi_clean = [float(x) for x in rsi_arr if x is not None]
    if len(rsi_clean) < stoch_period + k_smooth + d_smooth - 2:
        return None, None
    raw_k: List[Optional[float]] = []
    for i in range(len(rsi_clean)):
        if i < stoch_period - 1:
            raw_k.append(None)
            continue
        window = rsi_clean[i - stoch_period + 1 : i + 1]
        w_min, w_max = min(window), max(window)
        raw_k.append(0.0 if w_max == w_min else (rsi_clean[i] - w_min) / (w_max - w_min) * 100.0)
    k_smoothed: List[Optional[float]] = []
    for i in range(len(raw_k)):
        if raw_k[i] is None or i < k_smooth - 1:
            k_smoothed.append(None)
        else:
            win = [raw_k[j] for j in range(i - k_smooth + 1, i + 1) if raw_k[j] is not None]
            k_smoothed.append(_mean(win) if len(win) == k_smooth else None)
    k_vals = [x for x in k_smoothed if x is not None]
    if len(k_vals) < d_smooth:
        return None, None
    k_now = k_vals[-1]
    d_now = _mean(k_vals[-d_smooth:])
    return k_now, d_now


def compute_stochastic(highs: List[float], lows: List[float], closes: List[float], k_period: int = 14, d_period: int = 3):
    n = min(len(highs), len(lows), len(closes))
    if n < k_period + d_period:
        return None, None
    k_series = []
    for i in range(k_period - 1, n):
        wh = highs[i - k_period + 1 : i + 1]
        wl = lows[i - k_period + 1 : i + 1]
        h_max, l_min = max(wh), min(wl)
        k_series.append(0.0 if h_max == l_min else (closes[i] - l_min) / (h_max - l_min) * 100)
    if len(k_series) < d_period:
        return None, None
    return k_series[-1], _mean(k_series[-d_period:])


def sma_last(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return _mean(values[-period:])


def max_body_pct_4h(rows: List[list], lookback: int) -> Tuple[Optional[float], Optional[float]]:
    if len(rows) < 2:
        return None, None
    subset = rows[-lookback:] if len(rows) >= lookback else rows
    pcts = []
    for row in subset:
        op, cl = float(row[1]), float(row[4])
        if op > 0:
            pcts.append((cl - op) / op * 100)
    if not pcts:
        return None, None
    return max(pcts), min(pcts)


def compute_score(price, ma7, ma25, ma99, macd_val, macd_sig, macd_hist, stoch_k, stoch_d, lsr_acc, lsr_pos, oi_delta):
    score = 0.0
    reasons = []
    if ma7 is not None and ma25 is not None and ma99 is not None:
        if ma7 > ma25 > ma99:
            score += 3
            reasons.append("MA7>25>99(+3)")
        elif ma7 < ma25 < ma99:
            score -= 3
            reasons.append("MA7<25<99(-3)")
    if price and ma25:
        if price > ma25:
            score += 1
            reasons.append("P>MA25(+1)")
        elif price < ma25:
            score -= 1
            reasons.append("P<MA25(-1)")
    if macd_val is not None and macd_sig is not None:
        if macd_val > macd_sig and (macd_hist or 0) > 0:
            score += 2
            reasons.append("MACD>Sig(+2)")
        elif macd_val < macd_sig and (macd_hist or 0) < 0:
            score -= 2
            reasons.append("MACD<Sig(-2)")
    if stoch_k is not None:
        if stoch_k < 20 and (stoch_d is None or stoch_k > stoch_d):
            score += 1.5
            reasons.append("StochRSI<20(+1.5)")
        elif stoch_k > 80 and (stoch_d is None or stoch_k < stoch_d):
            score -= 1.5
            reasons.append("StochRSI>80(-1.5)")
    if lsr_acc is not None and lsr_acc > 3:
        score -= 1
        reasons.append(f"LSR_acc={lsr_acc:.2f}(-1)")
    if lsr_pos is not None and lsr_pos > 2:
        score += 1.5
        reasons.append(f"LSR_pos={lsr_pos:.2f}(+1.5)")
    score = max(-10, min(10, round(score, 1)))
    if score >= 5:
        suggest = "LONG mạnh"
    elif score >= 2:
        suggest = "LONG nhẹ"
    elif score <= -5:
        suggest = "SHORT mạnh"
    elif score <= -2:
        suggest = "SHORT nhẹ"
    else:
        suggest = "Trung tính"
    return score, suggest, "; ".join(reasons)


def fetch_oi_usdt_and_delta(symbol_clean: str, price: float) -> Tuple[Optional[float], Optional[float]]:
    """OI USDT = openInterest×giá; Δ24h từ openInterestHist limit=24 (mẫu chatbot)."""
    oi_usdt = None
    oi_data = _http_get(BASE_FUTURES, "/fapi/v1/openInterest", {"symbol": symbol_clean})
    if oi_data and price:
        try:
            oi_usdt = float(oi_data["openInterest"]) * price
        except (KeyError, TypeError, ValueError):
            pass
    hist = _http_get(
        BASE_FUTURES,
        "/futures/data/openInterestHist",
        {"symbol": symbol_clean, "period": "1h", "limit": 24},
    )
    oi_delta = None
    if isinstance(hist, list) and len(hist) >= 2:
        try:
            oi_now = float(hist[-1]["sumOpenInterest"])
            oi_old = float(hist[0]["sumOpenInterest"])
            if oi_old > 0:
                oi_delta = (oi_now - oi_old) / oi_old * 100
        except (KeyError, TypeError, ValueError):
            pass
    return oi_usdt, oi_delta


def fetch_ls_ratio(symbol_clean: str, period: str = "5m") -> Tuple[Optional[float], Optional[float]]:
    acc = _http_get(
        BASE_FUTURES,
        "/futures/data/globalLongShortAccountRatio",
        {"symbol": symbol_clean, "period": period, "limit": 1},
    )
    pos = _http_get(
        BASE_FUTURES,
        "/futures/data/topLongShortPositionRatio",
        {"symbol": symbol_clean, "period": period, "limit": 1},
    )
    lsr_acc = float(acc[0]["longShortRatio"]) if isinstance(acc, list) and acc else None
    lsr_pos = float(pos[0]["longShortRatio"]) if isinstance(pos, list) and pos else None
    return lsr_acc, lsr_pos


def build_symbol_data(
    symbol_clean: str,
    pair_display: str,
    use_closed_candle: bool = False,
) -> List[Any]:
    """
    Thu thập chỉ số một mã qua Binance REST (symbol_data_fetch / feedback khách).
    Trả về list cột A→BF.
    """
    fut_status = validate_futures_symbol(symbol_clean)
    spot_status = get_spot_status(symbol_clean)

    ticker = fetch_ticker_24h(symbol_clean)
    price = float(ticker["lastPrice"])
    pct24 = float(ticker["priceChangePercent"])
    vol24 = float(ticker.get("quoteVolume", 0))

    k1h = fetch_klines(symbol_clean, "1h", 200)
    k4h = fetch_klines(symbol_clean, "4h", 200)
    k1d = fetch_klines(symbol_clean, "1d", 60)
    k1w = fetch_klines(symbol_clean, "1w", 20)

    o1 = parse_ohlcv(k1h)
    o4 = parse_ohlcv(k4h)
    o1d = parse_ohlcv(k1d)
    o1w = parse_ohlcv(k1w)

    def slice_closed(ohlc: dict) -> dict:
        if not use_closed_candle or len(ohlc["close"]) < 2:
            return ohlc
        return {k: v[:-1] for k, v in ohlc.items()}

    o1_ind = slice_closed(o1)
    closes_1h = o1_ind["close"]
    highs_1h = o1_ind["high"]
    lows_1h = o1_ind["low"]

    bb1_u, bb1_l = bb_upper_lower(closes_1h)
    bb4_u, bb4_l = bb_upper_lower(o4["close"])
    bb1d_u, bb1d_l = bb_upper_lower(o1d["close"])
    bb1w_u, bb1w_l = bb_upper_lower(o1w["close"])

    # Vol 1h/4h mẫu chatbot: volume(nến cuối) × lastPrice; MA20 = mean(volume 20 nến) × price
    idx_last = -2 if use_closed_candle and len(o1["base_vol"]) >= 2 else -1
    vol_1h = float(o1["base_vol"][idx_last]) * price
    vol_4h = float(o4["base_vol"][idx_last]) * price if o4["base_vol"] else 0.0
    vol_window = o1["base_vol"][max(0, len(o1["base_vol"]) - 20) :]
    if use_closed_candle and len(vol_window) > 1:
        vol_window = vol_window[:-1]
    vol_ma20 = _mean(vol_window) * price if vol_window else None
    vol_ratio = (vol_1h / vol_ma20) if vol_ma20 and vol_ma20 > 0 else None

    # Max/min 40 ngày
    d40 = o1d["high"][-40:]
    l40 = o1d["low"][-40:]
    max40 = max(d40) if d40 else None
    min40 = min(l40) if l40 else None

    max_up_4h, max_dn_4h = max_body_pct_4h(k4h, lookback=min(360, len(k4h)))

    # RSI mẫu chatbot (calc_rsi SMA rolling) — U: 1d, AH: 4h
    rsi_1d = rsi_sma_last(o1d["close"])
    rsi_4h = rsi_sma_last(o4["close"])

    ma7 = sma_last(closes_1h, 7)
    ma25 = sma_last(closes_1h, 25)
    ma99 = sma_last(closes_1h, 99)
    macd_v, macd_s, macd_h = compute_macd(closes_1h)
    stoch_rsi_k, stoch_rsi_d = compute_stoch_rsi(closes_1h)
    stoch_k, stoch_d = compute_stochastic(highs_1h, lows_1h, closes_1h)

    oi_usdt, oi_delta = fetch_oi_usdt_and_delta(symbol_clean, price)
    # Sheet AV/AW: period 5m theo hướng dẫn khách (globalLongShortAccountRatio / topLongShortPositionRatio)
    lsr_acc_sheet, lsr_pos_sheet = fetch_ls_ratio(symbol_clean, "5m")
    lsr_acc_score, lsr_pos_score = fetch_ls_ratio(symbol_clean, "1h")

    dist_bb_up = ((bb1_u - price) / price * 100) if bb1_u and price else None
    dist_bb_dn = ((price - bb1_l) / price * 100) if bb1_l and price else None

    score, suggest, reasons = compute_score(
        price, ma7, ma25, ma99, macd_v, macd_s, macd_h,
        stoch_rsi_k, stoch_rsi_d, lsr_acc_score, lsr_pos_score, oi_delta,
    )

    recent_h = max(o1["high"][-24:]) if len(o1["high"]) >= 24 else max(o1["high"])
    recent_l = min(o1["low"][-24:]) if len(o1["low"]) >= 24 else min(o1["low"])
    open_1h = o1["open"][idx_last]

    row = [
        pair_display,
        round(pct24, 3),
        round(price, 8),
        bb1_u, bb1_l, bb4_u, bb4_l, bb1d_u, bb1d_l,
        "", "",  # J-K biên độ tuần (cần logic riêng, để trống hoặc tính sau)
        max40, min40,
        max_up_4h, max_dn_4h,
        bb1w_u, bb1w_l,
        "", "",  # R-S biên độ 30d
        vol24,
        rsi_1d,
        "",
        round(bb1w_l / min40, 4) if bb1w_l and min40 else "",
        f"{dist_bb_up:.2f}%" if dist_bb_up is not None else "",
        f"{dist_bb_dn:.2f}%" if dist_bb_dn is not None else "",
        round(vol_1h, 2),
        round(vol_4h, 2),
        fut_status,
        spot_status,
        "", "",  # AD-AE
        "", "",  # AF-AG BB width
        round(rsi_4h, 2) if rsi_4h is not None else "",
        round(vol_1h, 2),
        round(vol_ma20, 2) if vol_ma20 else "",
        "",  # AK delist
        ma7, ma25, ma99,
        macd_v, macd_s, macd_h,
        stoch_rsi_k, stoch_rsi_d,
        oi_usdt, oi_delta,
        lsr_acc_sheet, lsr_pos_sheet,
        round(vol_ratio, 2) if vol_ratio else "",
        score, suggest, reasons,
        open_1h, recent_h, recent_l,
        stoch_k, stoch_d,
    ]
    return row


def _normalize_pair_for_sheet(symbol: str) -> str:
    return str(symbol or "").replace(":USDT", "").upper()


def _dedupe_symbols_by_normalized_pair(symbols, tickers):
    chosen: dict = {}
    for s in symbols:
        key = _normalize_pair_for_sheet(s)
        if not key:
            continue
        prev = chosen.get(key)
        if prev is None:
            chosen[key] = s
            continue
        if (":USDT" in s) and (":USDT" not in prev):
            chosen[key] = s
            continue
        try:
            prev_vol = float(tickers.get(prev, {}).get("quoteVolume") or 0)
            cur_vol = float(tickers.get(s, {}).get("quoteVolume") or 0)
            if cur_vol > prev_vol:
                chosen[key] = s
        except Exception:
            pass
    return list(chosen.values())


def get_row_result(symbol: str, tickers: dict) -> List[Any]:
    """Một dòng A→BF — chỉ báo từ Binance REST (không CCXT)."""
    pair = symbol.replace(":USDT", "")
    symbol_clean = pair.replace("/", "")
    if float(tickers.get(symbol, {}).get("last") or 0) <= 0:
        empty = [""] * SHEET_NUM_COLUMNS
        empty[0] = pair
        empty[1] = tickers.get(symbol, {}).get("percentage", "")
        return empty
    try:
        row = build_symbol_data(symbol_clean, pair)
        print(
            f"🔄 [NEW/REST] {pair} — %24h: {row[1]}, giá: {row[2]}",
            flush=True,
        )
        time.sleep(0.12)  # tránh vượt rate limit REST khi quét ~100 mã
        return row
    except Exception as e:
        logger.warning(f"[{symbol}] lỗi build_symbol_data: {e}", exc_info=True)
        empty = [""] * SHEET_NUM_COLUMNS
        empty[0] = pair
        return empty


def _header_row() -> List[str]:
    return list(COL_NAMES)


def do_it():
    tab_name = gg_sheet_factory.tab_list_all_ma_new
    print(f"\n{'='*80}", flush=True)
    print(f"🚀 CẬP NHẬT SHEET NEW 100 MÃ — {datetime.now():%Y-%m-%d %H:%M:%S}", flush=True)
    print(f"   Tab: {tab_name}", flush=True)
    print(f"{'='*80}\n", flush=True)
    logger.info(f"Bắt đầu cập nhật tab: {tab_name}")
    start_time = time.time()

    print("📡 Lấy ticker 24h toàn sàn (Binance REST /fapi/v1/ticker/24hr)...", flush=True)
    tickers = fetch_all_tickers_24h()
    print(f"✅ Đã lấy {len(tickers)} mã USDT futures từ REST", flush=True)

    all_futures_usdt = [
        s for s in tickers
        if "/USDT" in s and "-" not in s and tickers[s].get("percentage") is not None
    ]
    try:
        white_list = set(gg_sheet_factory.get_white_list())
    except Exception as e:
        logger.warning(f"Whitelist: {e}")
        white_list = set()

    if white_list:
        futures_symbols = [s for s in all_futures_usdt if s in white_list]
        if not futures_symbols:
            futures_symbols = all_futures_usdt
    else:
        futures_symbols = all_futures_usdt

    futures_symbols = [
        s for s in futures_symbols
        if (tickers[s].get("quoteVolume") or 0) >= 100_000
        and (tickers[s].get("last") or 0) > 0
    ]
    futures_symbols = _dedupe_symbols_by_normalized_pair(futures_symbols, tickers)

    title1 = f"Top {cst.top_count} có % giảm giá nhiều nhất trong 24h"
    title2 = f"Top {cst.top_count} có % tăng giá nhiều nhất trong 24h"
    empty_row = [""] * SHEET_NUM_COLUMNS
    tab_rows: List[List[Any]] = []

    for fixed_sym in SHEET_LEADER_SYMBOLS:
        if fixed_sym in tickers:
            tab_rows.append(get_row_result(fixed_sym, tickers))
        else:
            tab_rows.append(empty_row)

    excluded = set(SHEET_LEADER_SYMBOLS)
    giam_symbols = [s for s in futures_symbols if tickers[s]["percentage"] < 0 and s not in excluded]
    tang_symbols = [s for s in futures_symbols if tickers[s]["percentage"] > 0 and s not in excluded]
    list_giam = sorted(giam_symbols, key=lambda x: tickers[x]["percentage"])[: cst.top_count]
    list_tang = sorted(tang_symbols, key=lambda x: tickers[x]["percentage"], reverse=True)[: cst.top_count]

    tab_rows.append([title1] + [""] * (SHEET_NUM_COLUMNS - 1))
    giam_data = []
    for idx, sym in enumerate(list_giam, 1):
        print(f"📉 [{idx}/{len(list_giam)}] {sym}", flush=True)
        giam_data.append(get_row_result(sym, tickers))
        if is_test_mode:
            break
    tab_rows.extend(giam_data)
    for _ in range(max(0, cst.top_count - len(giam_data))):
        tab_rows.append(empty_row)

    tab_rows.append([title2] + [""] * (SHEET_NUM_COLUMNS - 1))
    tang_data = []
    for idx, sym in enumerate(list_tang, 1):
        if is_test_mode:
            break
        print(f"📈 [{idx}/{len(list_tang)}] {sym}", flush=True)
        tang_data.append(get_row_result(sym, tickers))
    tab_rows.extend(tang_data)
    for _ in range(max(0, cst.top_count - len(tang_data))):
        tab_rows.append(empty_row)

    try:
        balance = exchange.fetch_balance()
        total_margin = round(float(balance["info"]["totalMarginBalance"]), 4)
        total_wallet = round(float(balance["info"]["totalWalletBalance"]), 4)
        total_pnl = round(float(balance["info"]["totalCrossUnPnl"]), 4)
    except Exception as e:
        logger.warning(f"fetch_balance: {e}")
        total_margin = total_wallet = total_pnl = ""

    account_row = [["Số dư margin/ví/pnl", total_margin, total_wallet, total_pnl]]
    sheet_data = [_header_row()] + account_row + tab_rows

    print(f"💾 Ghi {len(sheet_data)} dòng → '{tab_name}'...", flush=True)
    gg_sheet_factory.update_multi(tab_name, -1, sheet_data, "A")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    gg_sheet_factory.update_single_value(tab_name, "A1", ts)

    elapsed = time.time() - start_time
    print(f"✅ Hoàn tất NEW sheet trong {elapsed:.1f}s | A1={ts}", flush=True)
    logger.info(f"Hoàn tất tab {tab_name} — {elapsed:.1f}s")


gg_sheet_factory.init_sheet_api()

print("\n" + "=" * 80, flush=True)
print("  HD_UPDATE_ALL_NEW — Sheet đối chiếu (Binance REST, symbol_data_fetch)", flush=True)
print(f"  Tab mới: {gg_sheet_factory.tab_list_all_ma_new}", flush=True)
print(f"  Bot cũ: {gg_sheet_factory.tab_list_all_ma} (hd_update_all.py)", flush=True)
print(f"  Log: {log_filename}", flush=True)
print("=" * 80 + "\n", flush=True)

while True:
    try:
        do_it()
    except Exception as e:
        print(f"❌ Tổng lỗi: {e}", flush=True)
        logger.error(f"Tổng lỗi: {e}", exc_info=True)
    if is_test_mode:
        break
    print(f"\n⏳ Chờ {cst.delay_update_all}s...\n", flush=True)
    time.sleep(cst.delay_update_all)
