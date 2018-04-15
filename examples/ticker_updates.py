#!/usr/bin/python
# -*- coding: utf-8 -*-

# /examples/ticker_updates.py
# Stanislav Lazarov

# Sample script to show how subscribe_to_exchange_deltas() works.
# Overview:
#   Creates a custom ticker_updates_container dict through on_open method.
#   Subscribes to N tickers to get their general information.
#   When information is received, checks if the ticker is in ticker_updates_container and adds it if not.
#   Disconnects when it has the information for each ticker.

from bittrex_websocket.websocket_client import BittrexSocket
from time import sleep


def main():
    class MySocket(BittrexSocket):
        def __init__(self):
            super(MySocket, self).__init__()
            self.ticker_updates_container = {}

        def on_public(self, msg):
            name = msg['M']
            if name not in self.ticker_updates_container:
                self.ticker_updates_container[name] = msg
                print('Just received market update for {}.'.format(name))

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

    # Users can also subscribe without introducing delays in invoking but
    # it is recommended when you are subscribing to a large list of tickers.
    # ws.subscribe_to_exchange_deltas(tickers)

    while len(ws.ticker_updates_container) < len(tickers):
        sleep(1)
    else:
        print('We have received updates for all tickers. Closing...')
        ws.disconnect()
        sleep(10)


if __name__ == "__main__":
    main()
