#!/usr/bin/python
# -*- coding: utf-8 -*-

# /examples/record_trades.py
# Stanislav Lazarov

# Sample script showing how subscribe_to_exchange_deltas() works.

# Overview:
# ---------
# 1) Creates custom trade_history dict.
# 2) When an order is executed, the fill is recorded in trade_history.
# 3) When each ticker has received an order, the script disconnects.

from __future__ import print_function
from time import sleep
from bittrex_websocket import BittrexSocket, BittrexMethods


def main():
    class MySocket(BittrexSocket):

        def on_public(self, msg):
            # Create entry for the ticker in the trade_history dict
            if msg['invoke_type'] == BittrexMethods.SUBSCRIBE_TO_EXCHANGE_DELTAS:
                if msg['M'] not in trade_history:
                    trade_history[msg['M']] = []
                # Add history nounce
                trade_history[msg['M']].append(msg)
                # Ping
                print('[Trades]: {}'.format(msg['M']))

    # Create container
    trade_history = {}
    # Create the socket instance
    ws = MySocket()
    # Enable logging
    ws.enable_log()
    # Define tickers
    tickers = ['BTC-ETH', 'BTC-NEO', 'BTC-ZEC', 'ETH-NEO', 'ETH-ZEC']
    # Subscribe to trade fills
    ws.subscribe_to_exchange_deltas(tickers)

    while len(set(tickers) - set(trade_history)) > 0:
        sleep(1)
    else:
        for ticker in trade_history.keys():
            print('Printing {} trade history.'.format(ticker))
            for trade in trade_history[ticker]:
                print(trade)
        ws.disconnect()
        # sleep(10000)


if __name__ == "__main__":
    main()
