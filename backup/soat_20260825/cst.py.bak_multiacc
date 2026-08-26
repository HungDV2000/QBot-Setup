import configparser

config = configparser.ConfigParser()
with open('config.ini', encoding='utf-8') as file:
    config.read_file(file)

is_print_mode = config.getboolean('global', 'is_print_mode')
top_count = config.getint('global', 'top_count')
time_gap_do_it = config.getint('global', 'time_gap_do_it')
bot_token = config.get('global', 'bot_token')
chat_id = config.get('global', 'chat_id')
prefix_channel = config.get('global', 'prefix_channel', fallback='')

key_name = config.get('global', 'key_name')
key_binance = config.get('global', 'key_binance')
secret_binance = config.get('global', 'secret_binance')
test_mode = config.getboolean('global', 'test_mode')
spreadsheet_id = config.get('global', 'spreadsheet_id')
tab_dat_lenh = config.get('global', 'tab_dat_lenh')

delay_vao_lenh = config.getint('global', 'delay_vao_lenh')
delay_vao_lenh_123 = config.getint('global', 'delay_vao_lenh_123')
delay_cho_va_khop = config.getint('global', 'delay_cho_va_khop')
delay_update_price = config.getint('global', 'delay_update_price')
delay_update_all = config.getint('global', 'delay_update_all')
delay_calert_possition_and_open_order = config.getint('global', 'delay_calert_possition_and_open_order')

lenh2_rate_long = config.getfloat('global', 'lenh2_rate_long')
lenh2_rate_short = config.getfloat('global', 'lenh2_rate_short')
lenh3_rate_long = config.getfloat('global', 'lenh3_rate_long')
lenh3_rate_short = config.getfloat('global', 'lenh3_rate_short')
lenh3_callback_rate = config.getfloat('global', 'lenh3_callback_rate')
# O trống / NGAY → TP trailing kích hoạt ngay tại giá mark/last (phương án A)
lenh3_o_empty_immediate = config.getboolean('global', 'lenh3_o_empty_immediate', fallback=True)
cancel_orders_minutes = config.getint('global', 'cancel_orders_minutes')
max_increase_decrease_4h_day_count = config.getint('global', 'max_increase_decrease_4h_day_count')

# Phase 3 & 4 delays
delay_track_30_prices = config.getint('global', 'delay_track_30_prices')
delay_periodic_report = config.getint('global', 'delay_periodic_report')

# Telegram command bot: True = folder này chạy listener (nhận lệnh); False = chỉ chạy hd_order, không nhận lệnh
# Mặc định False: nếu config.ini chưa có run_tele_command thì không chạy (tránh bật nhầm)
run_tele_command = config.getboolean('global', 'run_tele_command', fallback=False)

# hd_update_all: ghi logs/column_audit_LAST.json (+ file theo timestamp) cho đúng 1 mã — để đối chiếu từng cột (để trống = tắt)
debug_column_audit_symbol = config.get('global', 'debug_column_audit_symbol', fallback='').strip()

# hd_update_all: ghi log [PROFILE] thời gian từng phase (fetch_tickers, batch get_row, sheet…). false = log gọn hơn
profile_do_it = config.getboolean('global', 'profile_do_it', fallback=True)

# ─────────────────────────────────────────────────────────────────────────────
# [TASK 1] Default values cho sheet "Chờ và khớp" (cột J-S)
# Tất cả đều có fallback cứng — file config.ini cũ vẫn chạy được.
# ─────────────────────────────────────────────────────────────────────────────

# % phân bổ qty theo 3 lớp (tổng phải = 100, mặc định 40/40/20)
default_ratio_layer_1 = config.getfloat('global', 'default_ratio_layer_1', fallback=40.0)
default_ratio_layer_2 = config.getfloat('global', 'default_ratio_layer_2', fallback=40.0)
default_ratio_layer_3 = config.getfloat('global', 'default_ratio_layer_3', fallback=20.0)

# % SL (cắt lỗ) cho 3 lớp — tính từ entry price
# LONG: SL_price = entry × (1 - rate/100);  SHORT: SL_price = entry × (1 + rate/100)
default_sl_rate_layer_1 = config.getfloat('global', 'default_sl_rate_layer_1', fallback=2.0)
default_sl_rate_layer_2 = config.getfloat('global', 'default_sl_rate_layer_2', fallback=5.0)
default_sl_rate_layer_3 = config.getfloat('global', 'default_sl_rate_layer_3', fallback=10.0)

# % TP (chốt lời) cho 3 lớp — tính từ entry price
# LONG: TP_price = entry × (1 + rate/100);  SHORT: TP_price = entry × (1 - rate/100)
default_tp_rate_layer_1 = config.getfloat('global', 'default_tp_rate_layer_1', fallback=3.0)
default_tp_rate_layer_2 = config.getfloat('global', 'default_tp_rate_layer_2', fallback=6.0)
default_tp_rate_layer_3 = config.getfloat('global', 'default_tp_rate_layer_3', fallback=10.0)

# Cột S "Cho phép đặt lệnh" — mặc định N (user phải chủ động đổi sang Y)
default_allow_order = config.get('global', 'default_allow_order', fallback='N').strip().upper()
# Bật/tắt tính năng auto-fill default (tắt → cột J-S luôn rỗng như trước)
fill_default_cho_va_khop = config.getboolean('global', 'fill_default_cho_va_khop', fallback=True)

