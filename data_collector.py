"""
Data Collector - Thu thập dữ liệu thị trường mở rộng cho QBot v2.0
Bổ sung: Funding Rate, Volume 5 khung, Bollinger Bands 6 khung, High/Low với timestamp
"""

import ccxt
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import cst

logger = logging.getLogger(__name__)


class DataCollector:
    """Thu thập dữ liệu thị trường mở rộng"""
    
    def __init__(self, exchange: ccxt.binance):
        self.exchange = exchange
    
    def get_funding_rate(self, symbol: str = "BTC/USDT") -> float:
        """
        Lấy Funding Rate hiện tại
        
        Args:
            symbol: Cặp giao dịch
            
        Returns:
            Funding rate (%)
        """
        try:
            funding_rate = self.exchange.fetch_funding_rate(symbol)
            rate = float(funding_rate.get('fundingRate', 0)) * 100  # Convert to percentage
            logger.info(f"Funding Rate {symbol}: {rate:.4f}%")
            return round(rate, 4)
        except Exception as e:
            logger.error(f"Lỗi lấy funding rate cho {symbol}: {e}")
            return 0.0
    
    def get_volumes_multi_timeframe(
        self, 
        symbol: str,
        timeframes: List[str] = ['15m', '1h', '4h', '1d', '1w']
    ) -> Dict[str, float]:
        """
        Lấy volume cho nhiều khung thời gian
        
        Args:
            symbol: Cặp giao dịch
            timeframes: Danh sách timeframes
            
        Returns:
            Dict {timeframe: volume}
        """
        result = {}
        
        for tf in timeframes:
            try:
                # Lấy candle mới nhất
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=tf, limit=1)
                if ohlcv and len(ohlcv) > 0:
                    volume = ohlcv[0][5]  # Volume là index 5
                    result[tf] = round(volume, 2)
                    logger.debug(f"Volume {symbol} {tf}: {volume}")
                else:
                    result[tf] = 0.0
            except Exception as e:
                logger.error(f"Lỗi lấy volume {symbol} {tf}: {e}")
                result[tf] = 0.0
        
        return result
    
    def calculate_bollinger_bands(
        self,
        symbol: str,
        timeframe: str,
        period: int = 20,
        std_dev: int = 2
    ) -> Tuple[float, float, float]:
        """
        Tính Bollinger Bands
        
        Args:
            symbol: Cặp giao dịch
            timeframe: Khung thời gian
            period: Chu kỳ MA (mặc định 20)
            std_dev: Số độ lệch chuẩn (mặc định 2)
            
        Returns:
            Tuple (upper_band, middle_band, lower_band)
        """
        try:
            # Lấy dữ liệu OHLCV
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=period + 10)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Tính MA
            df['sma'] = df['close'].rolling(window=period).mean()
            
            # Tính Standard Deviation
            df['std'] = df['close'].rolling(window=period).std()
            
            # Tính Upper và Lower Bands
            df['upper_band'] = df['sma'] + (std_dev * df['std'])
            df['lower_band'] = df['sma'] - (std_dev * df['std'])
            
            # Lấy giá trị mới nhất
            upper = round(df['upper_band'].iloc[-1], 8)
            middle = round(df['sma'].iloc[-1], 8)
            lower = round(df['lower_band'].iloc[-1], 8)
            
            logger.debug(f"BB {symbol} {timeframe}: U={upper}, M={middle}, L={lower}")
            return upper, middle, lower
            
        except Exception as e:
            logger.error(f"Lỗi tính Bollinger Bands {symbol} {timeframe}: {e}")
            return 0.0, 0.0, 0.0
    
    def get_bollinger_bands_multi_timeframe(
        self,
        symbol: str,
        timeframes: List[str] = ['15m', '1h', '4h', '1d', '1w', '1M']
    ) -> Dict[str, Tuple[float, float, float]]:
        """
        Lấy Bollinger Bands cho nhiều khung thời gian
        
        Args:
            symbol: Cặp giao dịch
            timeframes: Danh sách timeframes
            
        Returns:
            Dict {timeframe: (upper, middle, lower)}
        """
        result = {}
        
        for tf in timeframes:
            try:
                bb = self.calculate_bollinger_bands(symbol, tf)
                result[tf] = bb
            except Exception as e:
                logger.error(f"Lỗi lấy BB {symbol} {tf}: {e}")
                result[tf] = (0.0, 0.0, 0.0)
        
        return result
    
    def calculate_max_change_in_period(
        self,
        symbol: str,
        timeframe: str,
        days: int
    ) -> Tuple[float, float]:
        """
        Tính biên độ tăng/giảm mạnh nhất trong khoảng thời gian
        
        Args:
            symbol: Cặp giao dịch
            timeframe: Khung thời gian (15m, 1h, 4h, 1d, 1w, 1M)
            days: Số ngày cần tính
            
        Returns:
            Tuple (max_increase_percent, max_decrease_percent)
        """
        try:
            # Tính số candles cần lấy
            candles_per_day_map = {
                '15m': 96,   # 24h * 4
                '1h': 24,
                '4h': 6,
                '1d': 1,
                '1w': 1/7,
                '1M': 1/30
            }
            
            candles_per_day = candles_per_day_map.get(timeframe, 24)
            limit = int(days * candles_per_day) + 1
            
            # Lấy dữ liệu
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Tính % thay đổi
            df['change_percent'] = ((df['close'] - df['open']) / df['open']) * 100
            
            max_increase = round(df['change_percent'].max(), 2)
            max_decrease = round(df['change_percent'].min(), 2)
            
            logger.debug(f"Max change {symbol} {timeframe} {days}d: +{max_increase}% / {max_decrease}%")
            return max_increase, max_decrease
            
        except Exception as e:
            logger.error(f"Lỗi tính max change {symbol} {timeframe}: {e}")
            return 0.0, 0.0
    
    def get_high_low_simple(
        self,
        symbol: str,
        days: int
    ) -> Tuple[float, int, float, int]:
        """
        Lấy giá cao/thấp nhất trong N ngày (ĐƠN GIẢN - chỉ 1 API call)
        
        Args:
            symbol: Cặp giao dịch
            days: Số ngày (3, 7, 30)
            
        Returns:
            Tuple (high_price, 0, low_price, 0) - timestamp để 0
        """
        try:
            # Chỉ lấy dữ liệu 1 ngày - KHÔNG cần fetch 1m
            now = self.exchange.milliseconds()
            start_time = now - (days * 24 * 60 * 60 * 1000)
            
            ohlcv_daily = self.exchange.fetch_ohlcv(
                symbol, 
                timeframe='1d', 
                since=start_time, 
                limit=days + 1
            )
            
            if not ohlcv_daily:
                return 0.0, 0, 0.0, 0
            
            # Tìm high/low cao/thấp nhất
            df_daily = pd.DataFrame(ohlcv_daily, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            high_price = df_daily['high'].max()
            low_price = df_daily['low'].min()
            
            logger.debug(f"High/Low {symbol} {days}d: High={high_price}, Low={low_price}")
            return float(high_price), 0, float(low_price), 0
            
        except Exception as e:
            logger.error(f"Lỗi lấy high/low {symbol} {days}d: {e}")
            return 0.0, 0, 0.0, 0
    
    def get_high_low_with_timestamp(
        self,
        symbol: str,
        days: int
    ) -> Tuple[float, int, float, int]:
        """
        Lấy giá cao/thấp nhất và timestamp trong N ngày (CHI TIẾT - 3 API calls)
        KHÔNG khuyến khích dùng cho nhiều symbols (quá chậm)
        
        Args:
            symbol: Cặp giao dịch
            days: Số ngày (3, 7, 30)
            
        Returns:
            Tuple (high_price, high_timestamp, low_price, low_timestamp)
        """
        try:
            # Lấy dữ liệu 1 ngày để xác định ngày có high/low
            now = self.exchange.milliseconds()
            start_time = now - (days * 24 * 60 * 60 * 1000)
            
            ohlcv_daily = self.exchange.fetch_ohlcv(
                symbol, 
                timeframe='1d', 
                since=start_time, 
                limit=days + 1
            )
            
            if not ohlcv_daily:
                return 0.0, 0, 0.0, 0
            
            # Tìm ngày có high/low cao/thấp nhất
            df_daily = pd.DataFrame(ohlcv_daily, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            max_high_idx = df_daily['high'].idxmax()
            min_low_idx = df_daily['low'].idxmin()
            
            max_candle = ohlcv_daily[max_high_idx]
            min_candle = ohlcv_daily[min_low_idx]
            
            # Lấy dữ liệu 1m để tìm timestamp chính xác
            # High price
            ohlcv_minute_high = self.exchange.fetch_ohlcv(
                symbol,
                timeframe='1m',
                since=int(max_candle[0]),
                limit=1440,  # 1 ngày = 1440 phút
                params={'endTime': int(max_candle[0] + 24 * 60 * 60 * 1000)}
            )
            
            if ohlcv_minute_high:
                df_minute_high = pd.DataFrame(ohlcv_minute_high, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                max_high_minute_idx = df_minute_high['high'].idxmax()
                high_price = df_minute_high.loc[max_high_minute_idx, 'high']
                high_timestamp = int(df_minute_high.loc[max_high_minute_idx, 'timestamp'])
            else:
                high_price = max_candle[2]
                high_timestamp = int(max_candle[0])
            
            # Low price
            ohlcv_minute_low = self.exchange.fetch_ohlcv(
                symbol,
                timeframe='1m',
                since=int(min_candle[0]),
                limit=1440,
                params={'endTime': int(min_candle[0] + 24 * 60 * 60 * 1000)}
            )
            
            if ohlcv_minute_low:
                df_minute_low = pd.DataFrame(ohlcv_minute_low, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                min_low_minute_idx = df_minute_low['low'].idxmin()
                low_price = df_minute_low.loc[min_low_minute_idx, 'low']
                low_timestamp = int(df_minute_low.loc[min_low_minute_idx, 'timestamp'])
            else:
                low_price = min_candle[3]
                low_timestamp = int(min_candle[0])
            
            logger.info(f"High/Low {symbol} {days}d: High={high_price}@{high_timestamp}, Low={low_price}@{low_timestamp}")
            return float(high_price), high_timestamp, float(low_price), low_timestamp
            
        except Exception as e:
            logger.error(f"Lỗi lấy high/low {symbol} {days}d: {e}")
            return 0.0, 0, 0.0, 0
    
    def calculate_distance_to_extreme(
        self,
        current_price: float,
        high_price: float,
        low_price: float
    ) -> Tuple[float, float]:
        """
        Tính khoảng cách từ giá hiện tại đến đỉnh/đáy
        
        Args:
            current_price: Giá hiện tại
            high_price: Giá cao nhất
            low_price: Giá thấp nhất
            
        Returns:
            Tuple (distance_to_high_percent, distance_to_low_percent)
        """
        try:
            distance_to_high = ((current_price - high_price) / high_price) * 100
            distance_to_low = ((current_price - low_price) / low_price) * 100
            
            return round(distance_to_high, 2), round(distance_to_low, 2)
        except:
            return 0.0, 0.0
    
    def find_top_50_near_extremes(
        self,
        symbols: List[str],
        period_days: int = 30
    ) -> Tuple[List[str], List[str]]:
        """
        Tìm Top 50 mã gần đỉnh/đáy nhất
        
        Args:
            symbols: Danh sách symbols
            period_days: Số ngày (mặc định 30)
            
        Returns:
            Tuple (top_50_near_high, top_50_near_low)
        """
        logger.info(f"Đang tìm Top 50 mã gần đỉnh/đáy {period_days} ngày...")
        
        distance_data = []
        
        for symbol in symbols:
            try:
                # Lấy giá hiện tại
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # Lấy high/low
                high, _, low, _ = self.get_high_low_with_timestamp(symbol, period_days)
                
                if high > 0 and low > 0:
                    dist_high, dist_low = self.calculate_distance_to_extreme(current_price, high, low)
                    
                    distance_data.append({
                        'symbol': symbol,
                        'current_price': current_price,
                        'high': high,
                        'low': low,
                        'dist_to_high': dist_high,
                        'dist_to_low': dist_low
                    })
                    
            except Exception as e:
                logger.error(f"Lỗi xử lý {symbol}: {e}")
                continue
        
        # Sắp xếp
        # Top 50 gần đỉnh: distance_to_high gần 0 nhất (giá trị âm nhỏ nhất)
        sorted_near_high = sorted(distance_data, key=lambda x: x['dist_to_high'], reverse=True)[:50]
        top_50_near_high = [item['symbol'] for item in sorted_near_high]
        
        # Top 50 gần đáy: distance_to_low gần 0 nhất (giá trị dương nhỏ nhất)
        sorted_near_low = sorted(distance_data, key=lambda x: x['dist_to_low'])[:50]
        top_50_near_low = [item['symbol'] for item in sorted_near_low]
        
        logger.info(f"✅ Đã tìm xong Top 50 gần đỉnh: {len(top_50_near_high)} mã")
        logger.info(f"✅ Đã tìm xong Top 50 gần đáy: {len(top_50_near_low)} mã")
        
        return top_50_near_high, top_50_near_low
    
    def get_30_recent_prices(
        self,
        symbol: str,
        interval_minutes: int = 1
    ) -> List[Dict]:
        """
        Lấy 30 mức giá gần nhất (mỗi phút 1 điểm)
        
        Args:
            symbol: Cặp giao dịch
            interval_minutes: Khoảng cách giữa các điểm (phút)
            
        Returns:
            List các dict {timestamp, price}
        """
        try:
            # Lấy 30 nến 1m gần nhất
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='1m', limit=30)
            
            result = []
            for candle in ohlcv:
                result.append({
                    'timestamp': int(candle[0]),
                    'price': float(candle[4])  # Close price
                })
            
            logger.debug(f"Đã lấy {len(result)} mức giá cho {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Lỗi lấy 30 mức giá cho {symbol}: {e}")
            return []


# Singleton instance
_data_collector = None

def get_data_collector(exchange: ccxt.binance) -> DataCollector:
    """Get singleton instance"""
    global _data_collector
    if _data_collector is None:
        _data_collector = DataCollector(exchange)
    return _data_collector

