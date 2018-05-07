#!/usr/bin/python
# -*- coding: utf-8 -*-

# /examples/ticker_updates.py
# Stanislav Lazarov

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
