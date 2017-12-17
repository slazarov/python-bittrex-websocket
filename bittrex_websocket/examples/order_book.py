#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/examples/order_book.py
# Stanislav Lazarov

# Sample script to show how the following methods work:
#    • subscribe_to_orderbook()
#    • get_order_book_sync_state()
#    • get_order_book()
# Overview:
#   Subscribes to the order book for N tickers.
#   When all the order books are synced, prints the Bid quotes for each ticker at depth level 0 and disconnects

from __future__ import print_function

from time import sleep

from bittrex_websocket.websocket_client import BittrexSocket


def main():
    class MySocket(BittrexSocket):
        def on_orderbook(self, msg):
            print('[OrderBook]: {}'.format(msg['MarketName']))

    # Create the socket instance
    ws = MySocket()
    # Enable logging
    ws.enable_log()
    # Define tickers
    tickers = ['BTC-ETH', 'BTC-NEO', 'BTC-ZEC', 'ETH-NEO', 'ETH-ZEC']
    # Subscribe to live order book
    ws.subscribe_to_orderbook(tickers)

    while True:
        i = 0
        sync_states = ws.get_order_book_sync_state()
        for state in sync_states.values():
            if state == 3:
                i += 1
        if i == len(tickers):
            print('We are fully synced. Hooray!')
            for ticker in tickers:
                ob = ws.get_order_book(ticker)
                name = ob['MarketName']
                quantity = str(ob['Buys'][0]['Quantity'])
                price = str(ob['Buys'][0]['Rate'])
                print('Ticker: ' + name + ', Bids depth 0: ' + quantity + '@' + price)
            ws.disconnect()
            break
        else:
            sleep(1)


if __name__ == "__main__":
    main()
