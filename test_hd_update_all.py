"""
Test HD Update All - Kiểm tra dữ liệu lấy từ Binance cho sheet "100 mã (50 tăng và 50 giảm)"
Bổ sung: Biên độ giá ngày lớn nhất trong lịch sử
Log kết quả vào: logs/test_hd_update_all_TIMESTAMP.txt
"""

import sys
import os
from datetime import datetime
from pathlib import Path
import ccxt
import pandas as pd
import numpy as np
from typing import Tuple, Dict, List
import time

# Import các modules của bot
import cst
import gg_sheet_factory
from data_collector import DataCollector, get_data_collector

# ============================================================================
# KHỞI TẠO LOGGING
# ============================================================================
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

log_timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
log_filename = logs_dir / f'test_hd_update_all_{log_timestamp}.txt'

class TestLogger:
    """Logger đơn giản để ghi cả console và file"""
    
    def __init__(self, filename):
        self.filename = filename
        self.file = open(filename, 'w', encoding='utf-8')
    
    def log(self, message):
        """Ghi log ra cả console và file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line, flush=True)
        self.file.write(log_line + '\n')
        self.file.flush()
    
    def separator(self, char='=', length=100):
        """Ghi dòng phân cách"""
        line = char * length
        print(line, flush=True)
        self.file.write(line + '\n')
        self.file.flush()
    
    def close(self):
        """Đóng file"""
        self.file.close()

# Khởi tạo logger
logger = TestLogger(log_filename)

# ============================================================================
# KHỞI TẠO EXCHANGE
# ============================================================================
def init_exchange():
    """Khởi tạo Binance exchange"""
    try:
        logger.log("🔧 Đang khởi tạo Binance exchange...")
        
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
        
        # Load markets
        exchange.load_markets(True)
        logger.log("✅ Khởi tạo exchange thành công!")
        
        return exchange
    except Exception as e:
        logger.log(f"❌ Lỗi khởi tạo exchange: {e}")
        return None

# ============================================================================
# TÍNH BIÊN ĐỘ GIÁ NGÀY LỚN NHẤT (MỚI)
# ============================================================================
def calculate_max_daily_volatility(
    exchange: ccxt.binance,
    symbol: str,
    lookback_days: int = 365
) -> Tuple[float, str, float, float, float]:
    """
    Tính biên độ giá ngày lớn nhất trong lịch sử
    
    Args:
        exchange: CCXT exchange instance
        symbol: Cặp giao dịch (VD: BTC/USDT:USDT)
        lookback_days: Số ngày nhìn lại (mặc định 365)
    
    Returns:
        Tuple (
            max_volatility_percent,  # Biên độ % lớn nhất
            max_volatility_date,     # Ngày có biên độ lớn nhất
            high_price,              # Giá cao nhất ngày đó
            low_price,               # Giá thấp nhất ngày đó
            open_price               # Giá mở cửa ngày đó
        )
    """
    try:
        # Lấy dữ liệu nến 1d
        now = exchange.milliseconds()
        start_time = now - (lookback_days * 24 * 60 * 60 * 1000)
        
        ohlcv = exchange.fetch_ohlcv(
            symbol,
            timeframe='1d',
            since=start_time,
            limit=lookback_days + 10
        )
        
        if not ohlcv or len(ohlcv) == 0:
            return 0.0, "N/A", 0.0, 0.0, 0.0
        
        # Chuyển sang DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Tính biên độ % = (High - Low) / Open * 100
        df['volatility_percent'] = ((df['high'] - df['low']) / df['open']) * 100
        
        # Tìm ngày có biên độ lớn nhất
        max_idx = df['volatility_percent'].idxmax()
        max_row = df.loc[max_idx]
        
        max_volatility = round(max_row['volatility_percent'], 2)
        max_date = datetime.fromtimestamp(max_row['timestamp'] / 1000).strftime('%Y-%m-%d')
        high_price = float(max_row['high'])
        low_price = float(max_row['low'])
        open_price = float(max_row['open'])
        
        return max_volatility, max_date, high_price, low_price, open_price
        
    except Exception as e:
        logger.log(f"   ⚠️  Lỗi tính biên độ giá: {e}")
        return 0.0, "ERROR", 0.0, 0.0, 0.0

# ============================================================================
# CÁC HÀM TỪ HD_UPDATE_ALL.PY (COPY)
# ============================================================================
def calculate_max_increase_decrease_4h(exchange, pair, timeframe='4h', days=60):
    """Tính biên độ tăng/giảm mạnh nhất 4h trong 60 ngày"""
    try:
        candles_per_day = 24 // 4
        length = days * candles_per_day
        
        ohlcv_data = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=length)
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['change_percent'] = (df['close'] - df['open']) / df['open'] * 100
        
        max_increase = round(df['change_percent'].max(), 2)
        max_decrease = round(df['change_percent'].min(), 2)
        
        return max_increase, max_decrease
    except Exception as e:
        logger.log(f"   ⚠️  Lỗi calculate_max_increase_decrease_4h: {e}")
        return 0.0, 0.0

def calculate_price_range(exchange, pair, num_days, timeframe):
    """Tính biên độ giá theo khung thời gian"""
    try:
        if timeframe == '15m':
            length = num_days * 24 * 60 / 15
        elif timeframe == '1h':
            length = num_days * 24
        elif timeframe == '1d':
            length = num_days
        
        length = int(length)
        ohlcv_data = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=length)
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['price_change'] = df['close'] - df['open']
        df['direction'] = df['price_change'].apply(lambda x: 'Tăng' if x > 0 else 'Giảm' if x < 0 else 'Đứng giá')
        max_price = df.apply(lambda row: max(row['close'], row['open']) if row['direction'] == 'Giảm' else min(row['close'], row['open']), axis=1)
        df['amplitude_percent'] = ((df['high'] - df['low']) / max_price) * 100
        
        amplitude_increase = df[df['direction'] == 'Tăng']['amplitude_percent'].max()
        amplitude_decrease = df[df['direction'] == 'Giảm']['amplitude_percent'].max()
        
        max_price_increase = round(amplitude_increase, 2) if not np.isnan(amplitude_increase) else 0.0
        max_price_decrease = round(amplitude_decrease, 2) if not np.isnan(amplitude_decrease) else 0.0
        
        return max_price_increase, max_price_decrease
    except Exception as e:
        logger.log(f"   ⚠️  Lỗi calculate_price_range: {e}")
        return 0.0, 0.0

def calculate_high_low_30d(exchange, pair, timeframe='1d', num_days=40):
    """Tính giá cao/thấp trong N ngày"""
    try:
        ohlcv_data = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=num_days)
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        highest_price = df['high'].max()
        lowest_price = df['low'].min()
        
        return highest_price, lowest_price
    except Exception as e:
        logger.log(f"   ⚠️  Lỗi calculate_high_low_30d: {e}")
        return 0.0, 0.0

def get_bb(exchange, pair, timeframes):
    """Tính Bollinger Bands"""
    try:
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
        
        return bb
    except Exception as e:
        logger.log(f"   ⚠️  Lỗi get_bb: {e}")
        return [0.0] * (len(timeframes) * 2)

# ============================================================================
# TEST 1: LẤY TOP 50 TĂNG VÀ GIẢM
# ============================================================================
def test_get_top_symbols(exchange):
    """Test lấy top 50 tăng và top 50 giảm"""
    logger.separator('=')
    logger.log("📊 TEST 1: LẤY TOP 50 TĂNG VÀ TOP 50 GIẢM")
    logger.separator('=')
    
    try:
        start_time = time.time()
        
        # Lấy tất cả tickers
        logger.log("\n1️⃣  Đang lấy tất cả tickers từ Binance...")
        tickers = exchange.fetch_tickers()
        logger.log(f"✅ Lấy được {len(tickers)} tickers")
        
        # Lọc symbols (BỎ QUA WHITELIST cho test - lấy tất cả mã)
        logger.log("\n2️⃣  Đang lọc symbols Futures USDT...")
        
        # Lấy tất cả futures USDT (KHÔNG DÙNG WHITELIST)
        futures_symbols = [
            symbol for symbol in tickers.keys()
            if '/USDT' in symbol 
            and "-" not in symbol
            and tickers[symbol].get('percentage') is not None
        ]
        logger.log(f"✅ Tổng số futures USDT trên Binance: {len(futures_symbols)}")
        logger.log(f"   💡 Test này BỎ QUA whitelist - lấy trực tiếp từ Binance")
        
        # Lấy top 50 giảm
        logger.log("\n3️⃣  Đang lấy top 50 giảm...")
        list_giam_nhieu_nhat = sorted(futures_symbols, key=lambda x: tickers[x]['percentage'])[:50]
        logger.log(f"✅ Top 50 giảm:")
        for i, symbol in enumerate(list_giam_nhieu_nhat[:5], 1):  # Log 5 mã đầu
            logger.log(f"   {i}. {symbol}: {tickers[symbol]['percentage']:.2f}%")
        logger.log(f"   ... (và {len(list_giam_nhieu_nhat) - 5} mã khác)")
        
        # Lấy top 50 tăng
        logger.log("\n4️⃣  Đang lấy top 50 tăng...")
        list_tang_nhieu_nhat = sorted(futures_symbols, reverse=True, key=lambda x: tickers[x]['percentage'])[:50]
        logger.log(f"✅ Top 50 tăng:")
        for i, symbol in enumerate(list_tang_nhieu_nhat[:5], 1):  # Log 5 mã đầu
            logger.log(f"   {i}. {symbol}: {tickers[symbol]['percentage']:.2f}%")
        logger.log(f"   ... (và {len(list_tang_nhieu_nhat) - 5} mã khác)")
        
        elapsed = time.time() - start_time
        logger.log(f"\n✅ Test 1 hoàn thành trong {elapsed:.2f}s")
        
        return tickers, list_giam_nhieu_nhat, list_tang_nhieu_nhat, True
        
    except Exception as e:
        logger.log(f"\n❌ Test 1 thất bại: {e}")
        import traceback
        logger.log(traceback.format_exc())
        return None, [], [], False

# ============================================================================
# TEST 2: TEST LẤY DỮ LIỆU CHO 1 SYMBOL
# ============================================================================
def test_get_symbol_data(exchange, symbol, tickers, data_collector):
    """Test lấy tất cả dữ liệu cho 1 symbol"""
    logger.separator('-')
    logger.log(f"\n📌 TEST SYMBOL: {symbol}")
    logger.separator('-')
    
    result = {}
    errors = []
    
    try:
        price = tickers[symbol]['last']
        percentage = tickers[symbol]['percentage']
        logger.log(f"   Giá: {price} USDT | % 24h: {percentage:.2f}%")
        
        pair = symbol.replace(":USDT", "")
        result['symbol'] = pair
        result['percentage'] = percentage
        result['price'] = price
        
        # A-C: Symbol, %, Giá
        logger.log(f"\n   Cột A-C: ✅")
        
        # D-G: BB 1h và 1d (4 cột)
        try:
            bb_1h_1d = get_bb(exchange, pair, timeframes=['1h', '1d'])
            result['bb_1h_upper'] = bb_1h_1d[0]
            result['bb_1h_lower'] = bb_1h_1d[1]
            result['bb_1d_upper'] = bb_1h_1d[2]
            result['bb_1d_lower'] = bb_1h_1d[3]
            logger.log(f"   Cột D-G (BB 1h, 1d): ✅")
        except Exception as e:
            errors.append(f"BB 1h/1d: {e}")
            logger.log(f"   Cột D-G: ❌ {e}")
        
        # H-I: Biên độ 1h max tăng/giảm tuần (7 ngày)
        try:
            max_inc_1h, max_dec_1h = calculate_price_range(exchange, pair, 7, '1h')
            result['max_inc_1h_7d'] = max_inc_1h
            result['max_dec_1h_7d'] = max_dec_1h
            logger.log(f"   Cột H-I (Biên độ 1h 7d): ✅ Tăng={max_inc_1h}%, Giảm={max_dec_1h}%")
        except Exception as e:
            errors.append(f"Biên độ 1h: {e}")
            logger.log(f"   Cột H-I: ❌ {e}")
        
        # J-K: Giá cao/thấp 40 ngày
        try:
            high_40d, low_40d = calculate_high_low_30d(exchange, symbol, num_days=40)
            result['high_40d'] = high_40d
            result['low_40d'] = low_40d
            logger.log(f"   Cột J-K (High/Low 40d): ✅ High={high_40d}, Low={low_40d}")
        except Exception as e:
            errors.append(f"High/Low 40d: {e}")
            logger.log(f"   Cột J-K: ❌ {e}")
        
        # L-M: Biên độ tăng/giảm 4h/60 ngày
        try:
            max_inc_4h, max_dec_4h = calculate_max_increase_decrease_4h(exchange, symbol)
            result['max_inc_4h_60d'] = max_inc_4h
            result['max_dec_4h_60d'] = max_dec_4h
            logger.log(f"   Cột L-M (Max change 4h 60d): ✅ Tăng={max_inc_4h}%, Giảm={max_dec_4h}%")
        except Exception as e:
            errors.append(f"Max change 4h: {e}")
            logger.log(f"   Cột L-M: ❌ {e}")
        
        # N-O: BB 1 tuần
        try:
            bb_1w = get_bb(exchange, pair, timeframes=['1w'])
            result['bb_1w_upper'] = bb_1w[0]
            result['bb_1w_lower'] = bb_1w[1]
            logger.log(f"   Cột N-O (BB 1w): ✅")
        except Exception as e:
            errors.append(f"BB 1w: {e}")
            logger.log(f"   Cột N-O: ❌ {e}")
        
        # P-Q: Biên độ 30 ngày
        try:
            max_inc_30d, max_dec_30d = calculate_price_range(exchange, pair, 30, '1d')
            result['max_inc_30d'] = max_inc_30d
            result['max_dec_30d'] = max_dec_30d
            logger.log(f"   Cột P-Q (Biên độ 30d): ✅ Tăng={max_inc_30d}%, Giảm={max_dec_30d}%")
        except Exception as e:
            errors.append(f"Biên độ 30d: {e}")
            logger.log(f"   Cột P-Q: ❌ {e}")
        
        # R-S: Volume 24h và RSI
        try:
            volume_24h = tickers[symbol].get('quoteVolume', 0)
            result['volume_24h'] = volume_24h
            
            # RSI 14
            ohlcv_rsi = exchange.fetch_ohlcv(pair, '1d', limit=15)
            closes = [x[4] for x in ohlcv_rsi]
            gains = []
            losses = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                gains.append(max(0, change))
                losses.append(max(0, -change))
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi = 100 - (100 / (1 + rs))
            result['rsi_14'] = round(rsi, 2)
            logger.log(f"   Cột R-S (Volume, RSI): ✅ Vol={volume_24h:,.0f}, RSI={rsi:.2f}")
        except Exception as e:
            errors.append(f"Volume/RSI: {e}")
            logger.log(f"   Cột R-S: ❌ {e}")
        
        # U: Ratio O/K
        try:
            if low_40d != 0:
                ratio_ok = round((bb_1w[1] / low_40d), 4)
                result['ratio_ok'] = ratio_ok
                logger.log(f"   Cột U (O/K ratio): ✅ {ratio_ok}")
            else:
                result['ratio_ok'] = 0
                logger.log(f"   Cột U: ⚠️  Low=0")
        except Exception as e:
            errors.append(f"Ratio O/K: {e}")
            logger.log(f"   Cột U: ❌ {e}")
        
        # V-W: Khoảng cách đến BB 1h
        try:
            distance_to_bb_up = round(((bb_1h_1d[0] - price) / price) * 100, 2) if price != 0 else 0
            distance_to_bb_down = round(((price - bb_1h_1d[1]) / price) * 100, 2) if price != 0 else 0
            result['distance_bb_up'] = distance_to_bb_up
            result['distance_bb_down'] = distance_to_bb_down
            logger.log(f"   Cột V-W (Distance BB): ✅ Up={distance_to_bb_up}%, Down={distance_to_bb_down}%")
        except Exception as e:
            errors.append(f"Distance BB: {e}")
            logger.log(f"   Cột V-W: ❌ {e}")
        
        # X-Y: Volume 1h và 4h
        try:
            vol_1h = data_collector.get_volumes_multi_timeframe(pair, timeframes=['1h']).get('1h', 0)
            vol_4h = data_collector.get_volumes_multi_timeframe(pair, timeframes=['4h']).get('4h', 0)
            result['vol_1h'] = vol_1h
            result['vol_4h'] = vol_4h
            logger.log(f"   Cột X-Y (Vol 1h, 4h): ✅ 1h={vol_1h:,.2f}, 4h={vol_4h:,.2f}")
        except Exception as e:
            errors.append(f"Vol 1h/4h: {e}")
            logger.log(f"   Cột X-Y: ❌ {e}")
        
        # 🆕 BIÊN ĐỘ GIÁ NGÀY LỚN NHẤT (Cột mới)
        try:
            max_vol, max_date, high_price, low_price, open_price = calculate_max_daily_volatility(
                exchange, symbol, lookback_days=365
            )
            result['max_daily_volatility'] = max_vol
            result['max_daily_volatility_date'] = max_date
            logger.log(f"   🆕 Cột mới (Biên độ giá ngày lớn nhất): ✅ {max_vol}% (ngày {max_date})")
        except Exception as e:
            errors.append(f"Max daily volatility: {e}")
            logger.log(f"   🆕 Cột mới: ❌ {e}")
        
        # Tổng kết
        if errors:
            logger.log(f"\n⚠️  Test {symbol}: PARTIAL ({len(errors)} lỗi)")
            for error in errors:
                logger.log(f"      - {error}")
        else:
            logger.log(f"\n✅ Test {symbol}: PASS (tất cả cột OK)")
        
        return result, len(errors) == 0
        
    except Exception as e:
        logger.log(f"\n❌ Test {symbol}: FAILED - {e}")
        import traceback
        logger.log(traceback.format_exc())
        return result, False

# ============================================================================
# TEST 3: TEST LẤY DỮ LIỆU CHO TẤT CẢ SYMBOLS
# ============================================================================
def test_get_all_symbols_data(exchange, tickers, list_giam, list_tang):
    """Test lấy dữ liệu cho tất cả symbols"""
    logger.separator('=')
    logger.log("📊 TEST 2: LẤY DỮ LIỆU CHO TẤT CẢ SYMBOLS")
    logger.separator('=')
    
    try:
        start_time = time.time()
        
        # Khởi tạo data collector
        data_collector = get_data_collector(exchange)
        
        # Test với 1 mã mẫu từ mỗi danh sách (để kiểm tra nhanh)
        test_symbols_giam = [list_giam[0]] if len(list_giam) > 0 else []
        test_symbols_tang = [list_tang[0]] if len(list_tang) > 0 else []
        
        logger.log(f"\n📝 Test với {len(test_symbols_giam)} mã giảm và {len(test_symbols_tang)} mã tăng")
        logger.log(f"   (Chỉ test 1 mã từ mỗi top để kiểm tra cấu trúc dữ liệu)")
        
        all_results = []
        success_count = 0
        fail_count = 0
        
        # Test mã giảm
        if test_symbols_giam:
            logger.log(f"\n📉 TESTING TOP GIẢM: {test_symbols_giam[0]}")
            for symbol in test_symbols_giam:
                result, success = test_get_symbol_data(exchange, symbol, tickers, data_collector)
                all_results.append(result)
                if success:
                    success_count += 1
                else:
                    fail_count += 1
        else:
            logger.log("\n📉 TESTING TOP GIẢM: Không có mã nào")
        
        # Test mã tăng
        if test_symbols_tang:
            logger.log(f"\n📈 TESTING TOP TĂNG: {test_symbols_tang[0]}")
            for symbol in test_symbols_tang:
                result, success = test_get_symbol_data(exchange, symbol, tickers, data_collector)
                all_results.append(result)
                if success:
                    success_count += 1
                else:
                    fail_count += 1
        else:
            logger.log("\n📈 TESTING TOP TĂNG: Không có mã nào")
        
        elapsed = time.time() - start_time
        
        # Tổng kết
        logger.separator('-')
        logger.log(f"\n📊 TỔNG KẾT TEST 2:")
        logger.log(f"   Tổng số symbols test: {success_count + fail_count}")
        logger.log(f"   ✅ Thành công: {success_count}")
        logger.log(f"   ❌ Thất bại: {fail_count}")
        logger.log(f"   ⏱️  Thời gian: {elapsed:.2f}s")
        if (success_count + fail_count) > 0:
            logger.log(f"   ⏱️  Trung bình: {elapsed/(success_count + fail_count):.2f}s/symbol")
        else:
            logger.log(f"   ⚠️  Không có symbol nào để test!")
        
        # Kiểm tra kết quả
        if success_count + fail_count == 0:
            logger.log(f"\n❌ Test 2: FAILED (Không có mã nào để test)")
            return False
        elif fail_count == 0:
            logger.log(f"\n✅ Test 2: PASS")
            return True
        else:
            logger.log(f"\n⚠️  Test 2: PARTIAL ({success_count}/{success_count + fail_count} passed)")
            return False
        
    except Exception as e:
        logger.log(f"\n❌ Test 2 thất bại: {e}")
        import traceback
        logger.log(traceback.format_exc())
        return False

# ============================================================================
# TEST 4: VALIDATION DỮ LIỆU
# ============================================================================
def test_data_validation(exchange, symbol, tickers):
    """Test validation dữ liệu cho 1 symbol"""
    logger.separator('=')
    logger.log(f"✅ TEST 3: VALIDATION DỮ LIỆU ({symbol})")
    logger.separator('=')
    
    try:
        data_collector = get_data_collector(exchange)
        pair = symbol.replace(":USDT", "")
        price = tickers[symbol]['last']
        
        validations = []
        
        # Validation 1: Giá > 0
        if price > 0:
            validations.append(("Giá > 0", True, f"{price}"))
            logger.log(f"✅ Validation 1: Giá > 0 ({price})")
        else:
            validations.append(("Giá > 0", False, f"{price}"))
            logger.log(f"❌ Validation 1: Giá <= 0 ({price})")
        
        # Validation 2: % 24h trong khoảng hợp lý [-50%, 100%]
        percentage = tickers[symbol]['percentage']
        if -50 <= percentage <= 100:
            validations.append(("% 24h hợp lý", True, f"{percentage:.2f}%"))
            logger.log(f"✅ Validation 2: % 24h hợp lý ({percentage:.2f}%)")
        else:
            validations.append(("% 24h hợp lý", False, f"{percentage:.2f}%"))
            logger.log(f"⚠️  Validation 2: % 24h bất thường ({percentage:.2f}%)")
        
        # Validation 3: BB upper > BB lower
        bb_1h_1d = get_bb(exchange, pair, timeframes=['1h'])
        if bb_1h_1d[0] > bb_1h_1d[1]:
            validations.append(("BB upper > lower", True, f"{bb_1h_1d[0]:.2f} > {bb_1h_1d[1]:.2f}"))
            logger.log(f"✅ Validation 3: BB upper > lower")
        else:
            validations.append(("BB upper > lower", False, f"{bb_1h_1d[0]:.2f} <= {bb_1h_1d[1]:.2f}"))
            logger.log(f"❌ Validation 3: BB không hợp lệ")
        
        # Validation 4: High > Low
        high_40d, low_40d = calculate_high_low_30d(exchange, symbol, num_days=40)
        if high_40d > low_40d > 0:
            validations.append(("High > Low", True, f"{high_40d} > {low_40d}"))
            logger.log(f"✅ Validation 4: High > Low")
        else:
            validations.append(("High > Low", False, f"{high_40d} <= {low_40d}"))
            logger.log(f"❌ Validation 4: High/Low không hợp lý")
        
        # Validation 5: Volume > 0
        volume_24h = tickers[symbol].get('quoteVolume', 0)
        if volume_24h > 0:
            validations.append(("Volume > 0", True, f"{volume_24h:,.0f}"))
            logger.log(f"✅ Validation 5: Volume > 0")
        else:
            validations.append(("Volume > 0", False, f"{volume_24h}"))
            logger.log(f"❌ Validation 5: Volume = 0")
        
        # Validation 6: Biên độ giá ngày lớn nhất > 0
        max_vol, max_date, _, _, _ = calculate_max_daily_volatility(exchange, symbol, 365)
        if max_vol > 0:
            validations.append(("Max daily volatility > 0", True, f"{max_vol}%"))
            logger.log(f"✅ Validation 6: Biên độ giá ngày lớn nhất > 0 ({max_vol}%)")
        else:
            validations.append(("Max daily volatility > 0", False, f"{max_vol}%"))
            logger.log(f"❌ Validation 6: Biên độ giá = 0")
        
        # Tổng kết
        passed = sum(1 for v in validations if v[1])
        total = len(validations)
        
        logger.separator('-')
        logger.log(f"\n📊 KẾT QUẢ VALIDATION:")
        logger.log(f"   Tổng: {total} validations")
        logger.log(f"   ✅ Passed: {passed}")
        logger.log(f"   ❌ Failed: {total - passed}")
        
        if passed == total:
            logger.log(f"\n✅ Test 3: PASS")
            return True
        else:
            logger.log(f"\n⚠️  Test 3: PARTIAL ({passed}/{total} passed)")
            return False
        
    except Exception as e:
        logger.log(f"\n❌ Test 3 thất bại: {e}")
        import traceback
        logger.log(traceback.format_exc())
        return False

# ============================================================================
# MAIN - CHẠY TẤT CẢ TESTS
# ============================================================================
def main():
    """Chạy tất cả tests"""
    logger.separator('=')
    logger.log("🚀 TEST HD_UPDATE_ALL - KIỂM TRA DỮ LIỆU SHEET 100 MÃ")
    logger.log(f"📅 Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.log(f"📝 Log file: {log_filename}")
    logger.separator('=')
    
    # Đếm tests
    results = {
        'total': 0,
        'passed': 0,
        'failed': 0
    }
    
    # Khởi tạo Google Sheets API
    try:
        logger.log("\n🔧 Đang khởi tạo Google Sheets API...")
        gg_sheet_factory.init_sheet_api()
        logger.log("✅ Google Sheets API đã sẵn sàng")
    except Exception as e:
        logger.log(f"❌ Lỗi khởi tạo Google Sheets API: {e}")
        logger.log("⚠️  Tiếp tục với các tests khác...")
    
    # Khởi tạo exchange
    exchange = init_exchange()
    if not exchange:
        logger.log("\n❌ Không thể khởi tạo exchange - Dừng tests!")
        logger.close()
        return
    
    # Test 1: Lấy top 50 tăng và giảm
    logger.log("\n")
    try:
        tickers, list_giam, list_tang, success = test_get_top_symbols(exchange)
        results['total'] += 1
        if success:
            results['passed'] += 1
        else:
            results['failed'] += 1
            logger.close()
            return
    except Exception as e:
        logger.log(f"❌ Test 1 crashed: {e}")
        results['total'] += 1
        results['failed'] += 1
        logger.close()
        return
    
    # Test 2: Lấy dữ liệu cho tất cả symbols
    logger.log("\n")
    try:
        success = test_get_all_symbols_data(exchange, tickers, list_giam, list_tang)
        results['total'] += 1
        if success:
            results['passed'] += 1
        else:
            results['failed'] += 1
    except Exception as e:
        logger.log(f"❌ Test 2 crashed: {e}")
        results['total'] += 1
        results['failed'] += 1
    
    # Test 3: Validation dữ liệu (dùng BTC làm mẫu)
    logger.log("\n")
    try:
        test_symbol = 'BTC/USDT:USDT'
        success = test_data_validation(exchange, test_symbol, tickers)
        results['total'] += 1
        if success:
            results['passed'] += 1
        else:
            results['failed'] += 1
    except Exception as e:
        logger.log(f"❌ Test 3 crashed: {e}")
        results['total'] += 1
        results['failed'] += 1
    
    # Tổng kết
    logger.log("\n")
    logger.separator('=')
    logger.log("🏁 TỔNG KẾT TEST SUITE")
    logger.separator('=')
    
    logger.log(f"\n📊 KẾT QUẢ:")
    logger.log(f"   Tổng số tests: {results['total']}")
    logger.log(f"   ✅ Passed: {results['passed']}")
    logger.log(f"   ❌ Failed: {results['failed']}")
    
    if results['failed'] == 0:
        logger.log("\n🎉 TẤT CẢ TESTS ĐỀU PASS!")
    else:
        logger.log(f"\n⚠️  CÓ {results['failed']} TEST(S) FAILED")
    
    logger.log(f"\n📝 Log chi tiết: {log_filename}")
    logger.log("\n💡 LƯU Ý:")
    logger.log("   - File này chỉ test logic lấy dữ liệu")
    logger.log("   - KHÔNG ghi dữ liệu vào Google Sheets")
    logger.log("   - Test BỎ QUA whitelist - lấy trực tiếp từ Binance")
    logger.log("   - Chỉ test 1 mã giảm + 1 mã tăng để kiểm tra nhanh")
    logger.log("   - Để chạy thật với whitelist: python hd_update_all.py")
    logger.separator('=')
    
    logger.close()
    print(f"\n✅ Hoàn tất! Xem log tại: {log_filename}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.log("\n\n⚠️  Người dùng dừng test (Ctrl+C)")
        logger.close()
        sys.exit(0)
    except Exception as e:
        logger.log(f"\n\n❌ LỖI NGHIÊM TRỌNG: {e}")
        import traceback
        logger.log(traceback.format_exc())
        logger.close()
        sys.exit(1)
