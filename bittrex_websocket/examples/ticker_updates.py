#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/examples/ticker_updates.py
# Stanislav Lazarov

# Sample script to show how subscribe_to_ticker_update() works.
# Overview:
#   Creates a custom ticker_updates_container dict through on_open method.
#   Subscribes to N tickers to get their general information.
#   When information is received, checks if the ticker is in ticker_updates_container and adds it if not.
#   Disconnects when it has the information for each ticker.

from __future__ import print_function

from time import sleep

from bittrex_websocket.websocket_client import BittrexSocket


def main():
    class MySocket(BittrexSocket):
        def on_open(self):
            self.ticker_updates_container = {}

        def on_ticker_update(self, msg):
            name = msg['MarketName']
            if name not in self.ticker_updates_container:
                self.ticker_updates_container[name] = msg
                print('Just received ticker update for {}.'.format(name))

    # Create the socket instance
    ws = MySocket()
    # Enable logging
    ws.enable_log()
    # Define tickers
    tickers = ['BTC-ETH', 'BTC-NEO', 'BTC-ZEC', 'ETH-NEO', 'ETH-ZEC']
    # Subscribe to ticker information
    ws.subscribe_to_ticker_update(tickers)

    while len(ws.ticker_updates_container) < len(tickers):
        sleep(1)
    else:
        print('We have received updates for all tickers. Closing...')
        ws.disconnect()


if __name__ == "__main__":
    main()
