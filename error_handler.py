"""
Centralized Error Handler cho QBot
Xử lý tất cả các loại lỗi thường gặp một cách thống nhất
"""

import logging
import time
from typing import Optional, Callable, Any
from functools import wraps
import ccxt

logger = logging.getLogger(__name__)


class ErrorType:
    """Các loại lỗi"""
    TRIGGER_IMMEDIATELY = "trigger_immediately"
    BINANCE_BLOCKED = "binance_blocked"
    API_OVERLOAD = "api_overload"
    SYMBOL_MISMATCH = "symbol_mismatch"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    POSITION_NOT_FOUND = "position_not_found"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_LEVERAGE = "invalid_leverage"
    NETWORK_ERROR = "network_error"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"


class ErrorAction:
    """Hành động xử lý lỗi"""
    SKIP = "skip"  # Bỏ qua, không retry
    RETRY = "retry"  # Retry với delay
    WAIT = "wait"  # Chờ một khoảng thời gian dài
    ALERT = "alert"  # Gửi cảnh báo Telegram
    CRITICAL = "critical"  # Dừng bot


class ErrorHandler:
    """Centralized error handler"""
    
    @staticmethod
    def identify_error_type(error: Exception) -> str:
        """
        Xác định loại lỗi từ exception
        
        Args:
            error: Exception object
            
        Returns:
            str: Error type
        """
        error_str = str(error).lower()
        
        if "trigger immediately" in error_str or "would immediately trigger" in error_str:
            return ErrorType.TRIGGER_IMMEDIATELY
            
        elif "-1102" in error_str or "blocked" in error_str:
            return ErrorType.BINANCE_BLOCKED
            
        elif "-1003" in error_str or "too many requests" in error_str:
            return ErrorType.API_OVERLOAD
            
        elif "invalid symbol" in error_str or "symbol not found" in error_str:
            return ErrorType.SYMBOL_MISMATCH
            
        elif "insufficient" in error_str and "balance" in error_str:
            return ErrorType.INSUFFICIENT_BALANCE
            
        elif "position not found" in error_str or "no position" in error_str:
            return ErrorType.POSITION_NOT_FOUND
            
        elif "-1015" in error_str or "rate limit" in error_str:
            return ErrorType.RATE_LIMIT_EXCEEDED
            
        elif "invalid leverage" in error_str or "leverage" in error_str:
            return ErrorType.INVALID_LEVERAGE
            
        elif isinstance(error, ccxt.NetworkError):
            return ErrorType.NETWORK_ERROR
            
        elif isinstance(error, ccxt.ExchangeError) and "5" in str(getattr(error, 'status_code', '')):
            return ErrorType.SERVER_ERROR
            
        else:
            return ErrorType.UNKNOWN
    
    @staticmethod
    def get_error_action(error_type: str) -> str:
        """
        Xác định hành động cần thực hiện cho loại lỗi
        
        Args:
            error_type: Loại lỗi
            
        Returns:
            str: Hành động (SKIP, RETRY, WAIT, ALERT, CRITICAL)
        """
        actions = {
            ErrorType.TRIGGER_IMMEDIATELY: ErrorAction.SKIP,
            ErrorType.BINANCE_BLOCKED: ErrorAction.WAIT,
            ErrorType.API_OVERLOAD: ErrorAction.RETRY,
            ErrorType.SYMBOL_MISMATCH: ErrorAction.SKIP,
            ErrorType.INSUFFICIENT_BALANCE: ErrorAction.SKIP,
            ErrorType.POSITION_NOT_FOUND: ErrorAction.SKIP,
            ErrorType.RATE_LIMIT_EXCEEDED: ErrorAction.RETRY,
            ErrorType.INVALID_LEVERAGE: ErrorAction.SKIP,
            ErrorType.NETWORK_ERROR: ErrorAction.RETRY,
            ErrorType.SERVER_ERROR: ErrorAction.RETRY,
            ErrorType.UNKNOWN: ErrorAction.ALERT,
        }
        
        return actions.get(error_type, ErrorAction.ALERT)
    
    @staticmethod
    def handle_error(
        error: Exception,
        context: dict,
        telegram_callback: Optional[Callable] = None
    ) -> dict:
        """
        Xử lý lỗi và trả về recommendation
        
        Args:
            error: Exception
            context: Dict chứa thông tin context (symbol, order_type, ...)
            telegram_callback: Function để gửi Telegram (optional)
            
        Returns:
            dict: {
                'error_type': str,
                'action': str,
                'retry_delay': int,
                'message': str
            }
        """
        error_type = ErrorHandler.identify_error_type(error)
        action = ErrorHandler.get_error_action(error_type)
        
        result = {
            'error_type': error_type,
            'action': action,
            'retry_delay': 0,
            'message': ''
        }
        
        # Xử lý theo từng loại
        if error_type == ErrorType.TRIGGER_IMMEDIATELY:
            result['message'] = f"Giá đã qua điểm kích hoạt cho {context.get('symbol', 'N/A')}, bỏ qua lệnh"
            logger.warning(f"⚠️ {result['message']}")
            
        elif error_type == ErrorType.BINANCE_BLOCKED:
            result['retry_delay'] = 300  # 5 phút
            result['message'] = f"Binance tạm thời chặn {context.get('symbol', 'N/A')}, chờ 5 phút"
            logger.warning(f"⛔ {result['message']}")
            
            if telegram_callback:
                msg = f"⛔ <b>BINANCE BLOCKED</b>\n\n<b>Mã:</b> {context.get('symbol', 'N/A')}\n<b>Lý do:</b> Biến động mạnh\n<b>Chờ:</b> 5 phút"
                telegram_callback(msg)
                
        elif error_type == ErrorType.API_OVERLOAD:
            result['retry_delay'] = 5
            result['message'] = "API quá tải, retry sau 5 giây"
            logger.warning(f"⚠️ {result['message']}")
            
        elif error_type == ErrorType.RATE_LIMIT_EXCEEDED:
            result['retry_delay'] = 10
            result['message'] = "Vượt rate limit, retry sau 10 giây"
            logger.warning(f"⚠️ {result['message']}")
            
        elif error_type == ErrorType.INSUFFICIENT_BALANCE:
            result['message'] = "Không đủ số dư, bỏ qua lệnh"
            logger.error(f"❌ {result['message']}")
            
            if telegram_callback:
                msg = f"🚨 <b>KHÔNG ĐỦ SỐ DƯ</b>\n\n<b>Mã:</b> {context.get('symbol', 'N/A')}\n<b>Hành động:</b> Bỏ qua lệnh"
                telegram_callback(msg)
                
        elif error_type == ErrorType.NETWORK_ERROR:
            result['retry_delay'] = 3
            result['message'] = "Lỗi mạng, retry sau 3 giây"
            logger.warning(f"⚠️ {result['message']}")
            
        elif error_type == ErrorType.SERVER_ERROR:
            result['retry_delay'] = 5
            result['message'] = "Lỗi server Binance (5xx), retry sau 5 giây"
            logger.warning(f"⚠️ {result['message']}")
            
        else:
            result['message'] = f"Lỗi không xác định: {str(error)}"
            logger.error(f"❌ {result['message']}")
            
            if telegram_callback:
                msg = f"🔴 <b>LỖI KHÔNG XÁC ĐỊNH</b>\n\n<b>Mã:</b> {context.get('symbol', 'N/A')}\n<b>Chi tiết:</b> {str(error)}"
                telegram_callback(msg)
        
        return result


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    skip_errors: list = None
):
    """
    Decorator để tự động retry với exponential backoff
    
    Args:
        max_retries: Số lần retry tối đa
        initial_delay: Delay ban đầu (giây)
        backoff_factor: Hệ số nhân delay mỗi lần retry
        skip_errors: List các error types không nên retry
        
    Usage:
        @retry_with_backoff(max_retries=3)
        def my_function():
            # code here
    """
    if skip_errors is None:
        skip_errors = [
            ErrorType.TRIGGER_IMMEDIATELY,
            ErrorType.SYMBOL_MISMATCH,
            ErrorType.INSUFFICIENT_BALANCE,
            ErrorType.POSITION_NOT_FOUND
        ]
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_error = e
                    error_type = ErrorHandler.identify_error_type(e)
                    
                    # Kiểm tra có nên retry không
                    if error_type in skip_errors:
                        logger.info(f"Lỗi {error_type} không retry, bỏ qua")
                        raise e
                    
                    # Nếu là lần cuối, raise error
                    if attempt == max_retries - 1:
                        logger.error(f"❌ Retry {max_retries} lần thất bại cho {func.__name__}")
                        raise e
                    
                    # Log retry
                    logger.warning(
                        f"⚠️ Retry {attempt + 1}/{max_retries} cho {func.__name__} "
                        f"sau {delay}s (Lỗi: {error_type})"
                    )
                    
                    # Delay trước khi retry
                    time.sleep(delay)
                    delay *= backoff_factor  # Exponential backoff
            
            # Không bao giờ đến đây, nhưng để đảm bảo
            if last_error:
                raise last_error
                
        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Test error handler
    def mock_telegram(msg):
        print(f"[Telegram] {msg}")
    
    try:
        raise ccxt.ExchangeError("Order would immediately trigger")
    except Exception as e:
        result = ErrorHandler.handle_error(
            error=e,
            context={'symbol': 'BTC/USDT', 'order_type': 'TRAILING_STOP'},
            telegram_callback=mock_telegram
        )
        print(f"Result: {result}")
    
    # Test retry decorator
    @retry_with_backoff(max_retries=3, initial_delay=0.5)
    def test_function():
        print("Attempting...")
        raise ccxt.NetworkError("Connection failed")
    
    try:
        test_function()
    except Exception as e:
        print(f"Final error: {e}")

