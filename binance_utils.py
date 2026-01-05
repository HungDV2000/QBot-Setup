import ccxt
import cst

def get_price_precision(sym):
    if("/" not in sym):
        sym = sym.replace("USDT", "/USDT")
    
    exchange = ccxt.binance({
            'apiKey': cst.key_binance,
            'secret': cst.secret_binance,
            'options': {
                'defaultType': 'future',
            }
        })

    
    markets = exchange.load_markets()

    
    symbol = f'{sym}:USDT'

    
    if symbol in markets:
        
        market = markets[symbol]

        
        price_precision = market['precision']['price']
        amount_precision = market['precision']['amount']
        return int(price_precision)
        
        
    else:
        print(f"Cặp giao dịch {symbol} không tồn tại trên Binance futures.")

pr = get_price_precision("PEOPLE/USDT")
print(pr)