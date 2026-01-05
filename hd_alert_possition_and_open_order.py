import ccxt
import cst
import gg_sheet_factory
import cst
import logging
import time
from datetime import datetime
from pathlib import Path
import utils
import telegram_factory
import os
from binance_order_helper import cancel_all_open_orders_with_retry, BinanceOrderHelper
from cascade_manager import get_cascade_manager
from order_state_tracker import get_tracker
from notification_manager import get_notification_manager

file_name = os.path.basename(os.path.abspath(__file__))  
os.system(f"title {file_name} - {cst.key_name}")

# Tạo thư mục logs/ nếu chưa có
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Log file riêng (liên quan đến positions/orders - xử lý tiền)
log_file = logs_dir / 'hd_alert_possition_and_open_order.log'
logging.basicConfig(
    filename=str(log_file), 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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

# Khởi tạo order helper, cascade manager và notification manager
order_helper = BinanceOrderHelper(exchange)
cascade_mgr = get_cascade_manager(exchange, order_helper)
notif_mgr = get_notification_manager(cst.chat_id)



def get_all_open_orders_with_single_order():
    res = []
    
    for sym in  utils.get_all_open_orders_symbol_local():
        print(sym, flush=True)
        
        
        orders = exchange.fetch_open_orders(symbol=sym)
        if len(orders) == 1:
            res.append(orders[0])
        
        for order in orders:
            print(f"Symbol: {order['symbol']}, ID: {order['id']}, Status: {order['status']}, Amount: {order['amount']}, Price: {order['price']}", flush=True)
    return res

def get_opened_possition():
    
    balance = exchange.fetch_balance()
    positions = balance['info']['positions']
    opened_possition = []
    
    for position in positions:
        try:
            symbol = position.get('symbol', '')
            if not symbol:
                continue
                
            position_amt = float(position.get('positionAmt', 0))
            
            # Chỉ xử lý position có amount khác 0
        if position_amt != 0:
                # Sử dụng .get() với giá trị mặc định để tránh KeyError
                entry_price = float(position.get('entryPrice', 0))
                unrealized_pnl = float(position.get('unrealizedProfit', 0))
                leverage = int(position.get('leverage', 1))
                
                print(position, flush=True)
            opened_possition.append(position)
                print(f"Symbol: {symbol}, Position: {position_amt}, Entry Price: {entry_price}, Unrealized PnL: {unrealized_pnl}, Leverage: {leverage}", flush=True)
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Lỗi khi xử lý position: {position.get('symbol', 'UNKNOWN')} - {e}")
            continue
            
    return opened_possition

result_old = []
is_first_time = True

def cancel_all_open_orders(symbol):
    """
    Hủy tất cả lệnh chờ với retry mechanism
    """
    logger.info(f"Bắt đầu hủy lệnh chờ cho {symbol}...")
    
    success, remaining = cancel_all_open_orders_with_retry(
        exchange=exchange,
        symbol=symbol,
        max_retries=3,
        delay=2
    )
    
    if success:
        msg = f"✅ <b>ĐÃ HỦY LỆNH CHỜ</b>\n\n<b>Mã:</b> {symbol}\n<b>Trạng thái:</b> Đã xóa sạch tất cả lệnh"
        telegram_factory.send_tele(msg, cst.chat_id, True, True)
        logger.info(f"✅ Hủy lệnh thành công cho {symbol}")
    else:
        msg = f"🔴 <b>CẢNH BÁO NGHIÊM TRỌNG</b>\n\n<b>Mã:</b> {symbol}\n<b>Vấn đề:</b> Không thể xóa lệnh Reduce Only sau 3 lần thử\n<b>Lệnh còn sót:</b> {remaining if remaining > 0 else 'Không xác định'}\n<b>Yêu cầu:</b> Can thiệp thủ công!"
        telegram_factory.send_tele(msg, cst.chat_id, True, True)
        logger.critical(f"🔴 Không thể hủy lệnh cho {symbol}!")

def do_it():
    global result_old, is_first_time  

    print(f"{datetime.now()}. hd_alert_possition_and_open_order----------------------------------------------------", flush=True)

    res = get_opened_possition()
    print(f"Tổng Lệnh: {len(res)}", flush=True)
    print(res, flush=True)

    
    
    

    if is_first_time:
        result_old = res
        is_first_time = False
        return

        
    


    
    for item in res:
        is_contain = False
        for item_old in result_old:
            if item["symbol"] == item_old["symbol"]:
                is_contain = True
                break

        if not is_contain:
            print(f"phần tử mới được thêm vào: {item}", flush=True)
            symbol = item['symbol']
            logger.info(f"✅ Position mới mở: {symbol} - Entry: {item.get('entryPrice', 'N/A')} - Amount: {item.get('positionAmt', 'N/A')} - Leverage: {item.get('leverage', 'N/A')}")
            notif_mgr.send_position_opened(symbol)


    
    for item_old in result_old:
        is_contain = False
        for item in res:
            if item["symbol"] == item_old["symbol"]:
                is_contain = True
                break

        if not is_contain:
            print(f"phần tử cũ được bỏ đi: {item_old}", flush=True)
            symbol = item_old['symbol']
            
            # Detect TP hay SL bằng cách check PnL
            pnl = float(item_old.get('unrealizedProfit', 0))
            is_tp = pnl > 0  # Profit = TP, Loss = SL
            
            # Lấy state hiện tại từ sheet để biết đang ở lớp nào
            try:
                # Xác định side dựa trên position_amt
                position_amt = float(item_old.get('positionAmt', 0))
                side = "LONG" if position_amt > 0 else "SHORT"
                
                tracker = get_tracker(side)
                state = tracker.get_current_state(
                    symbol=symbol,
                    start_row=55 if side == "LONG" else 4,
                    end_row=104 if side == "LONG" else 53
                )
                
                if state and state.get('order_code'):
                    order_code = state['order_code']
                    # Parse layer từ order_code (VD: "1a" -> layer 1)
                    try:
                        layer_num = int(order_code[0])
                    except:
                        layer_num = 1
                    
                    # Xử lý theo TP/SL
                    if is_tp:
                        logger.info(f"💰 TP khớp cho {symbol} lớp {layer_num} - Entry: {item_old.get('entryPrice', 'N/A')} - PnL: {pnl:.2f}")
                        cascade_mgr.on_tp_filled(symbol, layer_num)
                    else:
                        logger.info(f"🛑 SL khớp cho {symbol} lớp {layer_num} - Entry: {item_old.get('entryPrice', 'N/A')} - PnL: {pnl:.2f}")
                        cascade_mgr.on_sl_filled(symbol, layer_num)
                    
                    # Gửi thông báo đóng vị thế
                    notif_mgr.send_position_closed(symbol, pnl)
                    
                else:
                    # Không có state, chỉ báo đóng position thông thường
                    notif_mgr.send_position_closed(symbol)
                    
            except Exception as e:
                logger.error(f"Lỗi xử lý TP/SL cho {symbol}: {e}", exc_info=True)
                notif_mgr.send_position_closed(symbol)

            # Hủy tất cả lệnh chờ
            cancel_all_open_orders(symbol)


    result_old = res


    
    
    
    

    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    
    
    
    

    
    
    

    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

    
    

while True:
    try:

        do_it()
        

    except Exception as e:
        print(f"Tổng Lỗi: {e}", flush=True)
        logger.error(f"Tổng lỗi: {e}", exc_info=True)
        import traceback
        traceback.print_exc()

    time.sleep(cst.delay_calert_possition_and_open_order)
    