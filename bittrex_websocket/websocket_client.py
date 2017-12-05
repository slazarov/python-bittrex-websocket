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
from requests.exceptions import HTTPError, MissingSchema
from signalr import Connection
from websocket import WebSocketConnectionClosedException

from bittrex_websocket.auxiliary import Ticker, BittrexConnection
from ._queue_events import SubscribeInternalEvent, ConnectEvent, DisconnectEvent, SubscribeEvent, UnsubscribeEvent, \
    SnapshotEvent

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
        self.threads = {}
        self.url = ['https://socket-stage.bittrex.com/signalr',
                    'https://socket.bittrex.com/signalr',
                    'https://socket-beta.bittrex.com/signalr']
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
        self.conn_list = {}
        self.order_book = {}
        self.max_tickers_per_conn = 1

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
                    elif control_event.type == 'DISCONNECT':
                        if self._handle_disconnect(control_event):
                            self.on_close()
                            break
                    elif control_event.type == 'SUBSCRIBE':
                        self._handle_subscribe(control_event)
                    elif control_event.type == 'SUBSCRIBE_INTERNAL':
                        self._handle_subscribe_internal(control_event)
                    elif control_event.type == 'UNSUBSCRIBE':
                        self._handle_unsubscribe(control_event)
                    elif control_event.type == 'SNAPSHOT':
                        self._handle_get_snapshot(control_event)
                    sleep(0.2)

    def _handle_connect(self, conn_event: ConnectEvent):
        """
        Start a new Bittrex connection in a new thread
        :param conn_event: Contains the connection object.
        :type conn_event: ConnectEvent
        """
        thread = Thread(target=self._init_connection, args=(conn_event.conn_obj,))
        self.threads[thread.getName()] = thread
        conn_event.conn_obj.assign_thread(thread.getName())
        self.conn_list.update({conn_event.conn_obj.id: conn_event.conn_obj})
        thread.start()

    def _init_connection(self, conn_obj: BittrexConnection):
        print('Establishing Bittrex connection...')
        conn, corehub = conn_obj.conn, conn_obj.corehub
        for url in self.url:
            try:
                conn.url = url
                conn.start()
                conn_obj.activate()
                logging.debug('Connection to Bittrex established successfully through {}.'.format(url))
                # Add handlers
                corehub.client.on('updateExchangeState', self._on_tick_update)
                corehub.client.on('updateSummaryState', self._on_ticker_update)
                conn.wait(120000)
            except HTTPError:
                logging.debug('Failed to establish connection through {}'.format(url))
            except MissingSchema:
                logging.debug('Invalid URL: {}'.format(url))
        else:
            logging.debug('Failed to establish connection to Bittrex through all supplied URLS. Closing the socket')
            return

    def _handle_disconnect(self, disconn_event):
        """
        Closing a connection from an external error results in an error.
        We set a close_me flag so that next time when a message is received
        from the thread that started the connection, a method will be called to close it.

        Returns True if all connections have to be closed.
        Returns False if only specific has to be closed.
        """

        # Find whether we are closing all connections or just one.
        if disconn_event.conn_object is None:
            conns = self.conn_list.values()
            msg = 'The websocket client instance has been successfully closed.'
            flag = True
        else:
            conns = disconn_event.conn_object
            msg = 'Connection {} has been successfully closed.'.format(conns[0].id)
            flag = False
        for conn in conns:
            conn.close()
            while conn.state:
                sleep(0.5)
        logging.debug(msg)
        return flag

    def _handle_subscribe(self, sub_event: SubscribeEvent):
        conn = sub_event.conn_object
        server_callback = sub_event.server_callback
        server_callback_no_payload = sub_event.server_callback_no_payload
        tickers = sub_event.tickers
        sub_type = sub_event.sub_type
        self.tickers.enable(tickers, sub_type, conn.id)
        while conn.state is False:
            sleep(0.2)
        else:
            try:
                if server_callback is not None:
                    conn.set_callback_state(BittrexConnection.CALLBACK_EXCHANGE_DELTAS,
                                            BittrexConnection.CALLBACK_STATE_ON)
                    for cb in server_callback:
                        for ticker in tickers:
                            conn.corehub.server.invoke(cb, ticker)
                            conn.increment_ticker()
                if server_callback_no_payload is not None:
                    conn.set_callback_state(BittrexConnection.CALLBACK_SUMMARY_DELTAS,
                                            BittrexConnection.CALLBACK_STATE_ON)
                    for cb in server_callback_no_payload:
                        conn.corehub.server.invoke(cb)
                        conn.set_callback_state(cb, conn.CALLBACK_STATE_ON)
            except Exception as e:
                print(e)
                print('Failed to subscribe')

    def _handle_subscribe_internal(self, sub_event: SubscribeInternalEvent):
        tickers = sub_event.tickers
        conn = sub_event.conn_object
        sub_type = sub_event.sub_type
        self.tickers.enable(tickers, sub_type, conn.id)

    def _handle_unsubscribe(self, unsub_event: UnsubscribeEvent):
        ticker, sub_type, conn_id = unsub_event.ticker, unsub_event.sub_type, unsub_event.conn_id
        self.tickers.disable(ticker, sub_type, conn_id)
        self._is_no_subs_active()

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
                logging.debug(
                    '[Subscription][{}][{}]: Order book snapshot requested.'.format(Ticker.SUB_TYPE_ORDERBOOK, ticker))
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
        else:
            return False

    def _subscribe_first_run(self, tickers, sub_type, objects=None):
        if objects is None:
            objects = self._create_connection(tickers)
        for obj in objects:
            self.control_queue.put(ConnectEvent(obj[1]))
            self.control_queue.put(SubscribeEvent(obj[0], obj[1], sub_type))

    def _unsubscribe(self, tickers, sub_type):
        for ticker in tickers:
            event = UnsubscribeEvent(ticker, self.tickers, sub_type)
            self.control_queue.put(event)

    def _get_snapshot(self, tickers):
        for ticker_name in tickers:
            ticker_object = self.tickers.list[ticker_name]
            conn_id = self.tickers.get_sub_type_conn_id(ticker_name, Ticker.SUB_TYPE_ORDERBOOK)
            # Due to multithreading the connection might not be added to the connection list yet
            while True:
                try:
                    conn = self.conn_list[conn_id]
                except KeyError:
                    sleep(0.5)
                    conn_id = self.tickers.get_sub_type_conn_id(ticker_name, Ticker.SUB_TYPE_ORDERBOOK)
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
        if self.conn_list:
            # Check for already existing tickers and enable the subscription before opening a new connection
            common_tickers = set(tickers) & set(self.tickers.list)  # common
            new_tickers = set(tickers) - set(self.tickers.list)  # unique
            for ticker in tickers:
                if self.tickers.get_sub_state(ticker, sub_type) is Ticker.SUB_STATE_ON:
                    logging.debug('{} subscription is already enabled for {}. Ignoring...'.format(sub_type, ticker))
                else:
                    # Assign most suitable connection
                    events = self._assign_conn(ticker, sub_type)
                    for event in events:
                        self.control_queue.put(event)
                    # [self.control_queue.put(event) for event in events]

    def _assign_conn(self, ticker, sub_type):
        conns = self.tickers.sort_by_callbacks()
        d = {}
        if sub_type == Ticker.SUB_TYPE_TICKERUPDATE:
            # Check for connection with enabled 'CALLBACK_SUMMARY_DELTAS'
            for conn in conns.keys():
                if BittrexConnection.CALLBACK_SUMMARY_DELTAS in conns[conn]:
                    d.update({conns[conn]['{} count'.format(BittrexConnection.CALLBACK_EXCHANGE_DELTAS)]: conn})
            # and get the connection with the lowest number of tickers.
            if d:
                min_tickers = min(d.keys())
                conn_id = d[min_tickers]
                return [SubscribeInternalEvent(ticker, self.conn_list[conn_id], sub_type)]
            # No connection found with 'CALLBACK_SUMMARY_DELTAS'.
            # Get the connection with the lowest number of tickers.
            else:
                for conn in conns.keys():
                    d.update({conns[conn]['{} count'.format(BittrexConnection.CALLBACK_EXCHANGE_DELTAS)]: conn})
                min_tickers = min(d.keys())
                conn_id = d[min_tickers]
                return [SubscribeEvent(ticker, self.conn_list[conn_id], sub_type)]
        else:
            # If 'EXCHANGE_DELTAS' is enabled for the ticker
            # and the specific connection, we just need to find the
            # connection and enable the subscription state in order
            # to stop filtering the messages.
            for conn in conns.keys():
                try:
                    if ticker in conns[conn][BittrexConnection.CALLBACK_EXCHANGE_DELTAS]:
                        return [SubscribeInternalEvent(ticker, self.conn_list[conn], sub_type)]
                except KeyError:
                    break
            # If there is no active subscription for the ticker,
            # check if there is enough quota and add the subscription to
            # an existing connection.
            for conn in conns.keys():
                d.update({conns[conn]['Ticker count']: conn})
            min_tickers = min(d.keys())
            if min_tickers < self.max_tickers_per_conn:
                conn_id = d[min_tickers]
                return SubscribeEvent(ticker, self.conn_list[conn_id], sub_type)
            # The existing connections are in full capacity, create a new connection and subscribe.
            else:
                obj = self._create_connection([ticker])[0]
                conn_event = ConnectEvent(obj[1])
                sub_event = SubscribeEvent(ticker, obj[1], sub_type)
                return [conn_event, sub_event]

    def _is_no_subs_active(self):
        active_conns = self.tickers.sort_by_callbacks()
        # Close the websocket if no active connections
        if not active_conns:
            self.disconnect()
        else:
            # Check for non-active connections and close ONLY them.
            non_active = set(self.conn_list) - set(active_conns)
            if non_active:
                for conn in non_active:
                    logging.debug('Connection {} has no active subscriptions. Closing it...'.format(conn))
                    conn_object = self.conn_list[conn]
                    disconnect_event = DisconnectEvent(conn_object)
                    self.control_queue.put(disconnect_event)

    # ==============
    # Public Methods
    # ==============

    # -----------------
    # Subscribe Methods
    # -----------------

    def subscribe_to_orderbook(self, tickers, book_depth=10):
        sub_type = Ticker.SUB_TYPE_ORDERBOOK
        self._is_order_queue()
        if self._is_first_run(tickers, sub_type) is False:
            self._is_running(tickers, sub_type)
        self.tickers.set_book_depth(tickers, book_depth)
        self._get_snapshot(tickers)

    def subscribe_to_orderbook_update(self, tickers):
        sub_type = Ticker.SUB_TYPE_ORDERBOOKUPDATE
        if self._is_first_run(tickers, sub_type) is False:
            self._is_running(tickers, sub_type)

    def subscribe_to_trades(self, tickers):
        sub_type = Ticker.SUB_TYPE_TRADES
        if self._is_first_run(tickers, sub_type) is False:
            self._is_running(tickers, sub_type)

    def subscribe_to_ticker_update(self, tickers):
        sub_type = Ticker.SUB_TYPE_TICKERUPDATE
        if self._is_first_run(tickers, sub_type) is False:
            self._is_running(tickers, sub_type)

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

    def _create_connection(self, tickers):
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
                conn_obj = self._create_signalr_connection()
                results.append([chunk_list, conn_obj])
        return results

    def _create_signalr_connection(self):
        with cfscrape.create_scraper() as connection:
            conn = Connection(None, connection)
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
                logging.debug(
                    '[Subscription][{}][{}]: Order book snapshot received.'.format(Ticker.SUB_TYPE_ORDERBOOK,
                                                                                   msg['R']['MarketName']))

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
