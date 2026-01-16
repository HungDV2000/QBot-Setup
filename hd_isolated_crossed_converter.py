import ccxt
from pprint import pprint
import time
import cst
import logging
import os
from pathlib import Path
from datetime import datetime
import telegram_factory
import gg_sheet_factory

file_name = os.path.basename(os.path.abspath(__file__))  
os.system(f"title {file_name} - {cst.key_name}")

# Tạo thư mục logs/ nếu chưa có
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Tạo tên file log với timestamp: hd_isolated_crossed_converter_dd_mm_yyyy_H_M_S.txt
log_timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
log_filename = logs_dir / f'hd_isolated_crossed_converter_{log_timestamp}.txt'

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
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(console_handler)

sleep_gap = 0.1  # Delay giữa các requests để tránh rate limit


def toggle_isolated_margin(exchange, enable_isolated=True, symbols_list=None):
    """
    Enable or disable isolated margin for USDT-M futures pairs (:USDT).
    
    ✅ NÂNG CẤP:
    - Hỗ trợ chọn symbols cụ thể từ Google Sheet hoặc xử lý tất cả
    - Thêm logging chi tiết
    - Thêm Telegram notifications
    - Cải thiện error handling
    
    Args:
        exchange: CCXT exchange object (Binance)
        enable_isolated: True for ISOLATED, False for CROSS
        symbols_list: List symbols cụ thể cần xử lý (None = xử lý tất cả)
    
    Returns:
        dict: Results with processed pairs and their status
    """
    margin_type = 'ISOLATED' if enable_isolated else 'CROSSED'
    result = {'success': [], 'failed': [], 'skipped': []}
    
    try:
        exchange.urls['api']['fapi'] = 'https://fapi.binance.com'
        
        # Load markets với retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                exchange.load_markets(reload=True)
                logger.info("Markets loaded successfully.")
                print("✅ Markets loaded successfully.", flush=True)
                break
            except Exception as e:
                logger.warning(f"Error loading markets (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"⚠️ Error loading markets (attempt {attempt + 1}/{max_retries}): {e}", flush=True)
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    raise Exception("Failed to load markets after retries.")

        markets = exchange.markets
        
        # ✅ NÂNG CẤP: Nếu có symbols_list, chỉ xử lý các symbols đó
        if symbols_list:
            futures_symbols = []
            for symbol_input in symbols_list:
                # Format symbol: "HOME/USDT" hoặc "HOMEUSDT" → "HOME/USDT:USDT"
                symbol = str(symbol_input).strip()
                if "/" not in symbol:
                    symbol = symbol.replace("USDT", "/USDT:USDT")
                elif ":USDT" not in symbol:
                    symbol = f"{symbol}:USDT"
                
                if symbol in markets:
                    futures_symbols.append(symbol)
                else:
                    logger.warning(f"Symbol {symbol} không tồn tại trong markets")
                    print(f"⚠️ Symbol {symbol} không tồn tại", flush=True)
        else:
            # Xử lý tất cả USDT futures pairs
            futures_symbols = [symbol for symbol in markets.keys() 
                             if symbol.endswith('/USDT:USDT') 
                             and markets[symbol].get('type') == 'swap' 
                             and not any(suffix in symbol for suffix in ['UP/USDT', 'DOWN/USDT', 'BULL/USDT', 'BEAR/USDT'])]

        logger.info(f"Tổng {len(futures_symbols)} symbols cần xử lý")
        print(f"📊 Tổng {len(futures_symbols)} symbols cần xử lý", flush=True)
        
        if not futures_symbols:
            raise Exception("No symbols found to process.")

        # Xử lý từng symbol
        for idx, symbol in enumerate(futures_symbols, 1):
            print(f"\n[{idx}/{len(futures_symbols)}] Processing: {symbol}", flush=True)
            logger.info(f"Processing {symbol} ({idx}/{len(futures_symbols)})")
            
            try:
                symbol_id = exchange.market(symbol)['id']
                
                # ✅ Kiểm tra positions
                try:
                    positions = exchange.fapiPrivateV2GetPositionRisk({'symbol': symbol_id})
                    if any(float(pos.get('positionAmt', 0)) != 0 for pos in positions):
                        print(f"  ⏭️  Bỏ qua: Có positions đang mở", flush=True)
                        logger.warning(f"{symbol}: Open positions exist, skipped")
                        result['skipped'].append({symbol: 'Open positions exist'})
                        continue
                except Exception as e:
                    logger.warning(f"{symbol}: Lỗi khi kiểm tra positions: {e}")

                # ✅ Kiểm tra open orders
                try:
                    open_orders = exchange.fapiPrivateGetOpenOrders({'symbol': symbol_id})
                    if open_orders:
                        print(f"  ⏭️  Bỏ qua: Có orders đang chờ", flush=True)
                        logger.warning(f"{symbol}: Open orders exist, skipped")
                        result['skipped'].append({symbol: 'Open orders exist'})
                        continue
                except Exception as e:
                    logger.warning(f"{symbol}: Lỗi khi kiểm tra orders: {e}")

                # ✅ Chuyển đổi margin type
                request = {
                    'symbol': symbol_id,
                    'marginType': margin_type.upper()
                }
                
                try:
                    response = exchange.fapiPrivatePostMarginType(request)
                    print(f"  ✅ Đã chuyển sang {margin_type}", flush=True)
                    logger.info(f"{symbol}: Successfully switched to {margin_type}")
                    result['success'].append({symbol: response})
                except ccxt.ExchangeError as e:
                    error_str = str(e)
                    
                    # Retry với 'margintype' (lowercase) nếu gặp lỗi -1102
                    if "code=-1102" in error_str:
                        logger.warning(f"{symbol}: Error -1102, retrying with 'margintype'...")
                        print(f"  🔄 Retry với margintype...", flush=True)
                        alt_request = {
                            'symbol': symbol_id,
                            'margintype': margin_type.upper()
                        }
                        try:
                            response = exchange.fapiPrivatePostMarginType(alt_request)
                            print(f"  ✅ Đã chuyển sang {margin_type} (retry)", flush=True)
                            logger.info(f"{symbol}: Successfully switched to {margin_type} (retry)")
                            result['success'].append({symbol: response})
                        except Exception as e2:
                            logger.error(f"{symbol}: Retry failed: {e2}")
                            result['failed'].append({symbol: str(e2)})
                    
                    # Đã ở mode này rồi
                    elif "code=-4046" in error_str:
                        print(f"  ℹ️  Đã ở {margin_type} mode", flush=True)
                        logger.info(f"{symbol}: Already in {margin_type} mode")
                        result['skipped'].append({symbol: f"Already in {margin_type} mode"})
                    
                    # Có positions/orders
                    elif "code=-4059" in error_str:
                        print(f"  ⏭️  Bỏ qua: Có positions/orders", flush=True)
                        logger.warning(f"{symbol}: Open positions/orders, cannot switch")
                        result['skipped'].append({symbol: 'Open positions/orders'})
                    
                    else:
                        logger.error(f"{symbol}: ExchangeError: {e}")
                        result['failed'].append({symbol: str(e)})
                        
            except Exception as e:
                logger.error(f"{symbol}: Unknown error: {e}", exc_info=True)
                print(f"  ❌ Lỗi: {e}", flush=True)
                result['failed'].append({symbol: str(e)})

            time.sleep(sleep_gap)

        # ✅ Gửi thông báo Telegram
        success_count = len(result['success'])
        failed_count = len(result['failed'])
        skipped_count = len(result['skipped'])
        
        msg = f"✅ <b>CHUYỂN ĐỔI MARGIN TYPE</b>\n\n"
        msg += f"<b>Mode:</b> {margin_type}\n"
        msg += f"<b>Thành công:</b> {success_count}\n"
        msg += f"<b>Bỏ qua:</b> {skipped_count}\n"
        msg += f"<b>Lỗi:</b> {failed_count}\n"
        msg += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        telegram_factory.send_tele(msg, cst.chat_id, True, True)
        
        return result

    except Exception as e:
        logger.error(f"General error: {e}", exc_info=True)
        print(f"❌ General error: {e}", flush=True)
        result['failed'].append({'general': str(e)})
        return result


def get_symbols_from_sheet():
    """
    ✅ NÂNG CẤP: Đọc danh sách symbols từ Google Sheet "Chờ và khớp" (cột A)
    """
    try:
        sheet_data = gg_sheet_factory.get_cho_va_khop("A3:A100")
        symbols = []
        
        for row in sheet_data:
            if row and len(row) > 0 and row[0]:
                symbol = str(row[0]).strip()
                if symbol and "USDT" in symbol.upper():
                    symbols.append(symbol)
        
        logger.info(f"Đã đọc {len(symbols)} symbols từ sheet")
        print(f"📋 Đã đọc {len(symbols)} symbols từ sheet", flush=True)
        return symbols
        
    except Exception as e:
        logger.error(f"Lỗi khi đọc symbols từ sheet: {e}", exc_info=True)
        print(f"⚠️ Lỗi khi đọc symbols từ sheet: {e}", flush=True)
        return None


if __name__ == "__main__":
    print(f"🚀 Bot chuyển đổi Margin Type khởi động", flush=True)
    print(f"CCXT version: {ccxt.__version__}", flush=True)
    logger.info(f"CCXT version: {ccxt.__version__}")

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

    try:
        # ✅ NÂNG CẤP: Menu lựa chọn
        print("\n" + "="*80, flush=True)
        print("Chọn chế độ:", flush=True)
        print("1: Chuyển TẤT CẢ symbols sang CROSS", flush=True)
        print("2: Chuyển TẤT CẢ symbols sang ISOLATED", flush=True)
        print("3: Chuyển symbols từ SHEET sang CROSS", flush=True)
        print("4: Chuyển symbols từ SHEET sang ISOLATED", flush=True)
        print("="*80, flush=True)
        
        while True:
            choice = input("Nhập lựa chọn (1-4): ").strip()
            
            if choice == '1':
                enable_isolated = False
                mode = "CROSS"
                symbols_list = None  # Xử lý tất cả
                break
            elif choice == '2':
                enable_isolated = True
                mode = "ISOLATED"
                symbols_list = None  # Xử lý tất cả
                break
            elif choice == '3':
                enable_isolated = False
                mode = "CROSS"
                symbols_list = get_symbols_from_sheet()
                if not symbols_list:
                    print("❌ Không đọc được symbols từ sheet!", flush=True)
                    continue
                break
            elif choice == '4':
                enable_isolated = True
                mode = "ISOLATED"
                symbols_list = get_symbols_from_sheet()
                if not symbols_list:
                    print("❌ Không đọc được symbols từ sheet!", flush=True)
                    continue
                break
            else:
                print("❌ Lựa chọn không hợp lệ! Vui lòng nhập 1-4.", flush=True)

        print(f"\n{'='*80}", flush=True)
        print(f"🔄 Bắt đầu chuyển đổi sang {mode} margin...", flush=True)
        if symbols_list:
            print(f"📋 Symbols từ sheet: {len(symbols_list)} symbols", flush=True)
        else:
            print(f"🌐 Xử lý TẤT CẢ USDT futures pairs", flush=True)
        print(f"{'='*80}\n", flush=True)
        
        logger.info(f"Bắt đầu chuyển đổi sang {mode} margin")
        
        result = toggle_isolated_margin(exchange, enable_isolated=enable_isolated, symbols_list=symbols_list)
        
        print(f"\n{'='*80}", flush=True)
        print(f"📊 KẾT QUẢ ({mode}):", flush=True)
        print(f"✅ Thành công: {len(result['success'])}", flush=True)
        print(f"⏭️  Bỏ qua: {len(result['skipped'])}", flush=True)
        print(f"❌ Lỗi: {len(result['failed'])}", flush=True)
        print(f"{'='*80}\n", flush=True)
        
        logger.info(f"Kết quả: Success={len(result['success'])}, Skipped={len(result['skipped'])}, Failed={len(result['failed'])}")
        
        if result['failed']:
            print("❌ Các symbols bị lỗi:", flush=True)
            for item in result['failed']:
                print(f"  - {item}", flush=True)

    except ccxt.NetworkError as e:
        error_msg = f"Network error: {e}. Check internet connection or Binance API status: https://status.binance.com/."
        print(f"❌ {error_msg}", flush=True)
        logger.error(error_msg)
    except ccxt.AuthenticationError as e:
        error_msg = f"Authentication error: {e}. Check API key and secret in cst."
        print(f"❌ {error_msg}", flush=True)
        logger.error(error_msg)
    except KeyboardInterrupt:
        print("\n⚠️  Nhận Ctrl+C - Dừng bot...", flush=True)
        logger.info("Bot dừng bởi user (Ctrl+C)")
    except Exception as e:
        error_msg = f"Unknown error: {e}"
        print(f"❌ {error_msg}", flush=True)
        logger.error(error_msg, exc_info=True)

    input("\nPress Enter to exit...")
