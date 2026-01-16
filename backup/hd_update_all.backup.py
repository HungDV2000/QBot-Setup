import gg_sheet_factory
import ccxt 
import time
import datetime
from enum import Enum
import numpy as np
from datetime import datetime, timedelta
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

logging.basicConfig(filename='error_pumb_dump.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
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
        
        # Thêm thời điểm niêm yết (tạm thời để trống, cần API riêng)
        row.append("")  # Cột 4: Thời điểm niêm yết
        
        # Thêm Volume 5 khung thời gian (15m, 1h, 4h, 1d, 1w)
        volumes = data_collector.get_volumes_multi_timeframe(
            pair, 
            timeframes=['15m', '1h', '4h', '1d', '1w']
        )
        row.extend([
            volumes.get('15m', 0),  # Cột 5
            volumes.get('1h', 0),    # Cột 6
            volumes.get('4h', 0),    # Cột 7
            volumes.get('1d', 0),    # Cột 8
            volumes.get('1w', 0)     # Cột 9
        ])

        # Bollinger Bands đầy đủ 6 khung (15m, 1h, 4h, 1d, 1w, 1M)
        # Mỗi khung trả về 2-4 giá trị (upper, lower, max_increase, max_decrease)
        result_bb_array = get_bb(pair,  timeframes = ['15m', '1h', '4h', '1d', '1w', '1M'])
        row.extend(result_bb_array)

        
        
        max_price_increase_month1, max_price_decrease_month1 = calculate_price_range(pair, 7, '1h')
        
        

        
        
        max_price_increase_month1 = "" if np.isnan(max_price_increase_month1) else max_price_increase_month1
        max_price_decrease_month1 = "" if np.isnan(max_price_decrease_month1) else max_price_decrease_month1

        
        
        row.append(max_price_increase_month1)
        row.append(max_price_decrease_month1)

        
        
        
        
        

        
        
        

 

        
        
        
        

        
        

        # Giá cao/thấp 30 ngày (giữ logic cũ)
        high, low = calculate_high_low_30d(symbol)
        row.append(high)
        row.append(low)
        
        # Fix: Đơn giản hóa - chỉ lấy high/low (không cần timestamp phút)
        # Giảm từ 900 API calls → 300 API calls cho 100 symbols
        try:
            # 3 ngày - chỉ lấy high/low
            high_3d, _, low_3d, _ = data_collector.get_high_low_simple(pair, 3)
            row.extend([high_3d, "", low_3d, ""])  # Cột Z, AA, AB, AC
            
            # 7 ngày
            high_7d, _, low_7d, _ = data_collector.get_high_low_simple(pair, 7)
            row.extend([high_7d, "", low_7d, ""])  # Cột AD, AE, AF, AG
            
            # 30 ngày
            high_30d, _, low_30d, _ = data_collector.get_high_low_simple(pair, 30)
            row.extend([high_30d, "", low_30d, ""])  # Cột AH, AI, AJ, AK
        except Exception as e:
            logging.error(f"Lỗi lấy high/low cho {pair}: {e}", flush=True)
            # Thêm 12 cột trống (3 periods * 4 values)
            row.extend([""] * 12)

        # Biên độ tăng/giảm 4h (giữ nguyên)
        increase, decrease = calculate_max_increase_decrease_4h(symbol)
        row.append(increase)
        row.append(decrease)
        
        # Marker Top 50 gần đỉnh/đáy
        marker = ""
        if pair in top_50_near_high:
            marker = "🔴 TOP ĐỈNH"
        elif pair in top_50_near_low:
            marker = "🟢 TOP ĐÁY"
        row.append(marker)

        return row


    list_them = ["BTC/USDT:USDT", "BTCDOM/USDT:USDT"]
    

    tab_100_ma_2d_arr = []
    title1 = f"Top {cst.top_count} có % giảm giá nhiều nhất trong 24h"
    title2 = f"Top {cst.top_count} có % tăng giá nhiều nhất trong 24h"

    
    
    list_giam_nhieu_nhat = sorted(futures_symbols, key=lambda x: tickers[x]['percentage'])[:cst.top_count]
    list_tang_nhieu_nhat = sorted(futures_symbols, reverse=True, key=lambda x: tickers[x]['percentage'])[0:cst.top_count]

    # Fix: Tính Top 50 gần đỉnh/đáy TRƯỚC khi gọi get_row_result()
    print("Đang tìm Top 50 mã gần đỉnh/đáy...", flush=True)
    all_symbols = list_giam_nhieu_nhat + list_tang_nhieu_nhat + list_them
    top_50_near_high, top_50_near_low = data_collector.find_top_50_near_extremes(
        [s.replace(":USDT", "") for s in all_symbols],
        period_days=30
    )
    print(f"✅ Top 50 gần đỉnh: {len(top_50_near_high)} mã", flush=True)
    print(f"✅ Top 50 gần đáy: {len(top_50_near_low)} mã", flush=True)

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
    
    # Lấy Funding Rate
    funding_rate = data_collector.get_funding_rate("BTC/USDT")
    print(f"Funding Rate: {funding_rate}%", flush=True)

    
    
    


    
    
    list_them_2d_arr = []
    for symbol in list_them:
        row_data = []
        bb_1d = get_bb(symbol, timeframes = [ '1w'])
        row_data.extend(bb_1d)
        bd =  get_bien_do_max(symbol) 
        row_data.append(bd[4])
        row_data.append(bd[5])
        list_them_2d_arr.append(row_data)

    print(list_them_2d_arr, flush=True)
    
    gg_sheet_factory.update_multi(gg_sheet_factory.tab_list_all_ma, 1, list_them_2d_arr, "N")





    # Hàng 2: Funding Rate | Margin Balance | Wallet Balance | Unrealized PNL
    tab_100_ma_2d_arr = [[funding_rate, totalMarginBalance,  totalWalletBalance, totalCrossUnPnl]]  + tab_100_ma_2d_arr

    # Fix: Clear dữ liệu cũ trước khi ghi mới (từ hàng 1 trở đi)
    # Clear từ hàng 1 đến hàng 1000
    # array_index = -1 để clear từ hàng 1 (vì index = abs(-1) = 1)
    gg_sheet_factory.clear_multi(gg_sheet_factory.tab_list_all_ma, -1, "A", end_row=1000)
    
    # Lấy timestamp hiện tại
    current_time = datetime.now()
    time_string = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Ghi timestamp vào A1 (không có header)
    print("Ghi timestamp vào A1...", flush=True)
    gg_sheet_factory.update_single_value(gg_sheet_factory.tab_list_all_ma, "A1", time_string)
    
    # Header từ B1 trở đi (tên tiếng Việt)
    header_row = [
        "% 24h",                        # B: Percentage 24h
        "Giá trị hiện thời",           # C: Price
        "Niêm yết",                     # D: Listing time
        "Vol 15p", "Vol 1h", "Vol 4h", "Vol 1 ngày", "Vol 1 tuần",  # E-I: Volume
        "BB15p trên", "BB15p dưới",     # J-K: BB 15m
        "BB1h trên", "BB1h dưới",       # L-M: BB 1h
        "BB4h trên", "BB4h dưới",       # N-O: BB 4h
        "BB1 ngày trên", "BB1 ngày dưới",  # P-Q: BB 1d
        "BB1 tuần trên", "BB1 tuần dưới",  # R-S: BB 1w
        "BB1 tháng trên", "BB1 tháng dưới",  # T-U: BB 1M
        "Biên độ 1h max tăng tuần", "Biên độ 1h max giảm tuần",  # V-W: Max inc/dec 7d
        "Max 30 ngày", "Min 30 ngày",   # X-Y: High/Low 30d
        "Max 3 ngày", "Thời điểm Max 3 ngày", "Min 3 ngày", "Thời điểm Min 3 ngày",  # Z-AC: High/Low 3d
        "Max 7 ngày", "Thời điểm Max 7 ngày", "Min 7 ngày", "Thời điểm Min 7 ngày",  # AD-AG: High/Low 7d
        "Max 30 ngày chi tiết", "Thời điểm Max 30 ngày", "Min 30 ngày chi tiết", "Thời điểm Min 30 ngày",  # AH-AK: High/Low 30d chi tiết
        "Max tăng 4h/60 ngày", "Max giảm 4h/60 ngày",  # AL-AM: Inc/Dec 4h
        "Đánh dấu"                      # AN: Marker
    ]
    
    # Ghi header từ B1 trở đi
    print("Ghi header từ B1 trở đi...", flush=True)
    gg_sheet_factory.update_multi(gg_sheet_factory.tab_list_all_ma, -1, [header_row], "B")
    print(f"Tổng số dòng dữ liệu: {len(tab_100_ma_2d_arr)}", flush=True)
    
    # Fix: Ghi data từ hàng 2 (array_index = 0 để ghi từ hàng 2)
    # Header đã ở hàng 1, data bắt đầu từ hàng 2
    gg_sheet_factory.update_multi(gg_sheet_factory.tab_list_all_ma, 0, tab_100_ma_2d_arr, "A")

    

    end_time = time.time()
    execution_time = end_time - start_time
    print("Thời gian thực thi:", execution_time, "giây", flush=True)
 

gg_sheet_factory.init_sheet_api()










while True:
    try:
        do_it()
        

    except Exception as e:
        print(f"Tổng Lỗi: {e}", flush=True)
        import traceback
        traceback.print_exc()
        logging.error("Tổng lỗi: %s", str(e))

    if is_test_mode:
        break
    time.sleep(cst.delay_update_all)



















