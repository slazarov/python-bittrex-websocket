#!/usr/bin/python
# -*- coding: utf-8 -*-

# /examples/order_book.py
# Stanislav Lazarov


from __future__ import print_function
from time import sleep
from bittrex_websocket import OrderBook


def main():
    class MySocket(OrderBook):
        def on_ping(self, msg):
            print('Received order book update for {}'.format(msg))

    # Create the socket instance
    ws = MySocket()
    # Enable logging
    ws.enable_log()
    # Define tickers
    tickers = ['BTC-ETH']
    # Subscribe to order book updates
    ws.subscribe_to_orderbook(tickers)

    while True:
        sleep(10)
        book = ws.get_order_book('BTC-ETH')
        print(book[u'S'][0])
    else:
        pass


if __name__ == "__main__":
    main()
