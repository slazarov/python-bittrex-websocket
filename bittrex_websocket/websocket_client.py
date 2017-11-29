#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/websocket_client.py
# Stanislav Lazarov

from __future__ import print_function

from abc import ABCMeta, abstractmethod
from threading import Thread
from time import sleep
from time import time

import cfscrape
from events import Events
from signalr import Connection

from .auxiliary import Ticker, ConnectEvent, SubscribeEvent, BittrexConnection

try:
    import Queue as queue
except ImportError:
    import queue


class WebSocket(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def subscribe_to_orderbook(self, tickers):
        # Subscribe and maintain the live order book for a set of ticker(s)
        raise NotImplementedError("Should implement subscribe_to_orderbook()")

    @abstractmethod
    def subscribe_to_orderbook_update(self, tickers):
        # Subscribe to order book updates for a set of ticker(s)
        raise NotImplementedError("Should implement subscribe_to_orderbook_update")

    @abstractmethod
    def subscribe_to_trades(self, tickers):
        # Subscribe and receive tick data(executed trades) for a set of ticker(s)
        raise NotImplementedError("Should implement subscribe_to_trades()")

    @abstractmethod
    def subscribe_to_ticker_update(self, tickers):
        """
        Subscribe and receive general data updates for a set of ticker(s). Example output:
        {
            'MarketName': 'BTC-ADA',
            'High': 7.65e-06,
            'Low': 4.78e-06,
            'Volume': 1352355429.5288217,
            'Last': 7.2e-06,
            'BaseVolume': 7937.59243908,
            'TimeStamp': '2017-11-28T15:02:17.7',
            'Bid': 7.2e-06,
            'Ask': 7.21e-06,
            'OpenBuyOrders': 4452,
            'OpenSellOrders': 3275,
            'PrevDay': 5.02e-06,
            'Created': '2017-09-29T07:01:58.873'
        }
        """
        raise NotImplementedError("Should implement subscribe_to_ticker_update()")


class BittrexSocket(WebSocket):
    def __init__(self):
        """

        """
        self.tickers = Ticker()
        self.conn_list = []
        self.threads = []
        self.url = 'http://socket-stage.bittrex.com/signalr'
        # Internal callbacks
        self.queryExchangeState = Events()
        self.queryExchangeState.on_change += self.on_message
        self.updateSummaryState = Events()
        self.updateSummaryState.on_change += self.on_ticker_update
        self.orderbook_update = Events()
        self.orderbook_update.on_change += self.on_orderbook_update
        self.trades = Events()
        self.trades.on_change += self.on_trades
        # Queues
        self.control_queue = queue.Queue()
        self._start_main_thread()

    # ===========================
    # Main Thread Private Methods
    # ===========================

    def _start_main_thread(self):
        """
        The websocket clients starts a separate thread upon
        initialization with further subthreads for each connection
        """
        thread = Thread(target=self._start_socket_control_queue)
        thread.daemon = True
        self.threads.append(thread)
        self.threads[0].start()

    # ---------------------
    # Control Queue Methods
    # ---------------------

    def _start_socket_control_queue(self):
        """
        Handles the communication with Bittrex, namely
        starting/closing a connection and un/subscribing to channels
        It stays idle until a command is send to it.
        """
        while True:
            try:
                control_event = self.control_queue.get()
            except queue.Empty:
                pass
            else:
                if control_event is not None:
                    if control_event.type == 'CONNECT':
                        self._handle_connect(control_event)
                    if control_event.type == 'DISCONNECT':
                        self._handle_disconnect(control_event)
                    if control_event.type == 'SUBSCRIBE':
                        self._handle_subscribe(control_event)
                    if control_event.type == 'UNSUBSCRIBE':
                        self._handle_unsubscribe(control_event)

    def _handle_connect(self, conn_event: ConnectEvent):
        """
        Start a new Bittrex connection in a new thread
        :param conn_event: Contains the connection object.
        :type conn_event: ConnectEvent
        """

        # Create thread
        thread = Thread(target=self._init_connection, args=(conn_event.conn_obj,))
        self.threads.append(thread)
        self.conn_list.append(conn_event.conn_obj)
        thread.start()

    def _init_connection(self, conn_obj: BittrexConnection):
        print('Establishing Bittrex connection...')
        conn, corehub = conn_obj.conn, conn_obj.corehub
        try:
            conn.start()
            conn_obj.activate()
            print('Connection to Bittrex established successfully.')
            # Add handlers
            corehub.client.on('updateExchangeState', self._on_tick_update)
            corehub.client.on('updateSummaryState', self._on_ticker_update)
            conn.wait(120000)
        except Exception as e:
            print(e)
            print('Failed to establish connection')

    def _handle_disconnect(self, conn_event):
        pass

    @staticmethod
    def _handle_subscribe(sub_event: SubscribeEvent):
        conn, server_callback, tickers = sub_event.conn_object, sub_event.server_callback, sub_event.tickers
        while conn.conn_state is False:
            sleep(0.2)
        else:
            try:
                for cb in server_callback:
                    for ticker in tickers:
                        conn.corehub.server.invoke(cb, ticker)
            except Exception as e:
                print(e)
                print('Failed to subscribe')

    def _handle_unsubscribe(self, control_event):
        pass

    def _is_first_run(self, tickers, sub_type):
        # Check if the websocket is has been initiated already or if it's the first run
        if not self.tickers.list:
            self._subscribe_first_run(tickers, sub_type)

    def _subscribe_first_run(self, tickers, sub_type):
        for ticker in tickers:
            self.tickers.add(ticker)
            self.tickers.change_sub_state(ticker, sub_type, True)
        objects = self._start2()
        for obj in objects:
            self.tickers.assign_conn_id(obj[0], sub_type, obj[1].id)
            self.control_queue.put(ConnectEvent(obj[1]))
            self.control_queue.put(SubscribeEvent(obj[0], obj[1], sub_type))

    # ==============
    # Public Methods
    # ==============

    def subscribe_to_orderbook(self, tickers):
        sub_type = 'OrderBook'
        self._is_first_run(tickers, sub_type)

    def subscribe_to_orderbook_update(self, tickers):
        sub_type = 'OrderBookUpdate'
        self._is_first_run(tickers, sub_type)

    def subscribe_to_trades(self, tickers):
        sub_type = 'Trades'
        self._is_first_run(tickers, sub_type)

    def subscribe_to_ticker_update(self, tickers):
        sub_type = 'TickerUpdate'
        self._is_first_run(tickers, sub_type)

    def run_old(self):
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
            for cb in self.client_callbacks:
                conn['corehub'].client.off(cb, self.on_message)
            conn['connection'].close()
        self.on_close()

    def _start2(self):
        results = []

        def get_chunks(l, n):
            # Yield successive n-sized chunks from l.
            for i in range(0, len(l), n):
                yield l[i:i + n]

        ticker_gen = get_chunks(list(self.tickers.list.keys()), 20)
        # Initiate a generator that splits the ticker list into chunks
        while True:
            try:
                chunk_list = next(ticker_gen)
            except StopIteration:
                break
            if chunk_list is not None:
                conn_obj = self._create_connection()
                self.conn_list.append(conn_obj)
                results.append([chunk_list, conn_obj])
        return results

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
                thread = Thread(target=self._subscribe_old, args=(conn_obj, chunk_list))
                self.threads.append(thread)
                conn_obj['thread-name'] = thread.getName()
                self.conn_list.append(conn_obj)
                thread.start()
        return

    def _create_connection(self):
        with cfscrape.create_scraper() as connection:
            conn = Connection(self.url, connection)
        conn.received += self.on_debug
        conn.error += self.on_error
        corehub = conn.register_hub('coreHub')
        return BittrexConnection(conn, corehub)

    def _subscribe_old(self, conn_object, tickers):
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

    def _is_orderbook_snapshot(self, msg):
        # Redirects full order book snapshots for a specific ticker to the main message channel (on_message).
        # That's because there is no corresponding server callback for queryExchangeState
        # which can be assigned to a data handling method.
        if 'R' in msg and type(msg['R']) is not bool:
            msg['R']['MessageType'] = 'OrderbookSnapshot'
            self.queryExchangeState.on_change(msg['R'])

    # ========================
    # Private Channels Methods
    # ========================

    def _on_tick_update(self, msg):
        subs = self.tickers.list[msg['MarketName']]
        if subs['OrderBook']['Active'] is True:
            pass
        if subs['OrderBookUpdate']['Active'] is True:
            if msg['Buys'] or msg['Sells']:
                d = dict(self._create_base_layout(msg),
                         **{'bids': msg['Buys'],
                            'asks': msg['Sells']})
                self.orderbook_update.on_change(d)
        if subs['Trades']['Active'] is True:
            if msg['Fills']:
                d = dict(self._create_base_layout(msg),
                         **{'trades': msg['Fills']})
                self.trades.on_change(d)

    @staticmethod
    def _create_base_layout(msg):
        d = {'ticker': msg['MarketName'],
             'nounce': msg['Nounce'],
             'timestamp': time()
             }
        return d

    def _on_ticker_update(self, msg):
        pass

    # ===============
    # Public Channels
    # ===============

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
        # Don't edit unless you know what you are doing.
        # Redirect full order book snapshots to on_message
        self._is_orderbook_snapshot(kwargs)

    def on_trades(self, msg):
        pass

    def on_message(self, msg):
        """
        This is where you get the order flow stream.
        Subscribed via 'updateExchangeState'
        Access it from args[0]
        Example output:
            {
                'MarketName': 'BTC-ETH',
                'Nounce': 101846,
                'Buys': [{'Type': 1, 'Rate': 0.05369548, 'Quantity': 0.0}],
                'Sells': [{'Type': 2, 'Rate': 0.05373854, 'Quantity': 62.48260112}],
                'Fills': [{'OrderType': 'BUY', 'Rate': 0.05373854, 'Quantity': 0.88839888,
                           'TimeStamp': '2017-11-24T13:18:43.44'}]
            }
        """
        # Implement summary state later
        if 'Deltas' in msg:
            self.updateSummaryState.on_change(msg)
        else:
            print('hi')

    def on_orderbook_update(self, msg):
        pass

    def on_ticker_update(self, msg):
        pass


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


    t = ['BTC-ETH', 'ETH-1ST', 'BTC-1ST', 'BTC-NEO', 'ETH-NEO']
    ws = MyBittrexSocket(t)
    ws.run_old()
    while ws.msg_count < 20:
        sleep(1)
        continue
    else:
        for message in ws.nounces:
            print(message)
    ws.stop()
