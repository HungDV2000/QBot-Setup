#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cập nhật sheet "New 100 mã (50 tăng và 50 giảm)" — cùng cấu trúc hàng/cột với hd_update_all,
logic chỉ báo mới (quote vol, Stoch RSI + Stochastic BE/BF, v.v.) để đối chiếu bot cũ.

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
SHEET_LEADER_SYMBOLS = ("BTC/USDT:USDT", "BTCDOM/USDT:USDT")

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


def fetch_klines_ccxt(pair: str, interval: str, limit: int) -> List[list]:
    rows = exchange.fetch_ohlcv(pair, interval, limit=limit)
    if not rows:
        return []
    out = []
    for row in rows:
        ts, o, h, l, c, v = row[0], float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])
        qv = v * c
        out.append([ts, o, h, l, c, v, ts, qv])
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


def rsi_wilder(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(0.0, x) for x in changes]
    losses = [max(0.0, -x) for x in changes]
    avg_g = _mean(gains[:period])
    avg_l = _mean(losses[:period])
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100.0 - (100.0 / (1.0 + rs))


def ema_series(values: List[float], period: int) -> List[Optional[float]]:
    if len(values) < period:
        return []
    k = 2.0 / (period + 1)
    out: List[Optional[float]] = [None] * len(values)
    seed = _mean(values[:period])
    out[period - 1] = seed
    for i in range(period, len(values)):
        out[i] = values[i] * k + out[i - 1] * (1 - k)
    return out


def compute_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9):
    if len(closes) < slow + signal:
        return None, None, None
    ef = ema_series(closes, fast)
    es = ema_series(closes, slow)
    macd_line: List[Optional[float]] = []
    for i in range(len(closes)):
        if ef[i] is None or es[i] is None:
            macd_line.append(None)
        else:
            macd_line.append(ef[i] - es[i])
    valid = [x for x in macd_line if x is not None]
    if len(valid) < signal:
        return None, None, None
    sig = ema_series(valid, signal)
    m, s = valid[-1], sig[-1]
    if s is None:
        return m, None, None
    return m, s, m - s


def compute_stoch_rsi(closes: List[float], rsi_period: int = 14, stoch_period: int = 14, k_smooth: int = 3, d_smooth: int = 3):
    min_len = rsi_period + stoch_period + k_smooth + d_smooth
    if len(closes) < min_len:
        return None, None
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(0.0, c) for c in changes]
    losses = [max(0.0, -c) for c in changes]
    rsi_series: List[Optional[float]] = [None] * len(closes)
    avg_g = _mean(gains[:rsi_period])
    avg_l = _mean(losses[:rsi_period])
    for i in range(rsi_period, len(gains) + 1):
        if i > rsi_period:
            avg_g = (avg_g * (rsi_period - 1) + gains[i - 1]) / rsi_period
            avg_l = (avg_l * (rsi_period - 1) + losses[i - 1]) / rsi_period
        rsi_series[i] = 100.0 if avg_l == 0 else 100 - (100 / (1 + avg_g / avg_l))
    rsi_clean = [x for x in rsi_series if x is not None]
    raw_k: List[Optional[float]] = []
    for i in range(len(rsi_clean)):
        if i < stoch_period - 1:
            raw_k.append(None)
            continue
        window = rsi_clean[i - stoch_period + 1 : i + 1]
        w_min, w_max = min(window), max(window)
        raw_k.append(0.0 if w_max == w_min else (rsi_clean[i] - w_min) / (w_max - w_min) * 100)
    k_valid = [x for x in raw_k if x is not None]
    if len(k_valid) < k_smooth + d_smooth:
        return None, None
    k_smoothed: List[Optional[float]] = []
    for i in range(len(k_valid)):
        if i < k_smooth - 1:
            k_smoothed.append(None)
        else:
            k_smoothed.append(_mean(k_valid[i - k_smooth + 1 : i + 1]))
    k_clean = [x for x in k_smoothed if x is not None]
    if len(k_clean) < d_smooth:
        return None, None
    return k_clean[-1], _mean(k_clean[-d_smooth:])


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


def fetch_ticker_24h(symbol_clean: str) -> dict:
    data = _http_get(BASE_FUTURES, "/fapi/v1/ticker/24hr", {"symbol": symbol_clean})
    if not isinstance(data, dict):
        raise RuntimeError("ticker/24hr không hợp lệ")
    return data


def fetch_oi_usdt_and_delta(symbol_clean: str, price: float) -> Tuple[Optional[float], Optional[float]]:
    hist = _http_get(
        BASE_FUTURES,
        "/futures/data/openInterestHist",
        {"symbol": symbol_clean, "period": "1h", "limit": 25},
    )
    if isinstance(hist, list) and len(hist) >= 2:
        try:
            oi_usdt = float(hist[-1].get("sumOpenInterestValue", 0))
            oi_old = float(hist[0].get("sumOpenInterestValue", 0))
            delta = ((oi_usdt - oi_old) / oi_old * 100) if oi_old > 0 else None
            return oi_usdt, delta
        except (TypeError, ValueError):
            pass
    oi_data = _http_get(BASE_FUTURES, "/fapi/v1/openInterest", {"symbol": symbol_clean})
    if oi_data and price:
        try:
            return float(oi_data["openInterest"]) * price, None
        except (KeyError, TypeError, ValueError):
            pass
    return None, None


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
    *,
    use_closed_candle: bool = False,
    price: Optional[float] = None,
    pct24: Optional[float] = None,
    vol24: Optional[float] = None,
    use_ccxt_klines: bool = True,
) -> List[Any]:
    """Thu thập chỉ số một mã — trả về list cột A→BF."""
    fut_status = validate_futures_symbol(symbol_clean)
    spot_status = get_spot_status(symbol_clean)

    if price is None or pct24 is None:
        ticker = fetch_ticker_24h(symbol_clean)
        price = float(ticker["lastPrice"])
        pct24 = float(ticker["priceChangePercent"])
        vol24 = float(ticker.get("quoteVolume", 0))
    else:
        vol24 = float(vol24 or 0)

    def _kl(interval: str, limit: int) -> List[list]:
        if use_ccxt_klines:
            return fetch_klines_ccxt(pair_display, interval, limit)
        return fetch_klines(symbol_clean, interval, limit)

    k1h = _kl("1h", 200)
    k4h = _kl("4h", 200)
    k1d = _kl("1d", 60)
    k1w = _kl("1w", 20)

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

    # Vol: nến cuối (forming) vs đã đóng
    idx_last = -2 if use_closed_candle and len(o1["quote_vol"]) >= 2 else -1
    vol_1h_quote = o1["quote_vol"][idx_last]
    vol_4h_quote = o4["quote_vol"][idx_last] if o4["quote_vol"] else 0
    vol_1h_legacy = o1["base_vol"][idx_last] * o1["close"][idx_last]

    vols_usdt_20 = [o1["quote_vol"][i] for i in range(max(0, len(o1["quote_vol"]) - 20), len(o1["quote_vol"]))]
    if use_closed_candle and len(vols_usdt_20) > 1:
        vols_usdt_20 = vols_usdt_20[:-1]
    vol_ma20 = _mean(vols_usdt_20) if vols_usdt_20 else None
    vol_ratio = (vol_1h_quote / vol_ma20) if vol_ma20 and vol_ma20 > 0 else None

    # Max/min 40 ngày
    d40 = o1d["high"][-40:]
    l40 = o1d["low"][-40:]
    max40 = max(d40) if d40 else None
    min40 = min(l40) if l40 else None

    max_up_4h, max_dn_4h = max_body_pct_4h(k4h, lookback=min(360, len(k4h)))

    # RSI
    closes_1d_rsi = o1d["close"][:-1] if len(o1d["close"]) > 15 else o1d["close"]
    rsi_1d = rsi_wilder(closes_1d_rsi)
    closes_4h_rsi = o4["close"][:-1] if len(o4["close"]) > 15 else o4["close"]
    rsi_4h = rsi_wilder(closes_4h_rsi)

    ma7 = sma_last(closes_1h, 7)
    ma25 = sma_last(closes_1h, 25)
    ma99 = sma_last(closes_1h, 99)
    macd_v, macd_s, macd_h = compute_macd(closes_1h)
    stoch_rsi_k, stoch_rsi_d = compute_stoch_rsi(closes_1h)
    stoch_k, stoch_d = compute_stochastic(highs_1h, lows_1h, closes_1h)

    oi_usdt, oi_delta = fetch_oi_usdt_and_delta(symbol_clean, price)
    lsr_acc_5m, lsr_pos_5m = fetch_ls_ratio(symbol_clean, "5m")
    lsr_acc_1h, lsr_pos_1h = fetch_ls_ratio(symbol_clean, "1h")

    dist_bb_up = ((bb1_u - price) / price * 100) if bb1_u and price else None
    dist_bb_dn = ((price - bb1_l) / price * 100) if bb1_l and price else None

    score, suggest, reasons = compute_score(
        price, ma7, ma25, ma99, macd_v, macd_s, macd_h,
        stoch_rsi_k, stoch_rsi_d, lsr_acc_1h, lsr_pos_1h, oi_delta,
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
        round(vol_1h_quote, 2),
        round(vol_4h_quote, 2),
        fut_status,
        spot_status,
        "", "",  # AD-AE
        "", "",  # AF-AG BB width
        round(rsi_4h, 2) if rsi_4h is not None else "",
        round(vol_1h_quote, 2),
        round(vol_ma20, 2) if vol_ma20 else "",
        "",  # AK delist
        ma7, ma25, ma99,
        macd_v, macd_s, macd_h,
        stoch_rsi_k, stoch_rsi_d,
        oi_usdt, oi_delta,
        lsr_acc_1h, lsr_pos_1h,
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
    """Một dòng A→BF cho symbol CCXT (vd BTC/USDT:USDT)."""
    pair = symbol.replace(":USDT", "")
    symbol_clean = pair.replace("/", "")
    price = float(tickers[symbol].get("last") or 0)
    pct = float(tickers[symbol].get("percentage") or 0)
    if price <= 0:
        empty = [""] * SHEET_NUM_COLUMNS
        empty[0] = pair
        empty[1] = pct
        return empty
    print(f"🔄 [NEW] {symbol} - %24h: {pct:.2f}%, giá: {price}", flush=True)
    return build_symbol_data(
        symbol_clean,
        pair,
        price=price,
        pct24=pct,
        vol24=float(tickers[symbol].get("quoteVolume") or 0),
        use_ccxt_klines=True,
    )


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

    tickers = exchange.fetch_tickers()
    print(f"✅ Đã lấy {len(tickers)} tickers", flush=True)

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
print("  HD_UPDATE_ALL_NEW — Sheet đối chiếu (logic chỉ báo mới)", flush=True)
print(f"  Tab: {gg_sheet_factory.tab_list_all_ma_new}", flush=True)
print(f"  Bot cũ: {gg_sheet_factory.tab_list_all_ma}", flush=True)
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
