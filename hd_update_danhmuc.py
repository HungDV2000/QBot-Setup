import ccxt
from pprint import pprint
import time
import cst
import gg_sheet_factory
import logging
import os
from pathlib import Path
from datetime import datetime
import telegram_factory
import sys

file_name = os.path.basename(os.path.abspath(__file__))  
os.system(f"title {file_name} - {cst.key_name}")

# Tạo thư mục logs/ nếu chưa có
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Tạo tên file log với timestamp: hd_update_danhmuc_dd_mm_yyyy_H_M_S.txt
log_timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
log_filename = logs_dir / f'hd_update_danhmuc_{log_timestamp}.txt'

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

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(console_handler)

print(f"🚀 Bot cập nhật danh mục khởi động", flush=True)
print(f"CCXT version: {ccxt.__version__}", flush=True)
logger.info(f"CCXT version: {ccxt.__version__}")


def update_danhmuc():
    """
    ✅ NÂNG CẤP: Cập nhật danh mục active USDT futures pairs vào Google Sheet "Danhmuc"
    - Lấy danh sách từ Binance
    - Lọc các pairs đang TRADING và có giá hợp lệ
    - Cập nhật vào sheet với logging và Telegram notifications
    """
    try:
        print(f"\n{'='*80}", flush=True)
        print(f"🔄 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Bắt đầu cập nhật danh mục", flush=True)
        print(f"{'='*80}\n", flush=True)
        logger.info(f"{'='*80}")
        logger.info("Bắt đầu cập nhật danh mục")
        
        # Khởi tạo exchange
        exchange_class = getattr(ccxt, 'binance')
        exchange = exchange_class({
            'enableRateLimit': True,
            'apiKey': cst.key_binance,
            'secret': cst.secret_binance,
            'options': {
                'defaultType': 'swap'  
            }
        })
        exchange.setSandboxMode(False)
        exchange.urls['api']['fapi'] = 'https://fapi.binance.com'
        
        # Load markets với retry
        print("⏳ Đang load markets từ Binance...", flush=True)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                exchange.load_markets(reload=True)
                print("✅ Markets loaded successfully.", flush=True)
                logger.info("Markets loaded successfully.")
                break
            except Exception as e:
                logger.warning(f"Error loading markets (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"⚠️ Error loading markets (attempt {attempt + 1}/{max_retries}): {e}", flush=True)
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    raise Exception("Failed to load markets after retries.")

        # ✅ BƯỚC 1: Lấy danh sách active futures từ exchangeInfo
        print("📊 Đang lấy danh sách active futures từ Binance...", flush=True)
        try:
            exchange_info = exchange.fapiPublicGetExchangeInfo()
            active_futures_symbols = [
                s['symbol'] for s in exchange_info['symbols']
                if s['status'] == 'TRADING'
                and s['symbol'].endswith('USDT')
                and s['contractType'] == 'PERPETUAL'
            ]
            print(f"✅ Tìm thấy {len(active_futures_symbols)} active perpetual futures pairs", flush=True)
            logger.info(f"Tìm thấy {len(active_futures_symbols)} active perpetual futures pairs từ exchangeInfo")
        except Exception as e:
            error_msg = f"Error fetching exchangeInfo: {e}"
            print(f"❌ {error_msg}", flush=True)
            logger.error(error_msg, exc_info=True)
            raise Exception("Failed to fetch active futures pairs from exchangeInfo.")

        # ✅ BƯỚC 2: Lọc và validate từ markets
        print("🔍 Đang lọc và validate symbols...", flush=True)
        markets = exchange.markets
        futures_symbols = []
        delisted_symbols = []
        
        processed_count = 0
        for symbol in markets.keys():
            market = markets[symbol]
            if (symbol.endswith('/USDT:USDT')
                and market.get('type') == 'swap'
                and not any(suffix in symbol for suffix in ['UP/USDT', 'DOWN/USDT', 'BULL/USDT', 'BEAR/USDT'])):
                symbol_id = market['id']  
                
                if symbol_id in active_futures_symbols:
                    # Validate bằng cách lấy ticker price
                    try:
                        ticker = exchange.fapiPublicGetTickerPrice({'symbol': symbol_id})
                        if 'price' in ticker and ticker['price']:
                            futures_symbols.append(symbol.replace(':USDT', ''))
                            processed_count += 1
                            if processed_count % 50 == 0:
                                print(f"  Đã xử lý {processed_count} symbols...", flush=True)
                        else:
                            delisted_symbols.append(symbol.replace(':USDT', ''))
                            logger.debug(f"Excluded {symbol}: No valid price in ticker")
                    except ccxt.ExchangeError as e:
                        delisted_symbols.append(symbol.replace(':USDT', ''))
                        logger.debug(f"Excluded {symbol}: Ticker error - {e}")
                else:
                    delisted_symbols.append(symbol.replace(':USDT', ''))

        # Sắp xếp danh sách
        futures_symbols = sorted(futures_symbols)
        
        print(f"\n✅ Hoàn thành lọc symbols:", flush=True)
        print(f"  📊 Active: {len(futures_symbols)} symbols", flush=True)
        print(f"  ⏭️  Delisted: {len(delisted_symbols)} symbols", flush=True)
        logger.info(f"Kết quả: Active={len(futures_symbols)}, Delisted={len(delisted_symbols)}")

        # ✅ BƯỚC 3: Cập nhật vào Google Sheet
        print(f"\n📤 Đang cập nhật vào Google Sheet 'Danhmuc'...", flush=True)
        try:
            # Convert sang format 2D array
            futures_symbols_2d = [[symbol] for symbol in futures_symbols]
            
            # Clear và update sheet
            gg_sheet_factory.clear_multi("Danhmuc", -1, "a")
            gg_sheet_factory.update_multi("Danhmuc", -1, futures_symbols_2d, "a")
            
            # Ghi timestamp vào A1 (nếu cần)
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                gg_sheet_factory.update_single_value("Danhmuc", "A1", f"Cập nhật lần cuối: {timestamp_str}")
            except:
                pass  # Không bắt buộc
            
            print(f"✅ Đã cập nhật {len(futures_symbols)} symbols vào sheet 'Danhmuc'", flush=True)
            logger.info(f"✅ Đã cập nhật {len(futures_symbols)} symbols vào sheet 'Danhmuc'")
            
            # ✅ Gửi thông báo Telegram
            msg = f"✅ <b>CẬP NHẬT DANH MỤC</b>\n\n"
            msg += f"<b>Tổng symbols:</b> {len(futures_symbols)}\n"
            msg += f"<b>Delisted:</b> {len(delisted_symbols)}\n"
            msg += f"<b>Thời gian:</b> {timestamp_str}"
            telegram_factory.send_tele(msg, cst.chat_id, True, True)
            
            return {
                'success': True,
                'active_count': len(futures_symbols),
                'delisted_count': len(delisted_symbols),
                'symbols': futures_symbols
            }
            
        except Exception as e:
            error_msg = f"Error updating Google Sheet: {e}"
            print(f"❌ {error_msg}", flush=True)
            logger.error(error_msg, exc_info=True)
            
            # Gửi thông báo lỗi
            msg = f"❌ <b>LỖI CẬP NHẬT DANH MỤC</b>\n\n<b>Lỗi:</b> {str(e)}"
            telegram_factory.send_tele(msg, cst.chat_id, True, True)
            
            return {
                'success': False,
                'error': str(e)
            }
        
    except Exception as e:
        error_msg = f"General error: {e}"
        print(f"❌ {error_msg}", flush=True)
        logger.error(error_msg, exc_info=True)
        
        # Gửi thông báo lỗi
        msg = f"❌ <b>LỖI NGHIÊM TRỌNG</b>\n\n<b>Lỗi:</b> {str(e)}"
        telegram_factory.send_tele(msg, cst.chat_id, True, True)
        
        return {
            'success': False,
            'error': str(e)
        }


# Main execution
if __name__ == "__main__":
    try:
        result = update_danhmuc()
        
        if result['success']:
            print(f"\n{'='*80}", flush=True)
            print(f"✅ HOÀN THÀNH!", flush=True)
            print(f"  Active symbols: {result['active_count']}", flush=True)
            print(f"  Delisted symbols: {result['delisted_count']}", flush=True)
            print(f"{'='*80}\n", flush=True)
        else:
            print(f"\n❌ Cập nhật thất bại: {result.get('error', 'Unknown error')}", flush=True)
            
    except KeyboardInterrupt:
        print("\n⚠️  Nhận Ctrl+C - Dừng bot...", flush=True)
        logger.info("Bot dừng bởi user (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Tổng lỗi: {e}", flush=True)
        logger.error(f"Tổng lỗi: {e}", exc_info=True)
    
    # Nếu chạy như script, dừng lại để xem kết quả
    if __name__ == "__main__":
        input("\nPress Enter to exit...")
