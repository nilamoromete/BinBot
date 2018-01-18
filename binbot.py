# -*- coding: utf-8 -*-
"""
Created on Tue Oct 17 19:21:53 2017

@author: Mikey
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
        return self.client.get_orderbook_tickers()
    
    def update_orderbook(self):
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
        flag = False
        #Local time compared to Binance NTP server time is offset +1000ms which throws error
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
        acc = self.client.get_account(recvWindow = binance_config.recv_window)
        for k in acc['balances']:
            if(k['asset'] == symbol[0, symbol_length]):
                return k['free']
        return "Symbol Not Found"
        
    def get_keys(self, orderbook):
        _keys = []
        for k in orderbook:
            _keys.append(list(k.keys())[0])
        return _keys
    
    def extract_btc_eth_rate(self, orderbook):
        for i in range(0, len(orderbook)):
            if(orderbook[i]['symbol'][0:6] == 'ETHBTC'):
                odbk = orderbook[i]
                odbk['btc_one'] = 1 / float(odbk['askPrice'])
                return orderbook[i]
        
    def modify_orderbook(self, orderbook):
        ob_sorted = sorted(orderbook, key=lambda k:k['symbol'])
        ob_sorted = self.del_non_pair_coins(ob_sorted)
        ob_dict = self.transform_data_list(ob_sorted)
        return ob_dict

    #REMOVED LINK/BNB/NEO (ON NO TRADE LIST) 
    #REMOVED LRC (DELISTED FROM BINANCE)
    #REMOVED ZEC (SEEMS DELISTED)
    #Removes coins that are not listed for both BTC and ETH
    def del_non_pair_coins(self, orders):
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
     
    #transforms data into the form
    # List --> dictionary -- > list(btc=0, eth=1)
    def transform_data_list(self, orders):
        transform = []
        for i in range(0, len(orders), 2):
            transform.append({orders[i]['symbol'][0:3]: [orders[i], orders[i+1]]})
        return transform    
        
    def orderbook_btc_eth(self, orderbook):
        #orderbook = self.modify_orderbook(orderbook)
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
        #orderbook = self.modify_orderbook(orderbook)
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
        """Sells coins into either ETH or BTC
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
        
    #formerly searh_arbitrage_opps()
    def hunt(self, trials, sleep_time):
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
        #else:
            #print("Notional Min not reached", "btc-->eth",str(amount_btc*float(purchase[0][btc_sym][0]['askPrice'])), 
             #     "eth-->btc", str(amount_eth * float(purchase[1][eth_sym][0]['bidPrice'])))
        self.remove_any_open_orders([purchase[0][btc_sym][0]['symbol'],purchase[0][btc_sym][1]['symbol'],purchase[1][eth_sym][1]['symbol'],
                                     purchase[1][eth_sym][0]['symbol']])
    
    def remove_any_open_orders(self, poss_orders = []):
        for order in poss_orders:
            open_orders = self.get_open_orders_symbol(_symbol = order)
            if len(open_orders) is not 0:
                self.order_sell_market(_symbol= open_orders[0]['symbol'], _quantity=open_orders[0]['origQty'])
       
    def check_server_time_difference(self):
        for i in range(0, 10):
            local_time_one = int(time.time()*1000)
            server_time = self.client.get_server_time()
            diff_one = server_time['serverTime'] - local_time_one
            local_time_two = int(time.time()*1000)
            diff_two = local_time_two - server_time['serverTime']
            print("local1: %s server: %s local2: %s diff1: %s diff2: %s" % (local_time_one, server_time['serverTime'], local_time_two, diff_one, diff_two))
            time.sleep(2)
        
    def get_specific_symbol(self, coin_sym='ETH', trade_currency='BTC'):
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
        return self.client.get_order_book(symbol=_symbol, limit=_limit)
    
    def get_open_orders_symbol(self, _symbol):
        try:
            return self.client.get_open_orders(symbol=_symbol)
        except binexc.BinanceAPIException as e:
            print(e.message)
            self.get_open_orders_symbol(_symbol)
    
    def get_current_past_orders(self, _symbol='ETHBTC'):
        return self.client.get_all_orders(symbol=_symbol)   
    
    def load_arbitrage_assets(self):
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

    def fix_symbols(self, symbol):
        if(symbol == "STR"):
            return "STRAT"
        elif(symbol == "SNG"):
            return "SNGLS"
        elif(symbol == 'IOT'):
            return 'IOTA'
        elif(symbol == 'SAL'):
            return 'SALT'
        elif(symbol == 'QTU'):
            return 'QTUM'
        else:
            return symbol           