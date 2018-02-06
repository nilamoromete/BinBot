"""
@author: Mike Anthony G
"""

from binance.client import Client
import operator
import binance_config
import binance.enums as enum
import binance.exceptions as binexc
import time
import datetime
import math

    
class BinBot(object):
    def __init__(self):
        self.client = Client(binance_config.api_key, binance_config.api_secret)
        self.fee = 0.0005 #if user has BNB tokens
        self.orderbook = self.get_orderbook_total()
        self.bit_rate = self.extract_btc_eth_rate(self.orderbook)
        self.update_orderbook()
        self.symbol_keys = self.get_keys(self.orderbook) 
        self.current_btc, self.current_eth = self.update_account()
        
    def get_orderbook_total(self):
        """ Returns orderbook from binance package. """
        return self.client.get_orderbook_tickers()
    
    def update_orderbook(self):
        """ Updates orderbook by analyzing exchange rates in BTC and removing
            coins in no_trade in binance_config. 
        """
        try:
            self.orderbook = self.get_orderbook_total()
            self.bit_rate = self.extract_btc_eth_rate(self.orderbook)
            self.orderbook = self.modify_orderbook(self.orderbook)
        except binexc.BinanceAPIException as e:
            print(e.status_code)
            print(e.message)
            time.sleep(10)
            self.update_orderbook()
    
    def update_account(self):
        """ Returns the amount of BTC or ETH in the account. """
        flag = False
        #If local time compared to Binance NTP server time is offset by +1000ms then API will throw error
        while(flag == False):
            try:
                acc = self.client.get_account(recvWindow = binance_config.recv_window)
                flag = True
            except binexc.BinanceAPIException as e:
                print(str(e.status_code) + " : " + e.message)
                time.sleep(1)
        btc_eth = []
        for k in acc['balances']:
            if(k['asset'] == 'BTC' or k['asset'] == 'ETH'):
                btc_eth.append(k['free'])
            if(len(btc_eth) == 2):
                break
        if(btc_eth[0] >= btc_eth[1]):
            return btc_eth[0], btc_eth[1]
        else:
            return btc_eth[1], btc_eth[0]
    
    def alt_asset_amount(self, symbol, symbol_length=3):
        """ Returns the total amount of an altcoin on the account.
        
            Keyword Arguments:
            symbol -- the symbol of the altcoin e.g. 'NEO'
            symbol_length -- 'NEO' will have symbol_length of 3
                             'LINK' will have symbol_length of 4
                              Work around for the API
                              (default 3)
        """
                
        acc = self.client.get_account(recvWindow = binance_config.recv_window)
        for k in acc['balances']:
            if(k['asset'] == symbol[0, symbol_length]):
                return k['free']
        return "Symbol Not Found"
        
    def get_keys(self, orderbook):
        """ Returns symbols of all coins on Binance """
        _keys = []
        for k in orderbook:
            _keys.append(list(k.keys())[0])
        return _keys
    
    def extract_btc_eth_rate(self, orderbook):
        """ Returns ETHBTC exchange rate """
        for i in range(0, len(orderbook)):
            if(orderbook[i]['symbol'][0:6] == 'ETHBTC'):
                odbk = orderbook[i]
                odbk['btc_one'] = 1 / float(odbk['askPrice'])
                return orderbook[i]
        
    def modify_orderbook(self, orderbook):
        """ Helper function to modify orderbook to remove trading pairs that
            are not involved eg BTCUSDT """
        ob_sorted = sorted(orderbook, key=lambda k:k['symbol'])
        ob_sorted = self.del_non_pair_coins(ob_sorted)
        ob_dict = self.transform_data_list(ob_sorted)
        return ob_dict


    def del_non_pair_coins(self, orders):
        """ Deletes coins that are no longer listed on Binance as well as coins 
            listed on the binance_config.no_trade list
        """
        i = 0
        orders_to_return = []
        while(i < len(orders)-1):
            if(orders[i]['symbol'][0:3] == orders[i+1]['symbol'][0:3]):
                if(orders[i]['symbol'] == 'ETC' or orders[i]['symbol'][-4:] == 'USDT'
                   or orders[i]['symbol'][0:4] in binance_config.no_trade or 
                   orders[i]['symbol'][0:3] in binance_config.no_trade or
                   orders[i]['symbol'][-3:] == 'BNB'):
                    i += 1
                elif(orders[i+1]['symbol'][-4:] == 'USDT'):
                    i += 1
                else:
                    orders_to_return.append(orders[i])
                    orders_to_return.append(orders[i+1])
                    i += 2
            else:
                i += 1    
        return orders_to_return
     
    def transform_data_list(self, orders):
        """ Transforms data from dictionary into list(BTC=0, ETH=1) """
        transform = []
        for i in range(0, len(orders), 2):
            transform.append({orders[i]['symbol'][0:3]: [orders[i], orders[i+1]]})
        return transform    
        
    def orderbook_btc_eth(self, orderbook):
        """ Looks for viable trading pairs in the BTC --> ETH direction """
        btc_to_eth = {}
        btc_pos = 0
        eth_pos = 1
        for k in orderbook:
            try:
                btc_to_eth[list(k.keys())[0]] = 1 / float(k[list(k.keys())[0]][btc_pos]['askPrice']) * float(k[list(k.keys())[0]][eth_pos]['bidPrice'])
            except ZeroDivisionError as e:
                print(e)
        return sorted(btc_to_eth.items(), key=operator.itemgetter(1), reverse=True)
    
    def orderbook_eth_btc(self, orderbook):
        """ Looks for viable trading pairs in the ETH --> BTC direction """
        eth_to_btc = {}
        btc_pos = 0
        eth_pos = 1
        for k in orderbook:
            try:
                eth_to_btc[list(k.keys())[0]] = 1 / float(k[list(k.keys())[0]][eth_pos]['askPrice']) * float(k[list(k.keys())[0]][btc_pos]['bidPrice'])
            except ZeroDivisionError as e:
                print(e)
        return sorted(eth_to_btc.items(), key=operator.itemgetter(1), reverse=True)
    
    #Without client validation - no google authenticator
    #symbol - string,   quantity = int, price = string -- must be 0.0002
    def order_buy_alt(self, _symbol, _quantity, _price, order_rank, attempt=1):
        """ Buys an altcoin using Binance package
            
            Keyword Arguments:
            _symbol -- String: Symbol name of trading pair eg NEOBTC 
            _quantity -- Integer: Quantity to buy
            _price -- String: Price to buy at
            order_rank -- Integer: The order of buy/sell exection
            attempt -- Integer: Total of attempts to buy at the price
        """
        try:
            self.client.create_order(symbol=_symbol,
                                        side = enum.SIDE_BUY,
                                        type = enum.ORDER_TYPE_LIMIT,
                                        timeInForce = enum.TIME_IN_FORCE_GTC,
                                        quantity = _quantity,
                                        price = _price,
                                        disable_validation=True)
            return True
        except binexc.BinanceAPIException as e:
            print(e.status_code, e.message, " | order_buy_alt")
            return False

    def order_sell_alt(self, _symbol, _quantity, _price, order_rank, attempt=1):
        """ Sells an altcoin using Binance package
            
            Keyword Arguments:
            _symbol -- String: Symbol name of trading pair eg NEOBTC 
            _quantity -- Integer: Quantity to buy
            _price -- String: Price to buy at
            order_rank -- Integer: The order of buy/sell exection
            attempt -- Integer: Total of attempts to buy at the price
        """
        try:
            self.client.create_order(symbol=_symbol,
                                        side = enum.SIDE_SELL,
                                        type = enum.ORDER_TYPE_LIMIT,
                                        timeInForce = enum.TIME_IN_FORCE_GTC,
                                        quantity = _quantity,
                                        price = _price,
                                        disable_validation=True)                                         
        except binexc.BinanceAPIException as e:
            #print(e.message, e.status_code, " | order_sell_alt")
            if(order_rank is 4 or order_rank is 2):
                if(attempt <= 25):
                    attempt += 1
                    self.order_sell_alt(_symbol, _quantity, _price, order_rank, attempt)
                    time.sleep(0.02)
            else:
                print("Went to market price | order_sell_alt", e.message, e.status_code)
                self.order_sell_market(_symbol, _quantity)
                
    def order_sell_market(self, _symbol, _quantity):
        """Sells coins into either ETH or BTC at MARKET VALUE.
            Use for upgrades for flexibility of binbot
                Say the order you originally placed was bought before your order arrived
                on the binance servers. This will immediately sell your coins and depending
                on the fluctuation of the market could still result in a (most likely milder)
                profit. 
        """
        try:
            self.crypto_storage.client.create_order(symbol=_symbol,
                                                            side=enum.SIDE_SELL,
                                                            type=enum.ORDER_TYPE_MARKET,
                                                            quantity=_quantity)
        except binexc.BinanceAPIException as e:
            print(e.status_code)
            print(e.message)
            self.order_sell_market(_symbol, _quantity)
                    
        
    def test_order_buy_alt(self, _symbol, _quantity, _price):
        """ FOR TESTING BINBOT BEFORE YOU LOSE MONEY
            Important to test if your orders will execute in time.
            Buys an altcoin using Binance package
            
            Keyword Arguments:
            _symbol -- String: Symbol name of trading pair eg NEOBTC 
            _quantity -- Integer: Quantity to buy
            _price -- String: Price to buy at
            order_rank -- Integer: The order of buy/sell exection
            attempt -- Integer: Total of attempts to buy at the price
        """
        try:
            self.client.create_test_order(symbol=_symbol,
                                        side = enum.SIDE_BUY,
                                        type = enum.ORDER_TYPE_LIMIT,
                                        timeInForce = enum.TIME_IN_FORCE_GTC,
                                        quantity = _quantity,
                                        price = _price,
                                        disable_validation=True)
        except binexc.BinanceAPIException as e:
            print(e.status_code)
            print(e.message)

    def test_order_sell_alt(self, _symbol, _quantity, _price):
        """ FOR TESTING BINBOT BEFORE YOU LOSE MONEY
            Important to test if your orders will execute in time.
            Sells an altcoin using Binance package
            
            Keyword Arguments:
            _symbol -- String: Symbol name of trading pair eg NEOBTC 
            _quantity -- Integer: Quantity to buy
            _price -- String: Price to buy at
            order_rank -- Integer: The order of buy/sell exection
            attempt -- Integer: Total of attempts to buy at the price
        """
        try:
            self.client.create_test_order(symbol=_symbol,
                                        side = enum.SIDE_SELL,
                                        type = enum.ORDER_TYPE_LIMIT,
                                        timeInForce = enum.TIME_IN_FORCE_GTC,
                                        quantity = _quantity,
                                        price = _price,
                                        disable_validation=True)                                         
        except binexc.BinanceAPIException as e:
            print(e.status_code)
            print(e.message)
        
    def hunt(self, trials=10000, sleep_time=0.1):
        """ This is the main function of BinBot.
            This function will search for arbitrage opportunities and execute orders
            if it finds an inefficient pair.
            
            Keyword Arguments:
            trials -- Integer: how many loops the bot will run (default 10,000)
            sleep_time -- Float: The Binance API (since I last checked) will only allow
                                you to access it 18 times per second. So need a sleep time
                                to avoid this problem. Remember the longer the sleep time
                                the less likely your arbitrage oppurtunity will still be
                                available. (default 0.1)
        """
        num_runs = 0
        pre_arbitrage_assets = self.load_arbitrage_assets()
        time.sleep(sleep_time)
        while(num_runs < trials):
            try:
                self.update_orderbook()
            except ConnectionError as e:
                print(e + "will suspend bot for 10 seconds")
                time.sleep(10)
                continue
            #Search for inefficiency
            orderbook_btc = self.orderbook_btc_eth(self.orderbook)
            orderbook_eth = self.orderbook_eth_btc(self.orderbook)
            if(orderbook_btc[0][1] - (self.fee * orderbook_btc[0][1]) > self.bit_rate['btc_one'] and
               orderbook_eth[0][1] - (self.fee * orderbook_eth[0][1]) > float(self.bit_rate['askPrice'])): 
                #print('found' + orderbook_btc[0][0] + orderbook_eth[0][0] + str(num_runs))
                num_runs += 1
                purchase = []
                for k in self.orderbook:
                    if(list(k.keys())[0] == orderbook_btc[0][0]):
                        purchase.insert(0, k)
                    if(list(k.keys())[0] == orderbook_eth[0][0]):
                        purchase.insert(1, k)
                btc_limit = binance_config.btc_trade_limit
                while(btc_limit > 0.001):
                    if(self.determine_feasibility(orderbook_btc[0][0], orderbook_eth[0][0], purchase, btc_limit) is True):
                        self.execute_trade(orderbook_btc[0][0], orderbook_eth[0][0], purchase, btc_limit)
                        break
                    else:
                        btc_limit = btc_limit - 0.001
            num_runs += 1
            if(num_runs % 100 == 0):
                print(str(num_runs))
        post_arbitrage_assets = self.load_arbitrage_assets()
        
        #Print results
        time_delta = datetime.datetime.now().replace(microsecond=0) - pre_arbitrage_assets['datetime'] 
        print('Initial: BTC:', pre_arbitrage_assets['BTC'],'ETH:', pre_arbitrage_assets['ETH'], 'BNB:', pre_arbitrage_assets['BNB'])
        print('After__: BTC:', post_arbitrage_assets['BTC'],'ETH:', post_arbitrage_assets['ETH'], 'BNB:', post_arbitrage_assets['BNB'])
        print('Diff___: BTC:', float(post_arbitrage_assets['BTC'])-float(pre_arbitrage_assets['BTC']),
              'ETH:', float(post_arbitrage_assets['ETH'])-float(pre_arbitrage_assets['ETH']),
              'BNB:', float(post_arbitrage_assets['BNB'])-float(pre_arbitrage_assets['BNB']),
              'TIME:', divmod(time_delta.total_seconds(), 60))
            
    
    def determine_feasibility(self, btc_sym, eth_sym, purchase, btc_trade_limit):
        """ Determines if an arbitrage opportunity is profitable. """
        if(btc_trade_limit / float(purchase[0][btc_sym][0]['askPrice']) <= float(purchase[0][btc_sym][0]['askQty']) and
           btc_trade_limit / float(purchase[0][btc_sym][0]['askPrice']) <= float(purchase[0][btc_sym][1]['bidQty'])):
            eth_capital = (btc_trade_limit / float(purchase[0][btc_sym][0]['askPrice'])) * float(purchase[0][btc_sym][1]['bidPrice'])
            if(eth_capital / float(purchase[1][eth_sym][1]['askPrice']) <= float(purchase[1][eth_sym][1]['askQty']) and
               eth_capital / float(purchase[1][eth_sym][1]['askPrice']) <= float(purchase[1][eth_sym][0]['bidQty'])):
               #and eth_capital / float(purchase[1][eth_sym][1]['askPrice']) >= 1):
                return True
            else:
                return False
        else:
            return False
               
    def execute_trade(self, btc_sym, eth_sym, purchase, btc_trade_limit):
        """ Executes trade in  BTC-->ALT_1-->ETH-->ALT_2-->BTC order.
                Side note: Making threads will improve likelihood of success. 
                            This implementation is inefficient. 
        """
        amount_btc = math.floor(btc_trade_limit/float(purchase[0][btc_sym][0]['askPrice']))
        eth_capital = (btc_trade_limit / float(purchase[0][btc_sym][0]['askPrice'])) * float(purchase[0][btc_sym][1]['bidPrice'])
        amount_eth = math.floor(eth_capital / float(purchase[1][eth_sym][1]['askPrice']))
        if(amount_btc*float(purchase[0][btc_sym][0]['askPrice']) > 0.001 and amount_eth * float(purchase[1][eth_sym][0]['bidPrice'])>0.001):
            if self.order_buy_alt(purchase[0][btc_sym][0]['symbol'], amount_btc, purchase[0][btc_sym][0]['askPrice'], 1) is True:
                print("1: " + purchase[0][btc_sym][0]['symbol'] + " " + str(amount_btc) + " " + purchase[0][btc_sym][0]['askPrice'])
                
                self.order_sell_alt(purchase[0][btc_sym][1]['symbol'], amount_btc, purchase[0][btc_sym][1]['bidPrice'], 2)
                print("2: " + purchase[0][btc_sym][1]['symbol'] + " " + str(amount_btc) + " " + purchase[0][btc_sym][1]['bidPrice'])
                
                if self.order_buy_alt(purchase[1][eth_sym][1]['symbol'], amount_eth, purchase[1][eth_sym][1]['askPrice'], 3) is True:
                    print("3: " + purchase[1][eth_sym][1]['symbol'] + " " + str(amount_eth) + " " + purchase[1][eth_sym][1]['askPrice'])
                    
                    self.order_sell_alt(purchase[1][eth_sym][0]['symbol'], amount_eth, purchase[1][eth_sym][0]['bidPrice'], 4)
                    print("4: " + purchase[1][eth_sym][0]['symbol'] + " " + str(amount_eth) + " " + purchase[1][eth_sym][0]['bidPrice'])

        self.remove_any_open_orders([purchase[0][btc_sym][0]['symbol'],purchase[0][btc_sym][1]['symbol'],purchase[1][eth_sym][1]['symbol'],
                                     purchase[1][eth_sym][0]['symbol']])
    
    def remove_any_open_orders(self, poss_orders = []):
        """ For upgrading flexibility of BinBot. Removes any open orders. """
        for order in poss_orders:
            open_orders = self.get_open_orders_symbol(_symbol = order)
            if len(open_orders) is not 0:
                self.order_sell_market(_symbol= open_orders[0]['symbol'], _quantity=open_orders[0]['origQty'])
       
    def check_server_time_difference(self):
        """ Checks the amount of time it takes for your packets to reach Binance 
            servers and return to your computer.
            VERY IMPORTANT: If your packets take too long, your trades will not execute
        """
        for i in range(0, 10):
            local_time_one = int(time.time()*1000)
            server_time = self.client.get_server_time()
            diff_one = server_time['serverTime'] - local_time_one
            local_time_two = int(time.time()*1000)
            diff_two = local_time_two - server_time['serverTime']
            print("local1: %s server: %s local2: %s diff1: %s diff2: %s" % (local_time_one, server_time['serverTime'], local_time_two, diff_one, diff_two))
            time.sleep(2)
        
    def get_specific_symbol(self, coin_sym='ETH', trade_currency='BTC'):
        """Returns a specific trading pair to see what price it is at in the orderbook.
            If no parameters are given, it will return the price of ETHBTC.
        
            Keyword Arguments:
            coin_sym -- This is the first symbol in the trading pair (default 'ETH')
            trade_currency -- This is the second symbol in the trading pair (default 'BTC')
        """            
        if trade_currency != 'BTC' and trade_currency != 'ETH' and trade_currency != 'BNB':
            print('Trade currency can only be BTC or ETH')
            return {}
        trade_pair = coin_sym + trade_currency
        for k in self.orderbook:
            if list(k.keys())[0] == coin_sym[0:3]:
                for pair in k[list(k.keys())[0]]:
                    if pair['symbol'] == trade_pair:
                        return pair
        print('Pair not in orderbook.')
        return {}
                
    def get_orderbook_symbol(self, _symbol='ETHBTC', _limit=10):
        """ Returns the orderbook (buy/sell prices) of a given symbol.
            Limit will hold the orderbook to only 10 prices of the buy/sell pair
            
            Returns:
            Dictionary of prices
        """
        return self.client.get_order_book(symbol=_symbol, limit=_limit)
    
    def get_open_order_symbol(self, _symbol='ETHBTC'):
        """Get all open orders of a symbol """
        try:
            return self.client.get_open_orders(symbol=_symbol)
        except binexc.BinanceAPIException as e:
            print(e.message)
            self.get_open_orders_symbol(_symbol)
    
    def get_past_orders(self, _symbol='ETHBTC'):
        """ Get the user's past orders. 
        """
        return self.client.get_all_orders(symbol=_symbol)   
    
    def load_arbitrage_assets(self):
        """ Loads the amount of coins in the user's account """
        flag = False
        btc_eth_bnb = {}
        while(flag is False):
            try:
                acc = self.client.get_account(recvWindow=binance_config.recv_window)
                flag = True
            except binexc.BinanceAPIException as e:
                print(str(e.status_code) + " : " + e.message)
                time.sleep(1)
        #acc['balances']
        for cryptoasset in acc['balances']:
            if cryptoasset['asset'] == 'BTC':
                btc_eth_bnb['BTC'] = cryptoasset['free']
            if cryptoasset['asset'] == 'ETH': 
                btc_eth_bnb['ETH'] = cryptoasset['free']
            if cryptoasset['asset'] == 'BNB':
                btc_eth_bnb['BNB'] = cryptoasset['free']
            if len(btc_eth_bnb) is 3:
                break
        btc_eth_bnb['datetime'] = datetime.datetime.now().replace(microsecond=0)
        return btc_eth_bnb

        