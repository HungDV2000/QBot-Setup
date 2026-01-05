from ccxt import binanceusdm
import os
import sys
from pprint import pprint
from pathlib import Path
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root + '/python')

import ccxt  


print('CCXT Version:', ccxt.__version__)
class Properties:
    def __init__(self, properties):
        self.properties = properties
        

    def get(self,name):
        if name in self.properties:
            return self.properties[str(name)]
        else:
            return ""
def printf(name,data):
    print(data)
    pathDir=str(Path().absolute()).replace("\\","/")
    filename=pathDir+"/order/"+str(name)+"/"+str(data['info']['orderId'])+".txt"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    f = open(filename, "w")
    f.write(str(data))
    f.close()    


def cancel_all_open_orders(symbol):
    open_orders = exchange.fetch_open_orders(symbol)

    if open_orders:
        for order in open_orders:
            order_id = order['id']
            cancel_result = exchange.cancel_order(order_id, symbol)
            print(f"Hủy lệnh {order_id} kết quả: {cancel_result}")
    else:
        print(f"Không có lệnh mở nào cho {symbol}")

def command(command_data):
    properties = {}

    for str in command_data.split(","):
        try:
            key_value = str.split("=")
            if len(key_value) == 2:
                properties[key_value[0].strip()] = key_value[1].strip()
        except Exception as e:
            pass

    type = properties.get("type")
    if type == "BUY":
        properties["side"] = "BUY".lower()
    elif type == "SELL" or type == "SHORT":
        properties["side"] = "SELL".lower()
    elif type == "COVER":
        properties["side"] = "BUY".lower()

    return Properties(properties)

def order():
    global properties
    symbol = properties.get("symbol")
    side = properties.get("side")
    type = properties.get("type")
    positionSide = properties.get("positionSide")
    orderType = properties.get("orderType")
    quantity = properties.get("quantity")
    price = properties.get("price")
    reduceOnly = properties.get("reduceOnly")
    newClientOrderId = properties.get("newClientOrderId")
    stopPrice = properties.get("stopPrice")
    limitPrice = properties.get("limitPrice")
    stopPercent = properties.get("stopPercent")
    maxPositions = properties.get("maxPositions")
    capitalMoney = properties.get("capitalMoney")
    maxOpenOrders = properties.get("maxOpenOrders")
    maxQuantity = properties.get("maxQuantity")
    capital = properties.get("capital")
    trailingRate = properties.get("trailingRate")
    trailingPrice = properties.get("trailingPrice")
    
    ticker =exchange.fetch_ticker(symbol)
    lastPrice=ticker["last"]

    amountUsdt=float(capitalMoney)

    amount =amountUsdt/lastPrice

    
    try:
        leverage = int(properties.get("leverage"))
        if(leverage>0):
            exchange.setLeverage (leverage, symbol)
            print(f"Đã thiết lập đòn bẩy {leverage} cho cặp giao dịch {symbol}")
    except Exception as e:
        print()



    
    
    
        
    if trailingRate :
        rate = float(trailingRate)
        if rate >0:

            price = None
            if trailingPrice:
                price = float(trailingPrice)

            params = {
                'stopPrice': stopPrice,
                'callbackRate': rate
            }
        order = exchange.create_order(symbol, orderType, side, amount, price, params)

    
        
    else:
        order = exchange.create_order(symbol, orderType, side, amount)

    printf(symbol,order)

    
    if float(stopPercent) >0:
        entry_price = order['price']
        print(f"entry_price = {entry_price}")
        if not leverage:
            leverage = 1

        print(f"leverage={leverage}")
        stp = 1-float(stopPercent)/100.0

        
        stopLossPrice = entry_price*(1-stp/leverage) if side == 'buy' else entry_price*(1+stp/leverage)
        
        
        print(f"stopLossPrice = {stopLossPrice}")
        inverted_side = 'sell' if side == 'buy' else 'buy'
        stopLossParams = {'stopPrice': stopLossPrice}
        stopLossOrder = exchange.create_order(symbol, 'STOP_MARKET', inverted_side, amount, lastPrice, stopLossParams)
        print(stopLossOrder)

def close():
    global properties
    symbol = properties.get("symbol")
    side = properties.get("side")
    type = properties.get("type")
    positionSide = properties.get("positionSide")
    orderType = properties.get("orderType")
    quantity = properties.get("quantity")
    price = properties.get("price")
    reduceOnly = properties.get("reduceOnly")
    newClientOrderId = properties.get("newClientOrderId")
    stopPrice = properties.get("stopPrice")
    stopPercent = properties.get("stopPercent")
    maxPositions = properties.get("maxPositions")
    maxOpenOrders = properties.get("maxOpenOrders")
    capital = properties.get("capital")
    capitalMoney = properties.get("capitalMoney")
    capitalClose = properties.get("capitalClose")

    positions=exchange.fetch_positions([symbol])[0]["info"]
    amount=0.0 
    
    if capitalClose=="100":
        amount= (float(positions["positionAmt"]))
    else:
        amount= (float(positions["positionAmt"])*(float(capitalClose)/100.0))

    if type in "COVER" and amount<0:
        amount=abs(amount)
    elif  type in "SELL" and amount>0:
        amount=abs(amount)
    else:
        return
    order = exchange.create_order(symbol, orderType, side, amount)
    printf(symbol,order)
    cancel_all_open_orders(symbol)


def cancel_all_orders(symbol=None):
    try:
        if symbol:
            open_orders = exchange.fetch_open_orders(symbol)
        else:
            open_orders = exchange.fetch_open_orders()
        
        for order in open_orders:
            order_id = order['id']
            exchange.cancel_order(order_id, order['symbol'])
            print(f"Canceled order {order_id} for {order['symbol']}")
    except Exception as e:
        print(f"An error occurred: {e}")












argv=sys.argv
properties=command(argv[3])
exchange = ccxt.binance({
        'apiKey': argv[1],
        'secret': argv[2],
        'options': {
            'defaultType': 'future',
        }
    })

markets = exchange.load_markets()
exchange.verbose = False


type = properties.get("type")
if type in "BUY" or type in "SHORT":
    order()
else:
    if type in "CANCEL":
        symbol = properties.get("symbol")

        cancel_all_orders(symbol)
    else:
        close()


sys.exit(0)