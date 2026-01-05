import ccxt
from pprint import pprint
import time
import cst  
import gg_sheet_factory

print(f"CCXT version: {ccxt.__version__}")


exchange_class = getattr(ccxt, 'binance')
exchange = exchange_class({
    'enableRateLimit': True,
    'apiKey': cst.key_binance,
    'secret': cst.secret_binance,
    'options': {
        'defaultType': 'swap'  
    }
})


exchange.urls['api']['fapi'] = 'https://fapi.binance.com'


max_retries = 3
for attempt in range(max_retries):
    try:
        exchange.load_markets(reload=True)
        print("Markets loaded successfully.")
        break
    except Exception as e:
        print(f"Error loading markets (attempt {attempt + 1}/{max_retries}): {e}")
        if attempt < max_retries - 1:
            time.sleep(5)
        else:
            raise Exception("Failed to load markets after retries.")


try:
    exchange_info = exchange.fapiPublicGetExchangeInfo()
    active_futures_symbols = [
        s['symbol'] for s in exchange_info['symbols']
        if s['status'] == 'TRADING'
        and s['symbol'].endswith('USDT')
        and s['contractType'] == 'PERPETUAL'
    ]
    print(f"Total {len(active_futures_symbols)} active perpetual futures pairs from exchangeInfo:")
    pprint(active_futures_symbols)
except Exception as e:
    print(f"Error fetching exchangeInfo: {e}")
    raise Exception("Failed to fetch active futures pairs from exchangeInfo.")


markets = exchange.markets
futures_symbols = []
delisted_symbols = []
for symbol in markets.keys():
    market = markets[symbol]
    if (symbol.endswith('/USDT:USDT')
        and market.get('type') == 'swap'
        and not any(suffix in symbol for suffix in ['UP/USDT', 'DOWN/USDT', 'BULL/USDT', 'BEAR/USDT'])):
        symbol_id = market['id']  
        if symbol_id in active_futures_symbols:
            
            try:
                ticker = exchange.fapiPublicGetTickerPrice({'symbol': symbol_id})
                if 'price' in ticker:
                    futures_symbols.append(symbol.replace(':USDT', ''))
                else:
                    delisted_symbols.append(symbol.replace(':USDT', ''))
                    print(f"Excluded {symbol}: No valid price in ticker.")
            except ccxt.ExchangeError as e:
                delisted_symbols.append(symbol.replace(':USDT', ''))
                print(f"Excluded {symbol}: Ticker error - {e}")
        else:
            delisted_symbols.append(symbol.replace(':USDT', ''))


print("Debug: Market info for USDT pairs:")
for symbol in markets.keys():
    if 'USDT' in symbol:
        market = markets[symbol]
        print(f"Symbol: {symbol}, Type: {market.get('type')}, Quote: {market.get('quote')}, ID: {market['id']}, Status: {market.get('status')}")

print(f"Total {len(futures_symbols)} active USDT futures pairs found:")
pprint(futures_symbols)
if delisted_symbols:
    print(f"Total {len(delisted_symbols)} delisted or non-trading USDT futures pairs found:")
    pprint(delisted_symbols)


futures_symbols = sorted(futures_symbols)


futures_symbols_2d = [[symbol] for symbol in futures_symbols]


try:
    gg_sheet_factory.clear_multi("Danhmuc", -1, "a")
    gg_sheet_factory.update_multi("Danhmuc", -1, futures_symbols_2d, "a")
    print("Successfully updated Google Sheet 'Danhmuc' with active futures pairs.")
except Exception as e:
    print(f"Error updating Google Sheet: {e}")
