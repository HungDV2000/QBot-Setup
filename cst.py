import configparser

config = configparser.ConfigParser()
with open('config.ini', encoding='utf-8') as file:
    config.read_file(file)

is_print_mode = config.getboolean('global', 'is_print_mode')
top_count = config.getint('global', 'top_count')
time_gap_do_it = config.getint('global', 'time_gap_do_it')
bot_token = config.get('global', 'bot_token')
chat_id = config.get('global', 'chat_id')

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
cancel_orders_minutes = config.getint('global', 'cancel_orders_minutes')
max_increase_decrease_4h_day_count = config.getint('global', 'max_increase_decrease_4h_day_count')

# Phase 3 & 4 delays
delay_track_30_prices = config.getint('global', 'delay_track_30_prices')
delay_periodic_report = config.getint('global', 'delay_periodic_report')

