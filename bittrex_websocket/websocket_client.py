#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/websocket_client.py
# Stanislav Lazarov

from threading import Thread
from time import sleep

import cfscrape
from requests import Session
from signalr import Connection


class BittrexSocket(object):
    def __init__(self, tickers=None, conn_type='normal'):
        """
        :param tickers: a list of tickers, single tickers should also be supplied as a list
        :type tickers: []
        :param conn_type: 'normal' direct connection or 'cloudflare' workaround
        :type conn_type: str
        """
        if tickers is None:
            self.tickers = ['BTC-ETH']
        else:
            self.tickers = tickers
        self.timeout = 120000
        self.conn_list = []
        self.threads = []
        self.conn_type = conn_type
        self.url = 'http://socket-stage.bittrex.com/signalr'  # ''http://socket.bittrex.com/signalr'
        self.client_callbacks = ['updateExchangeState']  # ['updateSummaryState']
        self.server_callbacks = ['SubscribeToExchangeDeltas']

    def run(self):
        self.on_open()
        thread = Thread(target=self._go)
        thread.daemon = True
        self.threads.append(thread)
        self.threads[0].start()

    def _go(self):
        # Create socket connections
        self._start()

    def stop(self):
        # To-do: come up with better handling of websocket stop
        for conn in self.conn_list:
            conn['corehub'].client.off('updateExchangeState', self.on_message)
            conn['connection'].close()
        self.on_close()

    def _start(self):
        def get_chunks(l, n):
            # Yield successive n-sized chunks from l.
            for i in range(0, len(l), n):
                yield l[i:i + n]

        # Initiate a generator that splits the ticker list into chunks
        ticker_gen = get_chunks(self.tickers, 20)
        while True:
            try:
                chunk_list = next(ticker_gen)
            except StopIteration:
                break
            if chunk_list is not None:
                # Create connection object
                conn_obj = self._create_connection()

                # Create thread
                thread = Thread(target=self._subscribe, args=(conn_obj, chunk_list))
                self.threads.append(thread)
                conn_obj['thread-name'] = thread.getName()
                self.conn_list.append(conn_obj)
                thread.start()
        return

    def _create_connection(self):
        # Sometimes Bittrex blocks the normal connection, so
        # we have to use a Cloudflare workaround
        if self.conn_type == 'normal':
            with Session() as connection:
                conn = Connection(self.url, connection)
        elif self.conn_type == 'cloudflare':
            with cfscrape.create_scraper() as connection:
                conn = Connection(self.url, connection)
        else:
            raise Exception('Connection type is invalid, set conn_type to \'normal\' or \'cloudflare\'')
        conn.received += self.on_debug
        conn.error += self.on_error
        corehub = conn.register_hub('coreHub')
        conn_object = {'connection': conn, 'corehub': corehub}
        return conn_object

    def _subscribe(self, conn_object, tickers):
        conn, corehub = conn_object['connection'], conn_object['corehub']
        print('Establishing ticker update connection...')
        try:
            conn.start()
            print('Ticker update connection established.')
            # Subscribe
            for cb in self.client_callbacks:
                corehub.client.on(cb, self.on_message)
            for k, cb in enumerate(self.server_callbacks):
                for i, ticker in enumerate(tickers):
                    corehub.server.invoke(cb, ticker)
                    if i == len(tickers) - 1:
                        sleep(5)
            # Close the connection if no message is received after timeout value.
            conn.wait(self.timeout)
        except Exception as e:
            print(e)
            print('Failed to establish connection')
            return

    def on_open(self):
        # Called before initiating the websocket connection
        # Use it when you want to add optional parameters
        pass

    def on_close(self):
        # Called after closing the websocket connection
        # Use it when you want to add any closing logic.
        print('Bittrex websocket closed.')

    def on_error(self, error):
        # Error handler
        print(error)
        self.stop()

    def on_debug(self, **kwargs):
        # Debug information, shows all data
        print(kwargs)

    def on_message(self, *args, **kwargs):
        """
        This is where you get the order flow stream.
        Subscribed via 'updateExchangeState'

        Access it from args[0]

        Example output:
        args = \
            (
                {
                    'MarketName': 'BTC-ETH', 'Nounce': 101846,
                    'Buys':
                        [
                            {'Type': 1, 'Rate': 0.05369548, 'Quantity': 0.0}
                        ],
                    'Sells':
                        [
                            {'Type': 2, 'Rate': 0.05373854, 'Quantity': 62.48260112}
                        ],
                    'Fills':
                        [
                            {'OrderType': 'BUY', 'Rate': 0.05373854, 'Quantity': 0.88839888,
                             'TimeStamp': '2017-11-24T13:18:43.44'}
                        ]
                }
            )
        """
        print(args[0])


if __name__ == "__main__":
    class MyBittrexSocket(BittrexSocket):
        def on_open(self):
            self.client_callbacks = ['updateExchangeState']
            self.nounces = []
            self.msg_count = 0

        def on_debug(self, **kwargs):
            pass

        def on_message(self, *args, **kwargs):
            self.nounces.append(args[0])
            self.msg_count += 1


    tickers = ['BTC-ETH', 'ETH-1ST', 'BTC-1ST', 'BTC-NEO', 'ETH-NEO']
    ws = MyBittrexSocket(tickers)
    ws.run()
    while ws.msg_count < 20:
        sleep(1)
        continue
    else:
        for msg in ws.nounces:
            print(msg)
    ws.stop()
