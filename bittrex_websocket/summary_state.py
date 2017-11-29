#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/summary_state.py
# Stanislav Lazarov

from time import sleep

from bittrex_websocket.websocket_client import BittrexSocket

if __name__ == "__main__":
    class MyBittrexSocket(BittrexSocket):
        def on_open(self):
            self.client_callbacks = ['updateSummaryState']

        def on_debug(self, **kwargs):
            pass

        def on_message(self, *args, **kwargs):
            print(args)


    tickers = ['BTC-ETH', 'ETH-1ST', 'BTC-1ST', 'BTC-NEO', 'ETH-NEO']
    ws = MyBittrexSocket(tickers)
    ws.run_old()
    for i in range(10):
        sleep(1)
    ws.stop()