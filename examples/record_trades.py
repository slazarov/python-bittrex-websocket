#!/usr/bin/python
# -*- coding: utf-8 -*-

# /examples/record_trades.py
# Stanislav Lazarov

# Sample script to show how subscribe_to_exchange_deltas() works.
# Overview:
#   Creates custom trade_history dict.
#   When an order is executed, the fill is recorded in trade_history.
#   When each ticker has received an order, the script disconnects.

from __future__ import print_function

from time import sleep

from bittrex_websocket.websocket_client import BittrexSocket


def main():
    class MySocket(BittrexSocket):
        def __init__(self, url=None):
            super(MySocket, self).__init__(url)
            self.trade_history = {}

        def on_public(self, msg):
            # Create entry for the ticker in the trade_history dict
            if msg['M'] not in self.trade_history:
                self.trade_history[msg['M']] = []
            # Add history nounce
            self.trade_history[msg['M']].append(msg)
            # Ping
            print('[Trades]: {}'.format(msg['M']))

    # Create the socket instance
    ws = MySocket()
    # Enable logging
    ws.enable_log()
    # Define tickers
    tickers = ['BTC-ETH', 'BTC-NEO', 'BTC-ZEC', 'ETH-NEO', 'ETH-ZEC']
    # Subscribe to trade fills
    ws.subscribe_to_exchange_deltas(tickers)

    while len(set(tickers) - set(ws.trade_history)) > 0:
        sleep(1)
    else:
        for ticker in ws.trade_history.keys():
            print('Printing {} trade history.'.format(ticker))
            for trade in ws.trade_history[ticker]:
                print(trade)
        ws.disconnect()
        sleep(10)


if __name__ == "__main__":
    main()
