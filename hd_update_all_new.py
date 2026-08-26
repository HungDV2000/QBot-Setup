#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cập nhật sheet "New 100 mã (50 tăng và 50 giảm)" — cùng cấu trúc hàng với hd_update_all.

Logic lấy số liệu: module binance_symbol_row (Binance REST, dùng chung với hd_update_all.py).

Chạy: python hd_update_all_new.py
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, List

import ccxt
import cst
import gg_sheet_factory

from binance_symbol_row import (
    build_symbol_data,
    fetch_all_tickers_24h,
    preload_exchange_caches,
)

file_name = os.path.basename(os.path.abspath(__file__))
os.system(f"title {file_name} - {cst.key_name}")

logs_dir = cst.account_dir('logs')  # [MULTI-ACC] tách theo tài khoản
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
SHEET_LEADER_SYMBOLS = ("BTCDOM/USDT:USDT", "BTC/USDT:USDT")

COL_NAMES = [
    "Mã", "% 24h", "Giá trị hiện thời", "BB1h trên", "BB1h dưới", "BB4h trên", "BB4h dưới",
    "BB1 ngày trên", "BB1 ngày dưới", "Biên độ 1h max tăng tuần", "Biên độ 1h max giảm tuần",
    "Max 40 ngày", "Min 40 ngày", "Max tăng 4h/60 ngày", "Max giảm 4h/60 ngày",
    "Giá Cao Nhất (BB1w trên)", "Giá Thấp Nhất (BB1w dưới)", "Biên độ 30d tăng", "Biên độ 30d giảm",
    "Volume 24h", "RSI 14", "(trống V)", "Min/Min40 (BB1w dưới / Min40)", "% đến BB1h trên",
    "% đến BB1h dưới", "Vol 1h", "Vol 4h", "Futures (trạng thái)", "Spot (trạng thái)",
    "Biên độ giá ngày lớn nhất (%)", "Ngày biên độ lớn nhất", "BB width 1d (3 ngày trước)",
    "BB width 1d (hiện tại)", "RSI 14 (4h)", "Vol 1h (hiện tại)", "Vol 1h MA20",
    "Cảnh báo delist sắp tới", "MA7 (1h)", "MA25 (1h)", "MA99 (1h)", "MACD (1h)",
    "MACD Signal (1h)", "MACD Hist (1h)", "Stoch RSI %K (1h)", "Stoch RSI %D (1h)",
    "Open Interest (USDT)", "OI Δ 24h (%)", "L/S Ratio (account)", "L/S Ratio (top traders)",
    "Vol 1h / MA20 (ratio)", "Score LONG/SHORT (-10..+10)", "Gợi ý", "Lý do score",
    "Open 1h", "High 1h gần đây", "Low 1h gần đây", "Stoch %K (1h)", "Stoch %D (1h)",
]
SHEET_NUM_COLUMNS = len(COL_NAMES)

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
    pair = symbol.replace(":USDT", "")
    symbol_clean = pair.replace("/", "")
    ti = tickers.get(symbol) or {}
    if float(ti.get("last") or 0) <= 0:
        empty = [""] * SHEET_NUM_COLUMNS
        empty[0] = pair
        empty[1] = ti.get("percentage", "")
        return empty
    t0 = time.time()
    print(f"   ⏳ REST {pair}...", flush=True)
    try:
        row = build_symbol_data(symbol_clean, pair, ticker_info=ti)
        elapsed = time.time() - t0
        print(f"🔄 [NEW/REST] {pair} — %24h: {row[1]}, giá: {row[2]} ({elapsed:.1f}s)", flush=True)
        time.sleep(0.05)
        return row
    except Exception as e:
        elapsed = time.time() - t0
        print(f"⚠️ {pair} lỗi sau {elapsed:.1f}s: {e}", flush=True)
        logger.warning(f"[{symbol}] build_symbol_data: {e}", exc_info=True)
        empty = [""] * SHEET_NUM_COLUMNS
        empty[0] = pair
        empty[1] = ti.get("percentage", "")
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

    print("📡 Lấy ticker 24h toàn sàn (Binance REST)...", flush=True)
    tickers = fetch_all_tickers_24h()
    print(f"✅ Đã lấy {len(tickers)} mã USDT futures từ REST", flush=True)

    print("📋 Tải cache exchangeInfo (1 lần)...", flush=True)
    preload_exchange_caches()

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


if __name__ == "__main__":
    gg_sheet_factory.init_sheet_api()

    print("\n" + "=" * 80, flush=True)
    print("  HD_UPDATE_ALL_NEW — Sheet đối chiếu (binance_symbol_row)", flush=True)
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
