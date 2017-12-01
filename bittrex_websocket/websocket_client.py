#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/websocket_client.py
# Stanislav Lazarov

from __future__ import print_function

import logging
from abc import ABCMeta, abstractmethod
from threading import Thread, current_thread
from time import sleep, time

import cfscrape
from events import Events
from signalr import Connection
from websocket import WebSocketConnectionClosedException

from bittrex_websocket.auxiliary import Ticker, ConnectEvent, DisconnectEvent, SubscribeEvent, UnsubscribeEvent, \
    SnapshotEvent, \
    BittrexConnection

logging.basicConfig(level=logging.DEBUG)

try:
    import Queue as queue
except ImportError:
    import queue


class WebSocket(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def subscribe_to_orderbook(self, tickers, book_depth):
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

    @abstractmethod
    def unsubscribe_to_orderbook(self, tickers):
        # Subscribe and maintain the live order book for a set of ticker(s)
        raise NotImplementedError("Should implement unsubscribe_to_orderbook()")

    @abstractmethod
    def unsubscribe_to_orderbook_update(self, tickers):
        # Subscribe to order book updates for a set of ticker(s)
        raise NotImplementedError("Should implement unsubscribe_to_orderbook_update")

    @abstractmethod
    def unsubscribe_to_trades(self, tickers):
        # Subscribe and receive tick data(executed trades) for a set of ticker(s)
        raise NotImplementedError("Should implement unsubscribe_to_trades()")

    @abstractmethod
    def unsubscribe_to_ticker_update(self, tickers):
        """
        Subscribe and receive general data updates for a set of ticker(s). Example output:
        """
        raise NotImplementedError("Should implement unsubscribe_to_ticker_update()")

    @abstractmethod
    def disconnect(self):
        """
        Disconnects the connections and stops the websocket instance
        """
        raise NotImplementedError("Should implement disconnect()")


class BittrexSocket(WebSocket):
    def __init__(self):
        """

        """
        self.tickers = Ticker()
        self.conn_list = []
        self.threads = {}
        self.url = 'http://socket-stage.bittrex.com/signalr'
        # Internal callbacks
        # --self.queryExchangeState = Events()
        # --self.queryExchangeState.on_change += self.on_message
        self.updateSummaryState = Events()
        self.updateSummaryState.on_change += self.on_ticker_update
        self.orderbook_callback = Events()
        self.orderbook_callback.on_change += self.on_orderbook
        self.orderbook_update = Events()
        self.orderbook_update.on_change += self.on_orderbook_update
        self.trades = Events()
        self.trades.on_change += self.on_trades
        # Queues
        self.control_queue = queue.Queue()
        self.order_queue = None
        self._start_main_thread()
        # Test
        self.conn_list_new = {}
        self.order_book = {}
        self.max_tickers_per_conn = 20

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
        self.threads[thread.getName()] = thread
        thread.start()

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
                        if self._handle_disconnect():
                            self.on_close()
                            break
                    if control_event.type == 'SUBSCRIBE':
                        self._handle_subscribe(control_event)
                    if control_event.type == 'UNSUBSCRIBE':
                        self._handle_unsubscribe(control_event)
                    if control_event.type == 'SNAPSHOT':
                        self._handle_get_snapshot(control_event)

    def _handle_connect(self, conn_event: ConnectEvent):
        """
        Start a new Bittrex connection in a new thread
        :param conn_event: Contains the connection object.
        :type conn_event: ConnectEvent
        """
        thread = Thread(target=self._init_connection, args=(conn_event.conn_obj,))
        self.threads[thread.getName()] = thread
        conn_event.conn_obj.assign_thread(thread.getName())
        self.conn_list.append(conn_event.conn_obj)
        self.conn_list_new.update({conn_event.conn_obj.id: conn_event.conn_obj})
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

    def _handle_disconnect(self):
        """
        Closing a connection from an external error results in an error.
        We set a close_me flag so that next time when a message is received
        from the thread that started the connection, a method will be called to close it.
        """
        for conn in self.conn_list_new.values():
            conn.close()
            while conn.state:
                sleep(0.5)
        logging.debug('The websocket client instance has been successfully closed.')
        return True

    @staticmethod
    def _handle_subscribe(sub_event: SubscribeEvent):
        conn, server_callback, tickers = sub_event.conn_object, sub_event.server_callback, sub_event.tickers
        while conn.state is False:
            sleep(0.2)
        else:
            try:
                for cb in server_callback:
                    for ticker in tickers:
                        conn.corehub.server.invoke(cb, ticker)
                        conn.increment_ticker()
            except Exception as e:
                print(e)
                print('Failed to subscribe')

    def _handle_unsubscribe(self, unsub_event: UnsubscribeEvent):
        ticker, sub_type, conn_id = unsub_event.ticker, unsub_event.sub_type, unsub_event.conn_id
        logging.debug('Unsubscribing {} for {}.'.format(sub_type, ticker))
        self.tickers.change_sub_state(ticker, sub_type, Ticker.SUB_STATE_OFF)
        self.tickers.remove_conn_id(ticker, sub_type)

    def _get_ordernum_in_queue(self, ticker):
        # ADD BETTER ERROR HANDLING FOR THIS
        match = 0
        for item in list(self.order_queue.queue):
            if item['MarketName'] == ticker:
                match += 1
        return match

    def _handle_get_snapshot(self, snapshot_event: SnapshotEvent):
        conn, ticker = snapshot_event.conn_object, snapshot_event.ticker
        method = 'queryExchangeState'
        # Wait for the connection to start successfully and record 2 nounces of data
        while conn.state is False or self._get_ordernum_in_queue(ticker) < 2:
            sleep(0.2)
        else:
            try:
                logging.debug('Requesting snapshot for {}.'.format(ticker))
                conn.corehub.server.invoke(method, ticker)
                self.tickers.set_snapshot_state(ticker, Ticker.SNAPSHOT_SENT)
            except Exception as e:
                print(e)
                print('Failed to invoke snapshot query')
        while self.tickers.get_snapshot_state(ticker) is not Ticker.SNAPSHOT_ON:
            sleep(0.5)
            # print('lol')

    def _is_first_run(self, tickers, sub_type):
        # Check if the websocket is has been initiated already or if it's the first run
        if not self.tickers.list:
            self.on_open()
            self._subscribe_first_run(tickers, sub_type)

    def _subscribe_first_run(self, tickers, sub_type, objects=None):
        for ticker in tickers:
            self.tickers.add(ticker)
            self.tickers.change_sub_state(ticker, sub_type, True)
        if objects is None:
            objects = self._start2(tickers)
        for obj in objects:
            self.tickers.assign_conn_id(obj[0], sub_type, obj[1].id)
            self.control_queue.put(ConnectEvent(obj[1]))
            self.control_queue.put(SubscribeEvent(obj[0], obj[1], sub_type))

    def _unsubscribe(self, tickers, sub_type):
        for ticker in tickers:
            event = UnsubscribeEvent(ticker, self.tickers, sub_type)
            self.control_queue.put(event)

    def _get_snapshot(self, tickers):
        for ticker_name in tickers:
            ticker_object = self.tickers.list[ticker_name]
            conn_id = ticker_object['OrderBook']['ConnectionID']
            # Due to multithreading the connection might not be added to the connection list yet
            while True:
                try:
                    conn = self.conn_list_new[conn_id]
                except KeyError:
                    continue
                else:
                    break
            self.control_queue.put(SnapshotEvent(ticker_name, conn))

    def _is_order_queue(self):
        if self.order_queue is None:
            self.order_queue = queue.Queue()
            thread = Thread(target=self._start_order_queue)
            thread.daemon = True
            self.threads[thread.getName()] = thread
            thread.start()

    def _start_order_queue(self):
        while True:
            try:
                order_event = self.order_queue.get()
            except queue.Empty:
                pass
            else:
                if order_event is not None:
                    ticker = order_event['MarketName']
                    snapshot_state = self.tickers.list[ticker]['OrderBook']['SnapshotState']
                    # Awaiting snapshot, put the order event back in the queue
                    if snapshot_state in [Ticker.SNAPSHOT_OFF, Ticker.SNAPSHOT_SENT]:
                        self.order_queue.put(order_event)
                    elif snapshot_state == Ticker.SNAPSHOT_RCVD:
                        if self._sync_order_book(ticker, order_event):
                            self.tickers.set_snapshot_state(ticker, Ticker.SNAPSHOT_ON)
                    else:
                        self._sync_order_book(ticker, order_event)
                        self.orderbook_callback.on_change(self.order_book[ticker])
                    self.order_queue.task_done()

    def _is_running(self, tickers, sub_type):
        # Check for existing connections
        if not self.conn_list_new:
            for conn in self.conn_list_new.values():
                # Check if connection is alive and it's not flagged for disconnection
                if conn.state is True and conn.close_me is False:
                    # Check if the ticker quota has been reached
                    free_slots = self.max_tickers_per_conn - conn.ticker_count
                    # Use existing connection
                    if free_slots > 0:
                        tickers_chunk = tickers[0:free_slots]
                        del tickers[0:free_slots]
                        for ticker in tickers_chunk:
                            self.tickers.add(ticker)
                            self.tickers.change_sub_state(ticker, sub_type, True)
                        self.tickers.assign_conn_id(tickers_chunk, sub_type, conn.id)
                        self.control_queue.put(SubscribeEvent(tickers_chunk, conn, sub_type))
            # The quota of the existing connections is filled -> create new connections
            if len(tickers) > 0:
                self._subscribe_first_run(tickers, sub_type)

    # ==============
    # Public Methods
    # ==============

    # -----------------
    # Subscribe Methods
    # -----------------

    def subscribe_to_orderbook(self, tickers, book_depth=10):
        sub_type = Ticker.SUB_TYPE_ORDERBOOK
        self._is_order_queue()
        self._is_first_run(tickers, sub_type)
        self._is_running(tickers, sub_type)
        self.tickers.set_book_depth(tickers, book_depth)
        self._get_snapshot(tickers)

    def subscribe_to_orderbook_update(self, tickers):
        sub_type = Ticker.SUB_TYPE_ORDERBOOKUPDATE
        self._is_first_run(tickers, sub_type)

    def subscribe_to_trades(self, tickers):
        sub_type = Ticker.SUB_TYPE_TRADES
        self._is_first_run(tickers, sub_type)

    def subscribe_to_ticker_update(self, tickers):
        sub_type = Ticker.SUB_TYPE_TICKERUPDATE
        self._is_first_run(tickers, sub_type)

    # -------------------
    # Unsubscribe Methods
    # -------------------

    def unsubscribe_to_orderbook(self, tickers):
        sub_type = Ticker.SUB_TYPE_ORDERBOOK
        self._unsubscribe(tickers, sub_type)

    def unsubscribe_to_orderbook_update(self, tickers):
        sub_type = Ticker.SUB_TYPE_ORDERBOOKUPDATE
        self._unsubscribe(tickers, sub_type)

    def unsubscribe_to_trades(self, tickers):
        sub_type = Ticker.SUB_TYPE_TRADES
        self._unsubscribe(tickers, sub_type)

    def unsubscribe_to_ticker_update(self, tickers):
        sub_type = Ticker.SUB_TYPE_TICKERUPDATE
        self._unsubscribe(tickers, sub_type)

    # -------------
    # Other Methods
    # -------------

    def disconnect(self):
        self.control_queue.put(DisconnectEvent())

    def _start2(self, tickers):
        results = []

        def get_chunks(l, n):
            # Yield successive n-sized chunks from l.
            for i in range(0, len(l), n):
                yield l[i:i + n]

        ticker_gen = get_chunks(list(tickers), 20)
        # Initiate a generator that splits the ticker list into chunks
        while True:
            try:
                chunk_list = next(ticker_gen)
            except StopIteration:
                break
            if chunk_list is not None:
                conn_obj = self._create_connection()
                results.append([chunk_list, conn_obj])
        return results

    def _create_connection(self):
        with cfscrape.create_scraper() as connection:
            conn = Connection(self.url, connection)
        conn.received += self._on_debug
        conn.error += self.on_error
        corehub = conn.register_hub('coreHub')
        return BittrexConnection(conn, corehub)

    def _is_orderbook_snapshot(self, msg):
        # Redirects full order book snapshots for a specific ticker to the main message channel (on_message).
        # That's because there is no corresponding server callback for queryExchangeState
        # which can be assigned to a data handling method.
        if 'R' in msg and type(msg['R']) is not bool:
            if 'MarketName' in msg['R'] and msg['R']['MarketName'] is None:
                for ticker in self.tickers.list.values():
                    if ticker['OrderBook']['SnapshotState'] == Ticker.SNAPSHOT_SENT:
                        # ticker['OrderBook']['Snapshot'] = msg
                        msg['R']['MarketName'] = ticker['Name']
                        del msg['R']['Fills']
                        self.order_book[ticker['Name']] = msg['R']
                        self.tickers.set_snapshot_state(ticker['Name'], Ticker.SNAPSHOT_RCVD)
                        break
                print('snapshot_got')

    # ========================
    # Private Channels Methods
    # ========================

    def _on_debug(self, **kwargs):
        """
        Debug information, shows all data
        Don't edit unless you know what you are doing.
        Redirect full order book snapshots to on_message
        """
        self._is_close_me()
        self._is_orderbook_snapshot(kwargs)

    def _on_tick_update(self, msg):
        self._is_close_me()
        subs = self.tickers.list[msg['MarketName']]
        if subs['OrderBook']['Active'] is True:
            self.order_queue.put(msg)
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

    def _on_ticker_update(self, msg):
        """
        Invoking summary state updates for specific filter
        doesn't work right now. So we will filter them manually.
        """
        self._is_close_me()
        ticker_updates = {}
        if 'Deltas' in msg:
            for update in msg['Deltas']:
                try:
                    ticker = update['MarketName']
                    subs = self.tickers.get_ticker_subs(ticker)
                except KeyError:  # not in the subscription list
                    continue
                else:
                    if subs['TickerUpdate']['Active']:
                        ticker_updates[ticker] = update
        if ticker_updates:
            self.updateSummaryState.on_change(ticker_updates)

    # -------------------------------------
    # Private Channels Supplemental Methods
    # -------------------------------------

    @staticmethod
    def _create_base_layout(msg):
        d = {'ticker': msg['MarketName'],
             'nounce': msg['Nounce'],
             'timestamp': time()
             }
        return d

    def _sync_order_book(self, pair_name, order_data):
        # Syncs the order book for the pair, given the most recent data from the socket
        book_depth = self.tickers.list[pair_name]['OrderBook']['OrderBookDepth']
        nounce_diff = order_data['Nounce'] - self.order_book[pair_name]['Nounce']
        if nounce_diff == 1:
            self.order_book[pair_name]['Nounce'] = order_data['Nounce']
            # Start syncing
            for side in [['Buys', True], ['Sells', False]]:
                made_change = False

                for item in order_data[side[0]]:
                    # TYPE 0: New order entries at matching price
                    # -> ADD to order book
                    if item['Type'] == 0:
                        self.order_book[pair_name][side[0]].append(
                            {
                                'Quantity': item['Quantity'],
                                'Rate': item['Rate']
                            })
                        made_change = True

                    # TYPE 1: Cancelled / filled order entries at matching price
                    # -> DELETE from the order book
                    elif item['Type'] == 1:
                        for i, existing_order in enumerate(
                                self.order_book[pair_name][side[0]]):
                            if existing_order['Rate'] == item['Rate']:
                                del self.order_book[pair_name][side[0]][i]
                                made_change = True
                                break

                    # TYPE 2: Changed order entries at matching price (partial fills, cancellations)
                    # -> EDIT the order book
                    elif item['Type'] == 2:
                        for existing_order in self.order_book[pair_name][side[0]]:
                            if existing_order['Rate'] == item['Rate']:
                                existing_order['Quantity'] = item['Quantity']
                                made_change = True
                                break

                if made_change:
                    # Sort by price, with respect to BUY(desc) or SELL(asc)
                    self.order_book[pair_name][side[0]] = sorted(
                        self.order_book[pair_name][side[0]],
                        key=lambda k: k['Rate'],
                        reverse=side[1])
                    # Put depth to 10
                    self.order_book[pair_name][side[0]] = \
                        self.order_book[pair_name][side[0]][
                        0:book_depth]
                    # Add nounce unix timestamp
                    self.order_book[pair_name]['timestamp'] = time()

                    # tick='BTC-ZEC'
                    # if order_data['MarketName'] == tick:
                    #     buys = self.order_book[tick]['Buys'][0]
                    #     buys2 = self.order_book[tick]['Buys'][1]
                    #     sells = self.order_book[tick]['Sells'][0]
                    #     sells2 = self.order_book[tick]['Sells'][1]
                    #     print(str(buys) + str(buys2) + str(sells) + str(sells2))
            return True
        elif nounce_diff <= 0:
            return False
        else:
            raise NotImplementedError("Implement nounce resync!")

    def _is_close_me(self):
        thread_name = current_thread().getName()
        conn_object = self.threads[thread_name]._args[0]
        if conn_object.close_me:
            try:
                conn_object.conn.close()
            except WebSocketConnectionClosedException:
                pass
            conn_object.deactivate()

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
        self.disconnect()

    def on_message(self, msg):
        """
        !!!TO BE DEPRECATED!!!
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
        # if 'Deltas' in msg:
        #     self.updateSummaryState.on_change(msg)

    def on_orderbook(self, msg):
        print('Just updated the order book of ' + msg['MarketName'])

    def on_orderbook_update(self, msg):
        print('Just received order book updates for ' + msg['ticker'])

    def on_trades(self, msg):
        print('Just received trade update for ' + msg['ticker'])

    def on_ticker_update(self, msg):
        for item in msg.values():
            print('Just received ticker update for ' + item['MarketName'])


if __name__ == "__main__":
    t = ['BTC-ETH', 'ETH-ZEC', 'BTC-ZEC', 'BTC-NEO', 'ETH-NEO']
    ws = BittrexSocket()
    ws.subscribe_to_ticker_update(t)
    for i in range(100):
        # if ws.conn_list != []:
        #     if ws.conn_list[0]['corehub'].client._HubClient__handlers =={}:
        #         ws.conn_list[0]['corehub'].client.on('updateSummaryState', ws.on_message)
        sleep(1)
        if i == 15:
            ws.unsubscribe_to_ticker_update(t)
        # ws.stop()
