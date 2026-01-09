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
from data_collector import DataCollector, get_data_collector

file_name = os.path.basename(os.path.abspath(__file__))  
os.system(f"title {file_name} - {cst.key_name}")

# Tạo thư mục logs/ nếu chưa có
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Chỉ log ERROR vào logs/error.log
logging.basicConfig(
    level=logging.ERROR,  # Chỉ log ERROR
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
# Thêm file handler cho error.log
error_log_path = logs_dir / 'error.log'
error_handler = logging.FileHandler(error_log_path, encoding='utf-8')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(error_handler)
is_test_mode = False

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
    

    

def do_it():
    print(f"-------------------------------start scan all: {datetime.now()}-------------------------------------", flush=True)
    start_time = time.time()

    # Fix: Khởi tạo data_collector ngay đầu hàm
    data_collector = get_data_collector(exchange)
    
    tickers = exchange.fetch_tickers()

    
    

    white_list = set(gg_sheet_factory.get_white_list())  
    print(f"Danh sách whitelist từ sheet (tổng {len(white_list)} mã):", flush=True)
    print(white_list, flush=True)
    
    # Fix: Lọc chỉ lấy các mã có trong whitelist VÀ đang được giao dịch trên Binance
    futures_symbols=  [
        symbol for symbol in tickers.keys()
        if '/USDT' in symbol 
        and "-" not in symbol
        and tickers[symbol].get('percentage') is not None
        and symbol in white_list  # Chỉ lấy mã có trong whitelist
    ]
    
    print(f"Số mã sau khi lọc whitelist: {len(futures_symbols)}", flush=True)

    



    
    
    
    
    
    
    
    


    

    
    

    def get_row_result(symbol):
        
        price = tickers[symbol]['last']

        print(symbol, tickers[symbol]['percentage'], price, flush=True)
        pair= symbol.replace(":USDT", "")
        row = [pair, tickers[symbol]['percentage'], price]
        
        # Bollinger Bands chỉ 2 khung: 1h và 1d (giống file cũ)
        result_bb_array = get_bb(pair,  timeframes = [ '1h', '1d'])
        row.extend(result_bb_array)  # D-G (4 cột)

        # Biên độ 1h max tăng/giảm tuần (7 ngày)
        max_price_increase_month1, max_price_decrease_month1 = calculate_price_range(pair, 7, '1h')
        
        max_price_increase_month1 = "" if np.isnan(max_price_increase_month1) else max_price_increase_month1
        max_price_decrease_month1 = "" if np.isnan(max_price_decrease_month1) else max_price_decrease_month1

        row.append(max_price_increase_month1)  # H
        row.append(max_price_decrease_month1)  # I

        # Giá cao/thấp 40 ngày (giống file cũ)
        high, low = calculate_high_low_30d(symbol)
        row.append(high)  # J
        row.append(low)   # K

        # Biên độ tăng/giảm 4h/60 ngày
        increase, decrease = calculate_max_increase_decrease_4h(symbol)
        row.append(increase)  # L
        row.append(decrease)  # M
        
        # Cột N-O: BB 1 tuần (thêm mới cho tất cả các mã)
        bb_1w = get_bb(pair, timeframes=['1w'])
        row.extend(bb_1w)  # N-O (2 cột)
        
        # Cột P-Q: Biên độ 30 ngày (thêm mới)
        bd = get_bien_do_max(pair)
        row.append(bd[4])  # P: Biên độ 30d tăng
        row.append(bd[5])  # Q: Biên độ 30d giảm
        
        # Cột R-S: Volume 24h và RSI (thêm mới)
        try:
            # Volume 24h từ ticker
            volume_24h = tickers[symbol].get('quoteVolume', 0)  # R
            row.append(volume_24h)
            
            # RSI 14 (tính từ 1d)
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
            row.append(round(rsi, 2))  # S: RSI
        except:
            row.extend([0, 0])  # R-S trống nếu lỗi
        
        # Cột T: Trống (dự phòng)
        row.append("")
            
        # Cột U: % vị trí trong range 40 ngày
        # Công thức: (Giá thấp nhất / Min 40 ngày)
        # Theo yêu cầu: U = O/K
        # O là Giá thấp nhất (BB1w lower ở cột O)
        # K là Min 40 ngày
        if low != 0:
            ratio = round((bb_1w[1] / low), 4)  # O/K
            row.append(ratio)  # U
        else:
            row.append("")
        
        # Cột V-Z: Dữ liệu bổ sung (5 cột)
        # V: Khoảng cách từ giá hiện tại đến BB1h trên
        distance_to_bb_up = round(((result_bb_array[0] - price) / price) * 100, 2) if price != 0 else 0
        row.append(distance_to_bb_up)  # V
        
        # W: Khoảng cách từ giá hiện tại đến BB1h dưới
        distance_to_bb_down = round(((price - result_bb_array[1]) / price) * 100, 2) if price != 0 else 0
        row.append(distance_to_bb_down)  # W
        
        # X-Y: Volume 1h và 4h
        try:
            vol_1h = data_collector.get_volumes_multi_timeframe(pair, timeframes=['1h']).get('1h', 0)
            vol_4h = data_collector.get_volumes_multi_timeframe(pair, timeframes=['4h']).get('4h', 0)
            row.append(vol_1h)  # X
            row.append(vol_4h)  # Y
        except:
            row.extend([0, 0])
        
        # Z: Trống (dự phòng)
        row.append("")
        
        # AA: Marker (trống - có thể dùng sau)
        row.append("")
        
        # AB-AC: Biên độ giá ngày lớn nhất (MỚI)
        try:
            max_vol, max_date = calculate_max_daily_volatility(symbol, lookback_days=365)
            row.append(max_vol)   # AB: Biên độ % lớn nhất
            row.append(max_date)  # AC: Ngày có biên độ lớn nhất
        except:
            row.extend([0, "N/A"])

        return row


    list_them = ["BTC/USDT:USDT", "BTCDOM/USDT:USDT"]
    

    tab_100_ma_2d_arr = []
    title1 = f"Top {cst.top_count} có % giảm giá nhiều nhất trong 24h"
    title2 = f"Top {cst.top_count} có % tăng giá nhiều nhất trong 24h"

    
    
    list_giam_nhieu_nhat = sorted(futures_symbols, key=lambda x: tickers[x]['percentage'])[:cst.top_count]
    list_tang_nhieu_nhat = sorted(futures_symbols, reverse=True, key=lambda x: tickers[x]['percentage'])[0:cst.top_count]

    # Bỏ tính toán Top 50 gần đỉnh/đáy (không cần trong bản đơn giản)

    list_all = []
    
    list_all.extend(list_them[::-1])
    list_all.append(title1)
    list_all.extend(list_giam_nhieu_nhat)
    list_all.append(title2)
    list_all.extend(list_tang_nhieu_nhat)

    with open("list_all.json", "w") as file:
        json.dump(list_all, file)


    
    tab_100_ma_2d_arr.append([title1])
    for symbol in list_giam_nhieu_nhat:
        tab_100_ma_2d_arr.append(get_row_result(symbol))
        
        if is_test_mode:
            break

    tab_100_ma_2d_arr.append([title2])
    index = 0

    
    for symbol in  list_tang_nhieu_nhat:
        if is_test_mode:
            break
        index +=1
        
        
        tab_100_ma_2d_arr.append(get_row_result(symbol))
    


    

    for symbol in list_them:
        tab_100_ma_2d_arr =  [get_row_result(symbol)]  + tab_100_ma_2d_arr

    # Lấy thông tin tài khoản (data_collector đã được khởi tạo ở đầu hàm)
    balance = exchange.fetch_balance()
    totalMarginBalance= round(float(balance["info"]["totalMarginBalance"]),4)
    totalCrossUnPnl= round(float(balance["info"]["totalCrossUnPnl"]),4)
    totalWalletBalance= round(float(balance["info"]["totalWalletBalance"]),4)
    
    # Không cần Funding Rate trong bản đơn giản

    
    
    


    # Không cần ghi thêm dữ liệu bổ sung cho BTC/BTCDOM vào cột N
    # Vì giờ tất cả các mã đã có đủ cột N-AA rồi





    # Hàng 2: Thông tin tài khoản (giống file cũ)
    tab_100_ma_2d_arr = [["Số dư margin/ví/pnl", totalMarginBalance,  totalWalletBalance, totalCrossUnPnl]]  + tab_100_ma_2d_arr

    # Hàng 1: Tiêu đề các cột
    header_row = [
        "Mã",                           # A
        "% 24h",                        # B
        "Giá trị hiện thời",           # C
        "BB1h trên",                    # D
        "BB1h dưới",                    # E
        "BB1 ngày trên",                # F
        "BB1 ngày dưới",                # G
        "Biên độ 1h max tăng tuần",    # H
        "Biên độ 1h max giảm tuần",    # I
        "Max 40 ngày",                  # J
        "Min 40 ngày",                  # K
        "Max tăng 4h/60 ngày",         # L
        "Max giảm 4h/60 ngày",         # M
        "Giá Cao Nhất",                # N: BB1w trên
        "Giá Thấp Nhất",               # O: BB1w dưới
        "Biên độ 30d tăng",            # P
        "Biên độ 30d giảm",            # Q
        "Volume 24h",                   # R
        "RSI 14",                       # S
        "",                             # T: Trống
        "Min/Min40",                    # U: O/K ratio
        "% đến BB1h trên",             # V
        "% đến BB1h dưới",             # W
        "Vol 1h",                       # X
        "Vol 4h",                       # Y
        "",                             # Z: Trống
        "Delist",                       # AA
        "Biên độ giá ngày lớn nhất (%)", # AB: Mới
        "Ngày biên độ lớn nhất"        # AC: Mới
    ]
    
    # Thêm header vào đầu array
    tab_100_ma_2d_arr = [header_row] + tab_100_ma_2d_arr
    
    # Thêm timestamp vào A1 sau khi có header
    current_time = datetime.now()
    time_string = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"Tổng số dòng dữ liệu: {len(tab_100_ma_2d_arr)}", flush=True)
    
    # Ghi tất cả dữ liệu từ hàng 1
    gg_sheet_factory.update_multi(gg_sheet_factory.tab_list_all_ma, -1, tab_100_ma_2d_arr, "A")
    
    # Ghi timestamp vào A1 (ghi đè lên header)
    gg_sheet_factory.update_single_value(gg_sheet_factory.tab_list_all_ma, "A1", time_string)

    

    end_time = time.time()
    execution_time = end_time - start_time
    print("Thời gian thực thi:", execution_time, "giây", flush=True)
 

gg_sheet_factory.init_sheet_api()










while True:
    try:
        do_it()
        

    except Exception as e:
        print(f"Tổng Lỗi: {e}", flush=True)
        logger.error(f"Tổng lỗi: {e}", exc_info=True)
        import traceback
        traceback.print_exc()

    if is_test_mode:
        break
    time.sleep(cst.delay_update_all)



















