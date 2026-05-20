#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot lấy dữ liệu chỉ báo 1 mã từ Binance Futures (public API) và ghi file TXT.

Mỗi lần chạy tạo file mới (không ghi đè / append):
  logs/data/{SYMBOL}_data_{dd_mm_yyyy_HH_MM_SS}.txt
Ví dụ: logs/data/BTCUSDT_data_20_05_2026_14_30_45.txt

Chạy:
  python symbol_data_fetch.py BTC
  python symbol_data_fetch.py "BTC/USDT" --closed-candle
  python symbol_data_fetch.py -s ETH,BNB,SOL
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_FUTURES = "https://fapi.binance.com"
BASE_SPOT = "https://api.binance.com"

LOGS_DIR = Path("logs") / "data"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

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
    if not values:
        return []
    alpha = 2.0 / (span + 1)
    out = [float(values[0])]
    for i in range(1, len(values)):
        out.append(float(values[i]) * alpha + out[-1] * (1.0 - alpha))
    return out


def compute_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9):
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = _ewm_pandas(closes, fast)
    ema_slow = _ewm_pandas(closes, slow)
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
    sig_line = _ewm_pandas(macd_line, signal)
    m, s = macd_line[-1], sig_line[-1]
    return m, s, m - s


def compute_stoch_rsi(closes: List[float], rsi_period: int = 14, stoch_period: int = 14, k_smooth: int = 3, d_smooth: int = 3):
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
    return k_vals[-1], _mean(k_vals[-d_smooth:])


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


def build_symbol_data(symbol_clean: str, pair_display: str, use_closed_candle: bool = False) -> Dict[str, Any]:
    """Thu thập toàn bộ chỉ số; trả về dict có key 'row' (list) và metadata."""
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

    idx_last = -2 if use_closed_candle and len(o1["base_vol"]) >= 2 else -1
    vol_1h = float(o1["base_vol"][idx_last]) * price
    vol_4h = float(o4["base_vol"][idx_last]) * price if o4["base_vol"] else 0.0
    vol_window = o1["base_vol"][max(0, len(o1["base_vol"]) - 20) :]
    if use_closed_candle and len(vol_window) > 1:
        vol_window = vol_window[:-1]
    vol_ma20 = _mean(vol_window) * price if vol_window else None
    vol_ratio = (vol_1h / vol_ma20) if vol_ma20 and vol_ma20 > 0 else None
    vol_1h_quote = o1["quote_vol"][idx_last]
    vol_1h_legacy = vol_1h

    # Max/min 40 ngày
    d40 = o1d["high"][-40:]
    l40 = o1d["low"][-40:]
    max40 = max(d40) if d40 else None
    min40 = min(l40) if l40 else None

    max_up_4h, max_dn_4h = max_body_pct_4h(k4h, lookback=min(360, len(k4h)))

    rsi_1d = rsi_sma_last(o1d["close"])
    rsi_4h = rsi_sma_last(o4["close"])

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
        lsr_acc_5m, lsr_pos_5m,
        round(vol_ratio, 2) if vol_ratio else "",
        score, suggest, reasons,
        open_1h, recent_h, recent_l,
        stoch_k, stoch_d,
    ]

    meta = {
        "symbol_binance": symbol_clean,
        "pair": pair_display,
        "use_closed_candle": use_closed_candle,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vol_1h_quote_forming": o1["quote_vol"][-1] if o1["quote_vol"] else None,
        "vol_1h_quote_closed": o1["quote_vol"][-2] if len(o1["quote_vol"]) >= 2 else None,
        "vol_1h_base_x_close": vol_1h_legacy,
        "lsr_account_5m": lsr_acc_5m,
        "lsr_position_5m": lsr_pos_5m,
        "stoch_rsi_k": stoch_rsi_k,
        "stoch_rsi_d": stoch_rsi_d,
        "stoch_classic_k": stoch_k,
        "stoch_classic_d": stoch_d,
        "note_stoch": "Chart TradingView 'Stochastic' thường khớp BE/BF, không phải AR/AS (Stoch RSI).",
    }
    return {"row": row, "meta": meta}


def _col_letter(idx: int) -> str:
    n = idx + 1
    letters = []
    while n:
        n, r = divmod(n - 1, 26)
        letters.append(chr(ord("A") + r))
    return "".join(reversed(letters))


def _fmt_value(value: Any) -> str:
    if value is None:
        return "(trống)"
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        return f"{value:,.8f}".rstrip("0").rstrip(".")
    if value == "":
        return "(trống)"
    return str(value)


def write_symbol_data_txt(symbol_clean: str, data: Dict[str, Any]) -> Path:
    """Ghi file mới mỗi lần gọi: {SYMBOL}_data_{dd_mm_yyyy_HH_MM_SS}.txt"""
    ts = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    filepath = LOGS_DIR / f"{symbol_clean}_data_{ts}.txt"
    row = data["row"]
    meta = data["meta"]

    lines = [
        "=" * 70,
        f"  {meta['pair']} ({symbol_clean})  —  {meta['fetched_at']}",
        f"  Nến chỉ báo: {'đã đóng (bỏ nến đang chạy)' if meta['use_closed_candle'] else 'gồm nến 1h đang chạy'}",
        "=" * 70,
        "",
        "--- Cột sheet A→BF (khớp hd_update_all) ---",
    ]
    for i, name in enumerate(COL_NAMES):
        val = row[i] if i < len(row) else ""
        lines.append(f"  {_col_letter(i):<3} | {name:<35} : {_fmt_value(val)}")

    lines.extend([
        "",
        "--- Đối chiếu feedback (Volume & Stochastic) ---",
        f"  Vol 1h quote (nến đang chạy)     : {_fmt_value(meta.get('vol_1h_quote_forming'))} USDT",
        f"  Vol 1h quote (nến vừa đóng)      : {_fmt_value(meta.get('vol_1h_quote_closed'))} USDT",
        f"  Vol 1h base×close (cách bot cũ)  : {_fmt_value(meta.get('vol_1h_base_x_close'))} USDT",
        f"  Stoch RSI %K / %D  (cột AR/AS)   : {_fmt_value(meta.get('stoch_rsi_k'))} / {_fmt_value(meta.get('stoch_rsi_d'))}",
        f"  Stochastic %K / %D (cột BE/BF)   : {_fmt_value(meta.get('stoch_classic_k'))} / {_fmt_value(meta.get('stoch_classic_d'))}",
        f"  L/S account 5m (hướng dẫn chatbot): {_fmt_value(meta.get('lsr_account_5m'))}",
        f"  L/S top pos 5m                   : {_fmt_value(meta.get('lsr_position_5m'))}",
        f"  Ghi chú                          : {meta.get('note_stoch', '')}",
        "",
    ])

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return filepath


def process_one(raw_symbol: str, use_closed_candle: bool = False) -> Path:
    symbol_clean, pair = normalize_symbol(raw_symbol)
    print(f"⏳ Đang lấy dữ liệu {pair} ({symbol_clean})...", flush=True)
    data = build_symbol_data(symbol_clean, pair, use_closed_candle=use_closed_candle)
    path = write_symbol_data_txt(symbol_clean, data)
    print(f"✅ Đã ghi: {path.resolve()}", flush=True)
    return path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lấy chỉ báo Binance Futures 1 mã và ghi file symbol_data_*.txt",
    )
    parser.add_argument(
        "symbol",
        nargs="?",
        help="Mã: BTC, BTCUSDT, BTC/USDT, BTC/USDT:USDT ...",
    )
    parser.add_argument(
        "-s", "--symbols",
        help="Nhiều mã, phân tách bởi dấu phẩy: BTC,ETH,SOL",
    )
    parser.add_argument(
        "--closed-candle",
        action="store_true",
        help="Chỉ báo 1h/4h dùng nến đã đóng (khớp TradingView khi bật 'chờ đóng nến')",
    )
    args = parser.parse_args(argv)

    symbols: List[str] = []
    if args.symbols:
        symbols.extend(x.strip() for x in args.symbols.split(",") if x.strip())
    if args.symbol:
        symbols.append(args.symbol.strip())
    if not symbols:
        parser.print_help()
        print("\nVí dụ: python symbol_data_fetch.py BTC", file=sys.stderr)
        return 1

    errors = 0
    for raw in symbols:
        try:
            symbol_clean, pair = normalize_symbol(raw)
            data = build_symbol_data(symbol_clean, pair, use_closed_candle=args.closed_candle)
            path = write_symbol_data_txt(symbol_clean, data)
            print(f"✅ {symbol_clean} → {path.resolve()}", flush=True)
        except (ValueError, urllib.error.URLError, RuntimeError) as e:
            errors += 1
            print(f"❌ {raw}: {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
