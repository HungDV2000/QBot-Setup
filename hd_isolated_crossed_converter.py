import ccxt
from pprint import pprint
import time
import cst  

sleep_gap = 0
def toggle_isolated_margin(exchange, enable_isolated=True):
    """
    Enable or disable isolated margin for USDT-M futures pairs (:USDT).
    
    Args:
        exchange: CCXT exchange object (Binance)
        enable_isolated: True for ISOLATED, False for CROSS
    
    Returns:
        dict: Results with processed pairs and their status
    """
    margin_type = 'ISOLATED' if enable_isolated else 'CROSSED'
    result = {'success': [], 'failed': [], 'skipped': []}
    
    try:
        
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

        
        markets = exchange.markets
        futures_symbols = [symbol for symbol in markets.keys() 
                         if symbol.endswith('/USDT:USDT') 
                         and markets[symbol].get('type') == 'swap' 
                         and not any(suffix in symbol for suffix in ['UP/USDT', 'DOWN/USDT', 'BULL/USDT', 'BEAR/USDT'])]

        
        print("Debug: Market info for USDT pairs:")
        for symbol in markets.keys():
            if 'USDT' in symbol:
                market = markets[symbol]
                print(f"Symbol: {symbol}, Type: {market.get('type')}, Quote: {market.get('quote')}, ID: {market['id']}")

        print(f"Total {len(futures_symbols)} USDT futures pairs (:USDT) found:")
        pprint(futures_symbols)

        if not futures_symbols:
            raise Exception("No USDT futures pairs (:USDT) found.")

        
        for symbol in futures_symbols:
            print(f"\nProcessing pair: {symbol}")
            try:
                
                positions = exchange.fapiPrivateV2GetPositionRisk({'symbol': exchange.market(symbol)['id']})
                if any(float(pos['positionAmt']) != 0 for pos in positions):
                    print(f"Cannot switch {symbol}: Open positions exist.")
                    result['skipped'].append({symbol: 'Open positions exist'})
                    continue

                
                open_orders = exchange.fapiPrivateGetOpenOrders({'symbol': exchange.market(symbol)['id']})
                if open_orders:
                    print(f"Cannot switch {symbol}: Open orders exist.")
                    result['skipped'].append({symbol: 'Open orders exist'})
                    continue

                
                symbol_id = exchange.market(symbol)['id']
                request = {
                    'symbol': symbol_id,
                    'marginType': margin_type.upper()
                }
                print(f"API request for {symbol}: {request}")

                
                try:
                    response = exchange.fapiPrivatePostMarginType(request)
                    print(f"Successfully switched {symbol} to {margin_type} mode:")
                    pprint(response)
                    result['success'].append({symbol: response})
                except ccxt.ExchangeError as e:
                    print(f"Standard call failed for {symbol}: {e}")
                    if "code=-1102" in str(e):
                        print(f"Error -1102 for {symbol}. Retrying with 'margintype'...")
                        alt_request = {
                            'symbol': symbol_id,
                            'margintype': margin_type.upper()
                        }
                        print(f"Alternative API request for {symbol}: {alt_request}")
                        response = exchange.fapiPrivatePostMarginType(alt_request)
                        print(f"Successfully switched {symbol} to {margin_type} mode (retry):")
                        pprint(response)
                        result['success'].append({symbol: response})
                    
                    
                    
                    
                    
                    
                    
                    else:
                        raise e

            except ccxt.ExchangeError as e:
                print(f"Error switching {symbol}: {e}")
                if "code=-4046" in str(e):
                    print(f"{symbol} is already in {margin_type} mode.")
                    result['skipped'].append({symbol: f"Already in {margin_type} mode"})
                elif "code=-4059" in str(e):
                    print(f"{symbol} has open positions or orders, cannot switch.")
                    result['skipped'].append({symbol: 'Open positions/orders'})
                else:
                    result['failed'].append({symbol: str(e)})
            except Exception as e:
                print(f"Unknown error processing {symbol}: {e}")
                result['failed'].append({symbol: str(e)})

            time.sleep(sleep_gap)  

        return result

    except Exception as e:
        print(f"General error: {e}")
        result['failed'].append({'general': str(e)})
        return result


if __name__ == "__main__":
    
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

    try:
        
        while True:
            print("\nChoose margin mode:")
            print("1: Switch to CROSS")
            print("2: Switch to ISOLATED")
            choice = input("Enter your choice (1 or 2): ").strip()
            
            if choice == '1':
                enable_isolated = False
                mode = "CROSS"
                break
            elif choice == '2':
                enable_isolated = True
                mode = "ISOLATED"
                break
            else:
                print("Invalid choice! Please enter 1 or 2.")

        
        print(f"\n=== Switching to {mode} margin ===")
        result = toggle_isolated_margin(exchange, enable_isolated=enable_isolated)
        print(f"\nResult for {mode}:")
        pprint(result)

    except ccxt.NetworkError as e:
        print(f"Network error: {e}. Check internet connection or Binance API status: https://status.binance.com/.")
    except ccxt.AuthenticationError as e:
        print(f"Authentication error: {e}. Check API key and secret in cst.")
    except Exception as e:
        print(f"Unknown error: {e}")

    input("Press Enter to exit...")