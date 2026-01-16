"""
Periodic Report - Module gửi báo cáo định kỳ về số dư và trạng thái
Chạy mỗi 5 phút để kiểm tra và gửi báo cáo khi cần
"""

import ccxt
import logging
import time
from datetime import datetime
import cst
from notification_manager import get_notification_manager
import os
from pathlib import Path

file_name = os.path.basename(os.path.abspath(__file__))  
os.system(f"title {file_name} - {cst.key_name}")

# Tạo thư mục logs/ nếu chưa có
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Tạo tên file log với timestamp: hd_periodic_report_dd_mm_yyyy_H_M_S.txt
log_timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
log_filename = logs_dir / f'hd_periodic_report_{log_timestamp}.txt'

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

# Setup exchange
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

# Notification manager
notif_mgr = get_notification_manager(cst.chat_id)


def get_balance_info():
    """
    Lấy thông tin số dư và tính toán
    
    Returns:
        Dict with keys: wallet_balance, margin_balance, unrealized_pnl, 
                        unrealized_pnl_percent, open_positions_count, pending_orders_count
    """
    try:
        balance = exchange.fetch_balance()
        
        wallet_balance = float(balance['info']['totalWalletBalance'])
        margin_balance = float(balance['info']['totalMarginBalance'])
        unrealized_pnl = float(balance['info']['totalCrossUnPnl'])
        
        # Tính % PNL
        if wallet_balance > 0:
            unrealized_pnl_percent = (unrealized_pnl / wallet_balance) * 100
        else:
            unrealized_pnl_percent = 0.0
        
        # Đếm vị thế đang mở
        positions = balance['info']['positions']
        open_positions_count = sum(1 for p in positions if float(p['positionAmt']) != 0)
        
        # Đếm lệnh chờ
        try:
            all_orders = exchange.fetch_open_orders()
            pending_orders_count = len(all_orders)
        except:
            pending_orders_count = 0
        
        return {
            'wallet_balance': wallet_balance,
            'margin_balance': margin_balance,
            'unrealized_pnl': unrealized_pnl,
            'unrealized_pnl_percent': unrealized_pnl_percent,
            'open_positions_count': open_positions_count,
            'pending_orders_count': pending_orders_count
        }
        
    except Exception as e:
        logger.error(f"Lỗi lấy thông tin balance: {e}")
        return None


def do_it():
    """Main loop - Kiểm tra và gửi báo cáo"""
    # Chỉ log ERROR, không log INFO (theo yêu cầu)
    balance_info = get_balance_info()
    
    if balance_info:
        # Gửi báo cáo (notification manager tự kiểm tra điều kiện)
        notif_mgr.send_balance_report(
            wallet_balance=balance_info['wallet_balance'],
            margin_balance=balance_info['margin_balance'],
            unrealized_pnl=balance_info['unrealized_pnl'],
            unrealized_pnl_percent=balance_info['unrealized_pnl_percent'],
            open_positions_count=balance_info['open_positions_count'],
            pending_orders_count=balance_info['pending_orders_count'],
            force_send=False  # Không bắt buộc, để manager tự quyết định
        )
    else:
        logger.error("Không lấy được thông tin balance", exc_info=True)


if __name__ == "__main__":
    # Gửi báo cáo đầu tiên ngay lập tức
    balance_info = get_balance_info()
    if balance_info:
        notif_mgr.send_balance_report(
            wallet_balance=balance_info['wallet_balance'],
            margin_balance=balance_info['margin_balance'],
            unrealized_pnl=balance_info['unrealized_pnl'],
            unrealized_pnl_percent=balance_info['unrealized_pnl_percent'],
            open_positions_count=balance_info['open_positions_count'],
            pending_orders_count=balance_info['pending_orders_count'],
            force_send=True  # Bắt buộc gửi lần đầu
        )
    
    while True:
        try:
            do_it()
        except Exception as e:
            logger.error(f"Tổng lỗi: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
        
        # Sleep 5 phút
        sleep_time = getattr(cst, 'delay_periodic_report', 300)  # Default 5 minutes
        time.sleep(sleep_time)

