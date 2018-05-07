|logo| bittrex-websocket
=====================

|pypi-v2| |pypi-pyversions2| |pypi-l2| |pypi-wheel2|

.. |pypi-v2| image:: https://img.shields.io/pypi/v/bittrex-websocket.svg
    :target: https://pypi.python.org/pypi/bittrex-websocket

.. |pypi-pyversions2| image:: https://img.shields.io/pypi/pyversions/bittrex-websocket.svg
    :target: https://pypi.python.org/pypi/bittrex-websocket

.. |pypi-l2| image:: https://img.shields.io/pypi/l/bittrex-websocket.svg
    :target: https://pypi.python.org/pypi/bittrex-websocket

.. |pypi-wheel2| image:: https://img.shields.io/pypi/wheel/bittrex-websocket.svg
    :target: https://pypi.python.org/pypi/bittrex-websocket

.. |logo| image:: /resources/py_btrx.svg
   :width: 60px

What is ``bittrex-websocket``?
--------------------------
Python Bittrex WebSocket (PBW) is the first unofficial Python wrapper for
the `Bittrex Websocket API <https://github.com/Bittrex/bittrex.github.io>`_.
It provides users with a simple and easy to use interface to the `Bittrex Exchange <https://bittrex.com>`_.

Users can use it to access real-time public data (e.g exchange status, summary ticks and order fills) and account-level data such as order and balance status. The goal of the package is to serve as a foundation block which users can use to build upon their applications. Examples usages can include maintaining live order books, recording trade history, analysing order flow and many more.

If you prefer ``asyncio``, then take a look at my other library: `bittrex-websocket-aio <https://github.com/slazarov/python-bittrex-websocket-aio>`_.

--------------

Documentation
    http://python-bittrex-websocket-docs.readthedocs.io/en/latest/
    
Getting started/How-to
    http://python-bittrex-websocket-docs.readthedocs.io/en/latest/howto.html
    
Methods
    http://python-bittrex-websocket-docs.readthedocs.io/en/latest/methods.html
    
Changelog
    http://python-bittrex-websocket-docs.readthedocs.io/en/latest/changelog.html#bittrex-websocket
    
I am constantly working on new features. Make sure you stay up to date by regularly checking the official docs!

**Having an issue or a question? Found a bug or perhaps you want to contribute? Open an issue!**

Quick Start
-----------
.. code:: bash

    pip install bittrex-websocket
   
.. code:: python

    #!/usr/bin/python
    # /examples/ticker_updates.py
    
    # Sample script showing how subscribe_to_exchange_deltas() works.

    # Overview:
    # ---------
    # 1) Creates a custom ticker_updates_container dict.
    # 2) Subscribes to N tickers and starts receiving market data.
    # 3) When information is received, checks if the ticker is
    #    in ticker_updates_container and adds it if not.
    # 4) Disconnects when it has data information for each ticker.

    from bittrex_websocket.websocket_client import BittrexSocket
    from time import sleep

    def main():
        class MySocket(BittrexSocket):

            def on_public(self, msg):
                name = msg['M']
                if name not in ticker_updates_container:
                    ticker_updates_container[name] = msg
                    print('Just received market update for {}.'.format(name))

        # Create container
        ticker_updates_container = {}
        # Create the socket instance
        ws = MySocket()
        # Enable logging
        ws.enable_log()
        # Define tickers
        tickers = ['BTC-ETH', 'BTC-NEO', 'BTC-ZEC', 'ETH-NEO', 'ETH-ZEC']
        # Subscribe to ticker information
        for ticker in tickers:
            sleep(0.01)
            ws.subscribe_to_exchange_deltas([ticker])

        # Users can also subscribe without introducing delays during invoking but
        # it is the recommended way when you are subscribing to a large list of tickers.
        # ws.subscribe_to_exchange_deltas(tickers)

        while len(ticker_updates_container) < len(tickers):
            sleep(1)
        else:
            print('We have received updates for all tickers. Closing...')
            ws.disconnect()
            sleep(10)

    if __name__ == "__main__":
        main()

Disclaimer
----------
I am not associated with Bittrex. Use the library at your own risk, I don't bear any responsibility if you end up losing your money.
