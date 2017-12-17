#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/websocket_client.py
# Stanislav Lazarov

from __future__ import print_function

import logging
from abc import ABCMeta, abstractmethod
from threading import Thread, current_thread

import cfscrape
from events import Events
from requests.exceptions import HTTPError, MissingSchema
from signalr import Connection
from time import sleep, time
from websocket import WebSocketConnectionClosedException

from ._auxiliary import BittrexConnection
from ._logger import add_stream_logger, remove_stream_logger
from ._queue_events import *
from .constants import *

logger = logging.getLogger(__name__)

try:
    import Queue as queue
except ImportError:
    import queue


class WebSocket(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def subscribe_to_orderbook(self, tickers, book_depth=10):
        """
        Subscribe and maintain the live order book for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        :param book_depth: The desired depth of the order book to be maintained.
        :type book_depth: int
        """
        raise NotImplementedError("Should implement subscribe_to_orderbook()")

    @abstractmethod
    def subscribe_to_orderbook_update(self, tickers):
        """
        Subscribe to order book updates for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """
        raise NotImplementedError("Should implement subscribe_to_orderbook_update")

    @abstractmethod
    def subscribe_to_trades(self, tickers):
        """
        Subscribe and receive tick data(executed trades) for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """
        raise NotImplementedError("Should implement subscribe_to_trades()")

    @abstractmethod
    def subscribe_to_ticker_update(self, tickers=None):
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

        :param tickers: A list of tickers you are interested in.
        :type tickers: [] or None
        """
        raise NotImplementedError("Should implement subscribe_to_ticker_update()")

    @abstractmethod
    def unsubscribe_to_orderbook(self, tickers):
        """
        Unsubscribe from real time order for specific set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """
        raise NotImplementedError("Should implement unsubscribe_to_orderbook()")

    @abstractmethod
    def unsubscribe_to_orderbook_update(self, tickers):
        """
        Unsubscribe from order book updates for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """
        raise NotImplementedError("Should implement unsubscribe_to_orderbook_update")

    @abstractmethod
    def unsubscribe_to_trades(self, tickers):
        """
        Unsubscribe from receiving tick data(executed trades) for a set of ticker(s)

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """
        raise NotImplementedError("Should implement unsubscribe_to_trades()")

    @abstractmethod
    def unsubscribe_to_ticker_update(self, tickers=None):
        """
        Unsubscribe from receiving general data updates for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: [] or None
        """
        raise NotImplementedError("Should implement unsubscribe_to_ticker_update()")

    @abstractmethod
    def get_order_book(self, ticker=None):
        """
        Returns the most recently updated order book for the specific ticker.
        If no ticker is specified, returns a dictionary with the order books of
        all subscribed tickers.

        :param ticker: The specific ticker you want the order book for.
        :type ticker: str
        """
        raise NotImplementedError("Should implement get_order_book()")

    @abstractmethod
    def get_order_book_sync_state(self, tickers=None):
        """
        Returns the sync state of the order book for the specific ticker(s).
        If no ticker is specified, returns the state for all tickers.
        The sync states are:

            Not initiated = 0
            Invoked, not synced = 1
            Received, not synced, not processing = 2
            Received, synced, processing = 3

        :param tickers: The specific ticker(s) and it's order book sync state you are interested in.
        :type tickers: []
        """
        raise NotImplementedError("Should implement get_order_book_sync_state()")

    @abstractmethod
    def disconnect(self):
        """
        Disconnects the connections and stops the websocket instance.
        """
        raise NotImplementedError("Should implement disconnect()")

    @staticmethod
    @abstractmethod
    def enable_log(file_name=None):
        """
        Enables logging.

        :param file_name: The name of the log file, located in the same directory as the executing script.
        :type file_name: str
        """
        raise NotImplementedError("Should implement enable_log()")

    @staticmethod
    @abstractmethod
    def disable_log():
        """
        Disables logging.
        """
        raise NotImplementedError("Should implement disable_log()")


class BittrexSocket(WebSocket):
    def __init__(self):
        # Event handlers
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
        # Other
        self.connections = {}
        self.order_books = {}
        self.threads = {}
        self.url = ['https://socket-stage.bittrex.com/signalr',
                    'https://socket.bittrex.com/signalr',
                    'https://socket-beta.bittrex.com/signalr']
        self.tickers = Ticker()
        self.max_tickers_per_conn = 20
        self._start_main_thread()

    # ===========================
    # Main Thread Private Methods
    # ===========================

    def _start_main_thread(self):
        """
        The websocket clients starts a separate thread upon
        initialization with further subthreads for each connection.
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
                    self.control_queue.task_done()

    def _handle_connect(self, conn_event):
        """
        Prepares and starts new thread for a new Bittrex connection.

        :param conn_event: Contains the connection object.
        :type conn_event: ConnectEvent
        """
        thread = Thread(target=self._init_connection, args=(conn_event.conn_obj,))
        self.threads[thread.getName()] = thread
        conn_event.conn_obj.assign_thread(thread.getName())
        self.connections.update({conn_event.conn_obj.id: conn_event.conn_obj})
        thread.start()

    def _init_connection(self, conn_obj):
        """
        Initiates the Bittrex connection and assigns event handlers.

        :param conn_obj: The Bittrex connection object
        :type conn_obj: BittrexConnection
        """
        conn, corehub = conn_obj.conn, conn_obj.corehub
        for url in self.url:
            try:
                logger.info('Trying to establish connection to Bittrex through {}.'.format(url))
                conn.url = url
                conn.start()
                conn_obj.activate()
                logger.info('Connection to Bittrex established successfully through {}.'.format(url))
                # Add handlers
                corehub.client.on('updateExchangeState', self._on_tick_update)
                corehub.client.on('updateSummaryState', self._on_ticker_update)
                conn.wait(120000)
                # When we purposely close the connection, the script will exit conn.wait()
                # so we need to inform the script that it should not try to reconnect.
                if conn_obj.close_me is True:
                    return
            except HTTPError:
                logger.info('Failed to establish connection through {}'.format(url))
            except MissingSchema:
                logger.info('Invalid URL: {}'.format(url))
        else:
            logger.info('Failed to establish connection to Bittrex through all supplied URLS. Closing the socket')
            return

    def _handle_disconnect(self, disconn_event):
        """
        Handles the event of disconnecting connections.

        :type disconn_event: The disconnect event.
        :type disconn_event: DisconnectEvent
        :return: True = all connections have to be closed; False = specific connection has to be closed.
        :rtype: bool
        """

        # Find whether we are closing all connections or just one.
        if disconn_event.conn_object is None:
            conns = self.connections.values()
            msg = 'Sending a close signal to all connections.'
            flag = True
        else:
            conns = disconn_event.conn_object
            msg = 'Sending a close signal to connection {}'.format(conns[0].id)
            flag = False

        # Closing a connection from an external error results in an error.
        # We set a close_me flag so that next time when a message is received
        # from the thread that started the connection, a method will be called to close it.
        for conn in conns:
            logger.info(msg)
            conn.close()
            while conn.state:
                sleep(0.5)
            logger.info('Connection {} has been successfully closed.'.format(conn.id))
        return flag

    def _handle_subscribe(self, sub_event):
        """
        Handles the event of subscribing a specific ticker to a specific subscription type.

        :param sub_event: The ticker subscription event
        :type sub_event: SubscribeEvent
        :return: False = Subscribing failed because the connection is not active.
        :rtype: bool
        """
        conn = sub_event.conn_object
        server_callback = sub_event.server_callback
        server_callback_no_payload = sub_event.server_callback_no_payload
        tickers = sub_event.tickers
        sub_type = sub_event.sub_type
        timeout = 0
        while conn.state is False:
            sleep(0.2)
            timeout += 1
            if timeout >= 100:
                logger.info(
                    'Failed to subscribe [{}][{}] from connection {} after 20 seconds. '
                    'The connection is probably down.'.format(sub_type, tickers, conn.id))
                return
        else:
            self.tickers.enable(tickers, sub_type, conn.id)
            try:
                if server_callback is not None:
                    conn.set_callback_state(CALLBACK_EXCHANGE_DELTAS,
                                            CALLBACK_STATE_ON)
                    for cb in server_callback:
                        for ticker in tickers:
                            conn.corehub.server.invoke(cb, ticker)
                            if self.tickers.get_sub_state(ticker, SUB_TYPE_ORDERBOOK) is True:
                                self._get_snapshot([ticker])
                            conn.increment_ticker()
                if server_callback_no_payload is not None:
                    if tickers == ALL_TICKERS:
                        state = CALLBACK_STATE_ON_ALLTICKERS
                    else:
                        state = CALLBACK_STATE_ON
                    conn.set_callback_state(CALLBACK_SUMMARY_DELTAS,
                                            state)
                    for cb in server_callback_no_payload:
                        conn.corehub.server.invoke(cb)
            except Exception as e:
                print(e)
                print('Failed to subscribe')

    def _handle_subscribe_internal(self, sub_event):
        """
        If the ticker is already in the tickers list and it shares a subscription
        callback for the new subscription request, then we don't have to invoke
        a request to Bittrex but only enable the subscription state internally,
        because the messages are received but are filtered.

        :param sub_event: The internal subscribe event.
        :type sub_event: SubscribeInternalEvent
        """
        tickers = sub_event.tickers
        conn = sub_event.conn_object
        sub_type = sub_event.sub_type
        self.tickers.enable(tickers, sub_type, conn.id)

    def _handle_unsubscribe(self, unsub_event):
        """
        Handles the event of revoking a specific active subscription
        for a specific ticker. Also if no active subscriptions remain,
        the websocket client is closed.

        :param unsub_event: The ticker unsubscribe event.
        :type unsub_event: UnsubscribeEvent
        """
        ticker, sub_type, conn_id = unsub_event.ticker, unsub_event.sub_type, unsub_event.conn_id
        self.tickers.disable(ticker, sub_type, conn_id)
        self._is_no_subs_active()

    def _handle_get_snapshot(self, snapshot_event):
        """
        Requests an order book snapshot request from Bittrex.

        :param snapshot_event: The ticker snapshot event.
        :type snapshot_event: SnapshotEvent
        """
        conn, ticker = snapshot_event.conn_object, snapshot_event.ticker
        method = 'queryExchangeState'
        # Wait for the connection to start successfully and record N nounces of data
        while conn.state is False or self.tickers.get_nounces(ticker) < 5:
            sleep(0.1)
        else:
            try:
                logger.info('[Subscription][{}][{}]: Order book snapshot '
                            'requested.'.format(SUB_TYPE_ORDERBOOK, ticker))
                conn.corehub.server.invoke(method, ticker)
                self.tickers.set_snapshot_state(ticker, SNAPSHOT_SENT)
            except Exception as e:
                print(e)
                print('Failed to invoke snapshot query')
        while self.tickers.get_snapshot_state(ticker) is not SNAPSHOT_ON:
            sleep(0.5)

    def _is_first_run(self, tickers, sub_type):
        # Check if the websocket has been initiated already or if it's the first run.
        if not self.tickers.list:
            self.on_open()
            self._subscribe_first_run(tickers, sub_type)
        else:
            return False

    def _subscribe_first_run(self, tickers, sub_type, objects=None):
        if objects is None:
            objects = self._create_btrx_connection(tickers)
        for obj in objects:
            self.control_queue.put(ConnectEvent(obj[1]))
            self.control_queue.put(SubscribeEvent(obj[0], obj[1], sub_type))

    def _unsubscribe(self, tickers, sub_type):
        for ticker in tickers:
            event = UnsubscribeEvent(ticker, self.tickers, sub_type)
            self.control_queue.put(event)

    def _get_snapshot(self, tickers):
        for ticker_name in tickers:
            # ticker_object = self.tickers.list[ticker_name]
            conn_id = self.tickers.get_sub_type_conn_id(ticker_name, SUB_TYPE_ORDERBOOK)
            # Due to multithreading the connection might not be added to the connection list yet
            while True:
                try:
                    conn = self.connections[conn_id]
                except KeyError:
                    sleep(0.5)
                    conn_id = self.tickers.get_sub_type_conn_id(ticker_name, SUB_TYPE_ORDERBOOK)
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
                    snapshot_state = self.tickers.get_snapshot_state(ticker)
                    if snapshot_state in [SNAPSHOT_OFF, SNAPSHOT_SENT]:
                        self._init_backorder_queue(ticker, order_event)
                    elif snapshot_state == SNAPSHOT_RCVD:
                        if self._transfer_backorder_queue(ticker):
                            self.tickers.set_snapshot_state(ticker, SNAPSHOT_ON)
                    if self.tickers.get_snapshot_state(ticker) == SNAPSHOT_ON:
                        self._sync_order_book(ticker, order_event)
                        self.orderbook_callback.on_change(self.order_books[ticker])
                    self.order_queue.task_done()

    def _is_running(self, tickers, sub_type):
        # Check for existing connections
        if self.connections:
            # Check for already existing tickers and enable the subscription before opening a new connection.
            for ticker in tickers:
                if self.tickers.get_sub_state(ticker, sub_type) is SUB_STATE_ON:
                    logger.info('{} subscription is already enabled for {}. Ignoring...'.format(sub_type, ticker))
                else:
                    # Assign most suitable connection
                    events = self._assign_conn(ticker, sub_type)
                    for event in events:
                        self.control_queue.put(event)

    def _assign_conn(self, ticker, sub_type):
        while self.control_queue.unfinished_tasks > 0:
            sleep(0.2)
        conns = self.tickers.sort_by_callbacks()
        d = {}
        if sub_type == SUB_TYPE_TICKERUPDATE:
            # Check for connection with enabled 'CALLBACK_SUMMARY_DELTAS'
            for conn in conns.keys():
                if CALLBACK_SUMMARY_DELTAS in conns[conn]:
                    d.update({conns[conn]['{} count'.format(CALLBACK_EXCHANGE_DELTAS)]: conn})
            # and get the connection with the lowest number of tickers.
            if d:
                min_tickers = min(d.keys())
                conn_id = d[min_tickers]
                return [SubscribeInternalEvent(ticker, self.connections[conn_id], sub_type)]
            # No connection found with 'CALLBACK_SUMMARY_DELTAS'.
            # Get the connection with the lowest number of tickers.
            else:
                for conn in conns.keys():
                    d.update({conns[conn]['{} count'.format(CALLBACK_EXCHANGE_DELTAS)]: conn})
                min_tickers = min(d.keys())
                conn_id = d[min_tickers]
                return [SubscribeEvent(ticker, self.connections[conn_id], sub_type)]
        else:
            # If 'EXCHANGE_DELTAS' is enabled for the ticker
            # and the specific connection, we just need to find the
            # connection and enable the subscription state in order
            # to stop filtering the messages.
            for conn in conns.keys():
                try:
                    if ticker in conns[conn][CALLBACK_EXCHANGE_DELTAS]:
                        return [SubscribeInternalEvent(ticker, self.connections[conn], sub_type)]
                except KeyError:
                    break
            # If there is no active subscription for the ticker,
            # check if there is enough quota and add the subscription to
            # an existing connection.
            for conn in conns.keys():
                d.update({conns[conn]['{} count'.format(CALLBACK_EXCHANGE_DELTAS)]: conn})
            min_tickers = min(d.keys())
            if min_tickers < self.max_tickers_per_conn:
                conn_id = d[min_tickers]
                return [SubscribeEvent(ticker, self.connections[conn_id], sub_type)]
            # The existing connections are in full capacity, create a new connection and subscribe.
            else:
                obj = self._create_btrx_connection([ticker])[0]
                conn_event = ConnectEvent(obj[1])
                sub_event = SubscribeEvent(ticker, obj[1], sub_type)
                return [conn_event, sub_event]

    def _is_no_subs_active(self):
        # Close the websocket if no active connections remain.
        active_conns = self.tickers.sort_by_callbacks()
        if not active_conns:
            self.disconnect()
        else:
            # Check for non-active connections and close ONLY them.
            non_active = set(self.connections) - set(active_conns)
            if non_active:
                for conn in non_active:
                    logger.info('Connection {} has no active subscriptions. Closing it...'.format(conn))
                    conn_object = self.connections[conn]
                    disconnect_event = DisconnectEvent(conn_object)
                    self.control_queue.put(disconnect_event)

    # ==============
    # Public Methods
    # ==============

    # -----------------
    # Subscribe Methods
    # -----------------

    def subscribe_to_orderbook(self, tickers, book_depth=10):
        """
        Subscribe and maintain the live order book for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        :param book_depth: The desired depth of the order book to be maintained.
        :type book_depth: int
        """
        sub_type = SUB_TYPE_ORDERBOOK
        self._is_order_queue()
        if self._is_first_run(tickers, sub_type) is False:
            self._is_running(tickers, sub_type)
        self.tickers.set_book_depth(tickers, book_depth)

    def subscribe_to_orderbook_update(self, tickers):
        """
        Subscribe to order book updates for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """
        sub_type = SUB_TYPE_ORDERBOOKUPDATE
        if self._is_first_run(tickers, sub_type) is False:
            self._is_running(tickers, sub_type)

    def subscribe_to_trades(self, tickers):
        """
        Subscribe and receive tick data(executed trades) for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """
        sub_type = SUB_TYPE_TRADES
        if self._is_first_run(tickers, sub_type) is False:
            self._is_running(tickers, sub_type)

    def subscribe_to_ticker_update(self, tickers=None):
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

        :param tickers: A list of tickers you are interested in.
        :type tickers: [] or None
        """
        if tickers is None:
            tickers = [ALL_TICKERS]
        sub_type = SUB_TYPE_TICKERUPDATE
        if self._is_first_run(tickers, sub_type) is False:
            self._is_running(tickers, sub_type)

    # -------------------
    # Unsubscribe Methods
    # -------------------

    def unsubscribe_to_orderbook(self, tickers):
        """
        Unsubscribe from real time order for specific set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """
        sub_type = SUB_TYPE_ORDERBOOK
        self._unsubscribe(tickers, sub_type)

    def unsubscribe_to_orderbook_update(self, tickers):
        """
        Unsubscribe from order book updates for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """
        sub_type = SUB_TYPE_ORDERBOOKUPDATE
        self._unsubscribe(tickers, sub_type)

    def unsubscribe_to_trades(self, tickers):
        """
        Unsubscribe from receiving tick data(executed trades) for a set of ticker(s)

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """
        sub_type = SUB_TYPE_TRADES
        self._unsubscribe(tickers, sub_type)

    def unsubscribe_to_ticker_update(self, tickers=None):
        """
        Unsubscribe from receiving general data updates for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: [] or None
        """
        if tickers is None:
            tickers = [ALL_TICKERS]
        sub_type = SUB_TYPE_TICKERUPDATE
        self._unsubscribe(tickers, sub_type)

    # -------------
    # Other Methods
    # -------------

    def get_order_book(self, ticker=None):
        """
        Returns the most recently updated order book for the specific ticker.
        If no ticker is specified, returns a dictionary with the order books of
        all subscribed tickers.

        :param ticker: The specific ticker you want the order book for.
        :type ticker: str
        """
        if ticker is None:
            return self.order_books
        else:
            return self.order_books[ticker]

    def get_order_book_sync_state(self, tickers=None):
        """
        Returns the sync state of the order book for the specific ticker(s).
        If no ticker is specified, returns the state for all tickers.
        The sync states are:

            Not initiated = 0
            Invoked, not synced = 1
            Received, not synced, not processing = 2
            Received, synced, processing = 3

        :param tickers: The specific ticker(s) and it's order book sync state you are interested in.
        :type tickers: []
        """
        if tickers is not None:
            t = find_ticker_type(tickers)
        else:
            t = self.tickers.list.keys()
        states = {}
        for ticker in t:
            if self.tickers.get_sub_state(ticker, SUB_TYPE_ORDERBOOK) is True:
                state = self.tickers.get_snapshot_state(ticker)
                states[ticker] = state
        return states

    def disconnect(self):
        """
        Disconnects the connections and stops the websocket instance.
        """
        self.control_queue.put(DisconnectEvent())

    @staticmethod
    def enable_log(file_name=None):
        """
        Enables logging.
        :param file_name: The name of the log file, located in the same directory as the executing script.
        :type file_name: str
        """
        add_stream_logger(file_name=file_name)

    @staticmethod
    def disable_log():
        """
        Disables logging.
        """
        remove_stream_logger()

    def _create_btrx_connection(self, tickers):
        results = []

        def get_chunks(l, n):
            # Yield successive n-sized chunks from l.
            for i in range(0, len(l), n):
                yield l[i:i + n]

        ticker_gen = get_chunks(list(tickers), self.max_tickers_per_conn)
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
        # Detect if the message contains order book snapshots and manipulate them.
        if 'R' in msg and type(msg['R']) is not bool:
            if 'MarketName' in msg['R'] and msg['R']['MarketName'] is None:
                for ticker in self.tickers.list.values():
                    if ticker['OrderBook']['SnapshotState'] == SNAPSHOT_SENT:
                        msg['R']['MarketName'] = ticker['Name']
                        del msg['R']['Fills']
                        self.order_books[ticker['Name']] = msg['R']
                        self.tickers.set_snapshot_state(ticker['Name'], SNAPSHOT_RCVD)
                        break
                logger.info(
                    '[Subscription][{}][{}]: Order book snapshot received.'.format(SUB_TYPE_ORDERBOOK,
                                                                                   msg['R']['MarketName']))

    def _init_backorder_queue(self, ticker, msg):
        sub = self.tickers.list[ticker][SUB_TYPE_ORDERBOOK]
        if sub['InternalQueue'] is None:
            sub['InternalQueue'] = queue.Queue()
        sub['InternalQueue'].put(msg)
        self.tickers.increment_nounces(ticker)

    def _transfer_backorder_queue(self, ticker):
        sub = self.tickers.list[ticker][SUB_TYPE_ORDERBOOK]
        q = sub['InternalQueue']
        while True:
            try:
                e = q.get(False)
            except queue.Empty:
                sub['InternalQueue'] = None
                return True
            else:
                if self._sync_order_book(ticker, e):
                    self.tickers.set_snapshot_state(ticker, SNAPSHOT_ON)
                q.task_done()

    # ========================
    # Private Channels Methods
    # ========================

    def _on_debug(self, **kwargs):
        """
        Debug information, shows all data
        Don't edit unless you know what you are doing.
        Redirect full order book snapshots to on_message
        """
        if self._is_close_me():
            return
        self._is_orderbook_snapshot(kwargs)

    def _on_tick_update(self, msg):
        if self._is_close_me():
            return
        ticker = msg['MarketName']
        subs = self.tickers.get_ticker_subs(ticker)
        if self.tickers.get_sub_state(ticker, SUB_TYPE_ORDERBOOK) is True:
            self.order_queue.put(msg)
        if subs[SUB_TYPE_ORDERBOOKUPDATE]['Active'] is True:
            d = dict(self._create_base_layout(msg),
                     **{'bids': msg['Buys'],
                        'asks': msg['Sells']})
            self.orderbook_update.on_change(d)
        if subs[SUB_TYPE_TRADES]['Active'] is True:
            if msg['Fills']:
                d = dict(self._create_base_layout(msg),
                         **{'trades': msg['Fills']})
                self.trades.on_change(d)

    def _on_ticker_update(self, msg):
        """
        Invoking summary state updates for specific filter
        doesn't work right now. So we will filter them manually.
        """
        if self._is_close_me():
            return
        if 'Deltas' in msg:
            for update in msg['Deltas']:
                if self.tickers.get_sub_state(ALL_TICKERS, SUB_TYPE_TICKERUPDATE) is SUB_STATE_ON:
                    self.updateSummaryState.on_change(msg['Deltas'])
                else:
                    try:
                        ticker = update['MarketName']
                        subs = self.tickers.get_ticker_subs(ticker)
                    except KeyError:  # not in the subscription list
                        continue
                    else:
                        if subs['TickerUpdate']['Active']:
                            self.updateSummaryState.on_change(update)

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
        nounce_diff = order_data['Nounce'] - self.order_books[pair_name]['Nounce']
        if nounce_diff == 1:
            self.order_books[pair_name]['Nounce'] = order_data['Nounce']
            # Start syncing
            for side in [['Buys', True], ['Sells', False]]:
                made_change = False

                for item in order_data[side[0]]:
                    # TYPE 0: New order entries at matching price
                    # -> ADD to order book
                    if item['Type'] == 0:
                        self.order_books[pair_name][side[0]].append(
                            {
                                'Quantity': item['Quantity'],
                                'Rate': item['Rate']
                            })
                        made_change = True

                    # TYPE 1: Cancelled / filled order entries at matching price
                    # -> DELETE from the order book
                    elif item['Type'] == 1:
                        for i, existing_order in enumerate(
                                self.order_books[pair_name][side[0]]):
                            if existing_order['Rate'] == item['Rate']:
                                del self.order_books[pair_name][side[0]][i]
                                made_change = True
                                break

                    # TYPE 2: Changed order entries at matching price (partial fills, cancellations)
                    # -> EDIT the order book
                    elif item['Type'] == 2:
                        for existing_order in self.order_books[pair_name][side[0]]:
                            if existing_order['Rate'] == item['Rate']:
                                existing_order['Quantity'] = item['Quantity']
                                made_change = True
                                break

                if made_change:
                    # Sort by price, with respect to BUY(desc) or SELL(asc)
                    self.order_books[pair_name][side[0]] = sorted(
                        self.order_books[pair_name][side[0]],
                        key=lambda k: k['Rate'],
                        reverse=side[1])
                    # Put depth to 10
                    self.order_books[pair_name][side[0]] = \
                        self.order_books[pair_name][side[0]][
                        0:book_depth]
                    # Add nounce unix timestamp
                    self.order_books[pair_name]['timestamp'] = time()
            return True
        # The next nounce will trigger a sync.
        elif nounce_diff == 0:
            return True
        # The order book snapshot nounce is ahead. Discard this nounce.
        elif nounce_diff < 0:
            return False
        else:
            raise NotImplementedError("Implement nounce resync!")

    def _is_close_me(self):
        thread_name = current_thread().getName()
        conn_object = self._return_conn_by_thread_name(thread_name)
        if conn_object.close_me:
            try:
                conn_object.conn.close()
            except WebSocketConnectionClosedException:
                pass
            conn_object.deactivate()
            return True

    def _return_conn_by_thread_name(self, thread_name):
        for conn in self.connections:
            if self.connections[conn].thread_name == thread_name:
                return self.connections[conn]

    # ===============
    # Public Channels
    # ===============

    def on_open(self):
        # Called before initiating the first websocket connection
        # Use it when you want to add some opening logic.
        pass

    def on_close(self):
        # Called before closing the websocket instance.
        # Use it when you want to add any closing logic.
        # print('Bittrex websocket closed.')
        pass

    def on_error(self, error):
        # Error handler
        print(error)
        self.disconnect()

    def on_orderbook(self, msg):
        # The main channel of subscribe_to_orderbook().
        # print('[OrderBook]: {}'.format(msg['MarketName']))
        pass

    def on_orderbook_update(self, msg):
        # The main channel of subscribe_to_orderbook_update().
        # print('[OrderBookUpdate]: {}'.format(msg['ticker']))
        pass

    def on_trades(self, msg):
        # The main channel of subscribe_to_trades().
        # print('[Trades]: {}'.format(msg['ticker']))
        pass

    def on_ticker_update(self, msg):
        # The main channel of subscribe_to_ticker_update().
        # print('Just received ticker update for {}.'.format(msg['MarketName']))
        pass
