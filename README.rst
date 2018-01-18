WARNING: This program used to be quite successful in finding arb opps. However, it has not been updated in a couple months and the huge influx of new traders from when the bot was originally used probably makes it all but useless now ie use at your own risk.


BinBot
~~~~~~~~~~~~~~~~~~~~~~~~~
``BinBot`` is a bot that will search for arbitrage opportunities on Binance. The method is simple. It also provides lots of data in an easily manageable dictionary. 
1) Use bitcoin to purchase altcoin.
2) Sell altcoin for ethereum.
3) Use ethereum to purchase a different altcoin from the original.
4) Sell second altcoin for bitcoin.

Update config files to make sure not to trade any coins you don't want to.

.. code-block: : pycon
	>>> bb = BinBot()
	>>> bb.hunt(10000, 0.01)  #1 trial every .01 second dependent on ping to server
	
	>>> #Check ping
	>>> bb.check_server_time_difference()


Requirements:
--------------------
Requires python-binance package. 
.. code-block: : console
	$ pip install python-binance