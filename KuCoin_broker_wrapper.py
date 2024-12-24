import base64
import hmac
import hashlib
import requests
import uuid
import json
class KuCoinHelper:
    def __init__(self,creds):
        self.BaseUrl = "https://api.kucoin.com"
        self.apiKey = creds['api_key']
        self.apiSecret = creds['api_secret']
        self.apiPassphrase = creds['api_passphrase']
        self.version = "v1"
        self.login = False
        self.authenticate()
    def getCurrentTime(self):
        '''This will fetch time from server in Unix timestamp'''
        data = self.makeRequest("GET", self.BaseUrl + "/api/v1/timestamp")
        if data.status_code != 200:
            raise Exception("Error in fetching time")
        data = data.json()
        return int(data['data'])
    def createSignaturesCheckSum(self, method,currentTime, parameter,data = None,version = None) -> str:
        '''This will create signature according to HMAC'''
        str_to_sign = str_to_sign = f"{str(currentTime)}{method}/api/"
        if version:
            str_to_sign += f"{version}/"
        else:
            str_to_sign += f"{self.version}/"
        str_to_sign += f"{parameter}"
        if data:
            str_to_sign += json.dumps(data)
        print(str_to_sign)
        signature = base64.b64encode(
            hmac.new(
                self.apiSecret.encode("utf-8"),
                str_to_sign.encode("utf-8"),
                hashlib.sha256
            ).digest())
        
        return signature
    def createPassPhraseSignature(self) -> str:
        '''This will create passphrase according to HMAC'''
        passphrase = base64.b64encode(
            hmac.new(
                self.apiSecret.encode('utf-8'),
                self.apiPassphrase.encode('utf-8'),
                hashlib.sha256
            ).digest()
        )
        return passphrase
    def createHeader(self,method,now,parameter,data=None,version = None):
        '''This will generate Header for API request'''
        header = {
            "KC-API-SIGN": self.createSignaturesCheckSum(method,now, parameter,data=data,version=version),
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": self.apiKey,
            "KC-API-PASSPHRASE": self.createPassPhraseSignature(),
            "KC-API-KEY-VERSION": "2"
        }
        if data:
            header['Content-Type'] = "application/json"
        return header
    def authenticate(self):
        '''Help in authenticating'''
        method = "GET"
        parameter = "accounts"
        now = self.getCurrentTime()
        url = self.BaseUrl + "/api/" + self.version + "/" + parameter
        headers = self.createHeader(method,now,parameter)
        response = self.makeRequest(method, url, headers)
        if response.status_code == 200:
            self.login = True
        else:
            self.login = False
        print(response.json())
        return response
    def makeRequest(self, method, url, headers=None,data = None):
        '''Make request and return response back'''

        try:
            if headers:
                if data:
                    response = requests.request(method, url, headers=headers,data=data)
                else :
                    response = requests.request(method, url, headers=headers)
            else:
                response = requests.request(method, url)

            return response

        except requests.exceptions.RequestException as e:
            return None
    def get_balance(self):
        '''This will return balance of all the coins'''
        method = "GET"
        parameter = "accounts"
        now = self.getCurrentTime()
        url = self.BaseUrl + "/api/" + self.version + "/" + parameter + f"/{self.apiKey}"
        print(url)
        headers = self.createHeader(method,now,parameter)
        response = self.makeRequest(method, url, headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '400100':
                print(f"Error: {data.get('msg')}")
                return None
            return data
        else:
            return None
    def fetch_ticker(self, symbol):
        '''This will return ticker for the symbol'''
        method = "GET"
        parameter = f"market/orderbook/level1"
        now = self.getCurrentTime()
        url = self.BaseUrl + "/api/" + self.version + "/" + parameter + f"?symbol={symbol}"
        headers = self.createHeader(method,now,parameter)
        response = self.makeRequest(method, url, headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    def load_markets(self,symbol='USDT'):
        '''This will load all the markets'''
        method = "GET"
        parameter = "markets"
        now = self.getCurrentTime()
        url = self.BaseUrl + "/api/" + self.version + "/" + parameter + f"?symbol={symbol}"
        headers = self.createHeader(method,now,parameter)
        response = self.makeRequest(method, url, headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    def fetch_ohlcv(self, symbol, timeframe='1hour',start = None, end= None, limit=250):
        '''This will return OHLCV data'''
        method = "GET"
        parameter = "market/candles"

        url = self.BaseUrl + "/api/" + self.version + "/" + parameter + f"?symbol={symbol}&type={timeframe}"
        if start and end:
            url += f"&startAt={start}&endAt={end}"
       
        response = self.makeRequest(method, url)
        if response.status_code == 200:
            data = response.json()['data']
            return data[:limit] if  len(data) >= limit else data
        else:
            return None
    def placeOrder(self, symbol, quantity, parms = {},stopOrder=False,ocoOrder=False, isFutures=False):
        '''This will place an order (buy or sell) and (limit or market)
        https://www.kucoin.com/docs/rest/spot-trading/orders/place-order
        '''
        version = None
        parms['clientOid'] = str(uuid.uuid1())
        parms['symbol'] = symbol
        parms['type'] = 'market' if "type" not in parms else parms['type']
        try:
            if quantity<=0:
                raise Exception("Quantity should be greater than 0")
            parms["size"] = quantity
            if ocoOrder and stopOrder:
                raise Exception("OCO and Stop Order can't be placed together")
            if parms['side'] not in ['buy', 'sell']:
                raise Exception("Invalid side (please use buy or sell)")
            if "remark" in parms and len(parms['remark']) > 50:
                raise Exception("Remark should be less than 50 characters")     
            if ocoOrder:
                if "stopPrice" not in parms or not isinstance(parms["stopPrice"], (int, float)) or parms["stopPrice"] <= 0:
                    raise Exception("Stop Price must be specified for OCO orders")
                if "price" not in parms or not isinstance(parms["price"], (int, float)) or parms["price"] <= 0:
                    raise Exception("Price must be specified for OCO orders")
            else :             
                if "type" in parms and parms['type'] not in ['limit', 'market']:
                    raise Exception("Invalid type (please use limit or market)")    
                if "stp" in parms and parms['stp'] not in ['CN', 'CO', 'CB', 'DC']:
                    raise Exception("Invalid stp value (please use CN, CO, CB, or DC)")
                if parms['type'] == 'limit' and "price" not in parms:
                    raise Exception("Price  must be specified for limit orders")
                   
                if stopOrder:
                    if "stopPrice" not in parms:
                        raise Exception("Stop Price must be specified for stop orders")
                    if "stopPrice" in parms and parms['stopPrice'] <= 0:
                        raise Exception("Stop Price must be greater than 0")
                    if "stopPrice" in parms and "stop" not in parms:
                        raise Exception("Stop must be specified for stop orders")
                    if "stopPrice" in parms and parms['stop'] not in ['loss', 'entry']:
                        raise Exception("Invalid stop value (please use loss or entry)")   
        except Exception as e:
            print(f"Error: {e}")
            return None

        data = parms
        method = "POST"
        if stopOrder:
            parameter = "stop-order"
        if isFutures:
            pass
        elif ocoOrder:
            parameter = "oco/order"
        else :
            parameter = "orders"
        now = self.getCurrentTime()
        url = self.BaseUrl + "/api/" + self.version + "/" + parameter

        if ocoOrder:
            url = self.BaseUrl + "/api/v3/" + parameter
            version = "v3"
        print(json.dumps(data))
        headers = self.createHeader(method, now, parameter, data, version=version)
        print(url)

        response = self.makeRequest(method, url, headers, data = json.dumps(data))
        if response.status_code == 200:
            return response.json()
        print("Status Code: ", response.status_code)
        print(f"Error while placing order: {response.json()}")
        return None
    def lastPrice(self, symbol):
        '''This will return last price of the symbol'''
        data = self.fetch_ticker(symbol)
        if data:
            return data['data']['price']
        return None
    def fetchOrDelete_order(self, orderid=None, symbol=None,delete = False, params={},isOco=False,isStop=False,isFutures=False,):
        '''This will fetch order details default it takes normal order'''
        version = self.version
        method = "DELETE" if delete else "GET"
        if isOco:
            version = "v3"
            parameter = f"oco/order"
            parameter+="/details" if not delete else ""
        elif isStop:
            parameter = f"stop-order"
        elif isFutures:
            pass
        else:
            parameter = f"order"
        parameter += f"/{orderid}"
        now = self.getCurrentTime()
        url = self.BaseUrl + "/api/" + version + "/" + parameter
        print(url)
        headers = self.createHeader(method, now, parameter,data=params,version=version)
        response = self.makeRequest(method, url, headers,data=json.dumps(params))
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error while fetching order: {response.json()}")
            return None
    
class KuCoin:
    def __init__(self, login_type, apikey, secretkey, passphrase, testnet=False, futures=False, broker="kucoin"):
        self.api_key = apikey
        self.secret_key = secretkey
        self.passphrase = passphrase
        self.trading_type = "spot" if not futures else "futures"
        self.broker = "KuCoin"

        self.wrapper = KuCoinHelper(
            {
            'api_key':self.api_key,
            'api_secret':self.secret_key,
            'api_passphrase':self.passphrase
            }
        )
        self.login = self.wrapper.login
        if not  self.login:
            raise Exception("Login Failed")

        self.sl_orders = []
        self.tp_orders = []
    def get_balance(self):
        return self.wrapper.get_balance()
    def fetch_ticker(self, symbol):
        return self.wrapper.fetch_ticker(symbol)
    def load_markets(self):
        return self.wrapper.load_markets()
    def fetch_ohlcv(self, symbol, timeframe='1h',start = None,end = None, limit=250):
        return self.wrapper.fetch_ohlcv(symbol, timeframe, limit= limit)
    def create_market_buy_order(self, symbol, quantity, params={"side":"buy"}):
        return self.wrapper.placeOrder(symbol, quantity,parms = params)
    def create_market_sell_order(self, symbol, quantity, params={"side":"sell"}):
        return self.wrapper.placeOrder(symbol, quantity,parms = params)
    def create_stop_market_order(self, symbol, side, amount, stopPrice, params={}):
        params['side'] = side
        params['stop'] = "loss"
        params['stopPrice'] = stopPrice
        return self.wrapper.placeOrder(symbol, amount,parms = params,stopOrder=True)
    def create_stop_limit_order(self, symbol, side, amount, price, stopPrice, params={}):
        params['side'] = side
        params['stop'] = "loss"
        params['stopPrice'] = stopPrice
        params['price'] = price
        params['type'] = "limit"
        return self.wrapper.placeOrder(symbol, amount,parms = params,stopOrder=True)
    def create_takeprofit(self, symbol, side, amount, takeProfitPrice):
        params = {}
        params['side'] = side
        params['stop'] = "entry"
        params['stopPrice'] = takeProfitPrice
        return self.wrapper.placeOrder(symbol, amount,parms = params,stopOrder=True)
    def create_takeprofit_limit(self, symbol, side, amount, price, takeProfitPrice):
        params = {}
        params['side'] = side
        params['stop'] = "entry"
        params['stopPrice'] = takeProfitPrice
        params['type'] = "limit"
        params['price'] = price
        return self.wrapper.placeOrder(symbol, amount,parms = params,stopOrder=True)
    def create_limit_buy_order(self, symbol, amount, price, params={}):
        params['side'] = "buy"
        params['type'] = "limit"
        params['price'] = price
        return self.wrapper.placeOrder(symbol, amount,parms = params)
    def create_limit_sell_order(self, symbol, amount, price, params={}):
        params['side'] = "sell"
        params['type'] = "limit"
        params['price'] = price
        return self.wrapper.placeOrder(symbol, amount,parms = params)
    def create_buy_oco_order(self,symbol,amount,stopPrice,takeProfitPrice):
        lastPrice = float(self.wrapper.lastPrice(symbol))
        if takeProfitPrice >= lastPrice:
            raise ValueError(f"Take profit price ({takeProfitPrice}) must be less than the last price ({lastPrice})")

        if stopPrice <= lastPrice:
            raise ValueError(f"Stop price ({stopPrice}) must be greater than the take last price ({lastPrice})")

        params = {}
        params['side'] = "buy"
        params['stopPrice'] = stopPrice
        params['price'] = takeProfitPrice
        params['limitPrice'] = takeProfitPrice
        return self.wrapper.placeOrder(symbol, amount,parms = params,ocoOrder=True)
    def create_sell_oco_order(self,symbol,amount,stopPrice,takeProfitPrice):
        lastPrice = float(self.wrapper.lastPrice(symbol))
        if takeProfitPrice <= lastPrice:
            raise ValueError(f"Take profit price ({takeProfitPrice}) must be greater than the last price ({lastPrice})")

        if stopPrice >= lastPrice:
            raise ValueError(f"Stop price ({stopPrice}) must be less than the take last price ({lastPrice})")

        params = {}
        params['side'] = "sell"
        params['stopPrice'] = stopPrice
        params['price'] = takeProfitPrice
        params['limitPrice'] = takeProfitPrice
        return self.wrapper.placeOrder(symbol, amount,parms = params,ocoOrder=True)
    def fetch_order(self, orderid, symbol, params={},isOco=False,isStop=False,isFutures=False):
        params['orderId'] = orderid
        return self.wrapper.fetchOrDelete_order(orderid, symbol, params,isOco,isStop,isFutures)
    def cancel_order(self, orderid, symbol, untriggered = False,isOco=False,isStop=False,isFutures=False):
        params = {}
        params['orderId'] = orderid
        return self.wrapper.fetchOrDelete_order(orderid, symbol, params=params,isOco=True,delete=True)



if __name__ == "__main__":
    api_key = "your_api_key"
    api_secret = "your_api_secret"
    api_passphrase = "your_api_passphrase"
    kucoin = KuCoin("API", api_key, api_secret, api_passphrase)
    # print(kucoin.get_balance())
    # print(kucoin.fetch_ticker("BTC-USDT"))
    # print(kucoin.load_markets())
    # print(len(kucoin.fetch_ohlcv("BTC-USDT","1min",limit=10)))
    # print(kucoin.create_market_buy_order("BTC-USDT",0.0001))

    # print(kucoin.create_market_sell_order("BTC-USDT",0.0001))
    # print(kucoin.create_stop_market_order("BTC-USDT","sell",0.0001, 50000))
    # print(kucoin.create_stop_limit_order("BTC-USDT","sell",0.0001, 50000, 50001))
    # print(kucoin.create_takeprofit("BTC-USDT","sell",0.0001, 50001))
    # print(kucoin.create_takeprofit_limit("BTC-USDT","sell",0.0001, 50000, 50001))
    # print(kucoin.create_limit_buy_order("BTC-USDT",0.0001, 50000))
    # print(kucoin.create_limit_sell_order("BTC-USDT",0.0001, 50000))
    # print(kucoin.create_buy_oco_order("BTC-USDT",0.0001, 95000,90000))
    # print(kucoin.create_sell_oco_order("BTC-USDT",0.0001, 90000,95000))
    # print(kucoin.fetch_order("676a325e7b793e00076e63dd","BTC-USDT",isOco=True,))
    # print(kucoin.cancel_order("676a325e7b793e00076e63dd","BTC-USDT",isOco=True))



