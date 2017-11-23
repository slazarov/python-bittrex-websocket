#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/websocket_client.py
# Stanislav Lazarov
# Install requests with: pip install requests[security] if you have any errors with SSL

import sys
from threading import Thread
from time import sleep, time
from requests import Session
from signalr import Connection
import cfscrape


class BittrexSocket(object):
    def __init__(self, tickers: [] = None, conn_type: str = 'normal'):
        if tickers is None:
            self.tickers = ['BTC-ETH']
        else:
            self.tickers = tickers
        self.timeout = 120000
        self.conn_list = []
        self.threads = []
        self.conn_type = conn_type

    def run(self):
        thread = Thread(target=self._go)
        thread.daemon = True
        self.threads.append(thread)
        self.threads[0].start()

    def stop(self):
        try:
            for conn in self.conn_list:
                conn['connection'].close()
        except Exception:
            # To-do: come up with better handling of websocket stop
            pass
        self.threads[0].join()

    def _go(self):
        # Create socket connections
        self._start()

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
        url = 'http://socket.bittrex.com/signalr'
        # Sometimes Bittrex blocks the normal connection, so
        # we have to use a Cloudflare workaround
        if self.conn_type == 'normal':
            with Session() as connection:
                conn = Connection(url, connection)
        elif self.conn_type == 'cloudflare':
            with cfscrape.create_scraper() as connection:
                conn = Connection(url, connection)
        else:
            raise Exception('Connection type is invalid, set conn_type to \'normal\' or \'cloudflare\'')
        conn.received += self.debug
        conn.error += self.error
        corehub = conn.register_hub('coreHub')
        conn_object = {'connection': conn, 'corehub': corehub}
        return conn_object

    def _get_subscribe_commands(self):
        return ['SubscribeToExchangeDeltas']

    def _subscribe(self, conn_object, tickers):
        conn, corehub = conn_object['connection'], conn_object['corehub']
        print('Establishing ticker update connection...')
        try:
            conn.start()
            print('Ticker update connection established.')
            # Subscribe for changes in the order book
            corehub.client.on('updateExchangeState', self.ticker_data)
            cmds = self._get_subscribe_commands()
            for k, cmd in enumerate(cmds):
                for i, ticker in enumerate(tickers):
                    corehub.server.invoke(cmd, ticker)
                    if i == len(tickers) - 1:
                        sleep(5)
            # Close the connection if no message is received after timeout value.
            conn.wait(self.timeout)
        except Exception as e:
            print(e)
            print('Failed to establish connection')
            return

    # Error handler
    def error(self, error):
        print(error)
        print('Quitting')
        sys.exit(0)

    # Debug information, shows all data
    def debug(self, **kwargs):
        print(kwargs)

    # Ticker update event
    def ticker_data(self, *args, **kwargs):
        print(args[0])

    def market_data(self, *args, **kwargs):
        pass


def main():
    a = BittrexSocket(['BTC-ETH', 'ETH-1ST', 'BTC-1ST', 'BTC-NEO', 'ETH-NEO'])
    a.run()
    b = None
    while 1 > 0:
        sleep(60)


if __name__ == "__main__":
    main()
