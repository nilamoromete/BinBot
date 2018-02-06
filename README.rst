WARNING: This program used to be quite successful in finding arb opps. However, it has not been updated in a couple months and the huge influx of new traders from when the bot was originally used probably makes it all but useless now ie use at your own risk. Be sure to read the issues section.

BinBot
~~~~~~~~~
``BinBot`` is a bot that will search for arbitrage opportunities on Binance. The method is simple. It also provides lots of data in an easily manageable dictionary. 

1) Use bitcoin to purchase altcoin.
2) Sell altcoin for ethereum.
3) Use ethereum to purchase a different altcoin from the original.
4) Sell the second altcoin for bitcoin.

.. image:: https://user-images.githubusercontent.com/16274160/35866214-2e06327e-0b1c-11e8-837e-d9fd3a8287b2.jpg

It provides additional functionality such selling at market and managing your account.

Installation
^^^^^^^^^^^^^
Requires python-binance package.

.. code-block:: console
    
     $ pip install python-binance
 
Usage
^^^^^^^
Update config files to avoid trading coins on your no-trade list. 

.. code-block:: pycon

     >>> bb = BinBot()
     >>> #Check ping
     >>> bb.check_server_time_difference()
     >>> #Search for and execute trades
     >>> bb.hunt(10000, 0.01)  #One trial every .01 seconds dependent on ping to server

There are additional methods you might want to add to your script such as:

 - get_past_orders() 
 - get_open_order_symbol()
 - order_sell_market()

Issues
^^^^^^^^
Not updated since 7/2017
---------------------------
Trading pairs that were added or delisted from Binance after this date have not been updated. 

Amount of BNB in account
---------------------------
Having BNB in your account will lower your trading fees. If you wish to use BinBot without BNB, change fee in __init__ to 0.001.
BinBot does take into account the fees when deciding whether a trade is feasible. 

Distance to Binance servers
--------------------------------
Last time I checked, the servers are located in Taiwan/HK (maybe Singapore as well). If you are located far away from these locations, every additional millisecond your packets take to arrive at the server is time for someone else to execute the order before your data arrives. 

Improvements
----------------
BinBot can BUY an altcoin but be unable to SELL because the order it wanted to place has been exercised by someone else. The altcoin will stay in your account. This will happen and you will have to use get_open_order_symbol() and order_sell_market() in your script or manually sell them.

The filtering functions probably can be optimized. You will have to deal with the list of dictionaries that the python-binance package returns.

Threads: Implement threads to send multiple orders at the same time rather than sequentially. (This will require the account to have a reserve of both BTC and ETH.)

.. image:: https://user-images.githubusercontent.com/16274160/35866222-3167c78e-0b1c-11e8-8f0b-9c1ab074dfb5.jpg


