#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/websocket_client.py
# Stanislav Lazarov

from __future__ import print_function
from ._signalr import Connection
import logging
from ._logger import add_stream_logger, remove_stream_logger
from threading import Thread
from ._queue_events import *
from .constants import EventTypes, BittrexParameters, BittrexMethods, ErrorMessages, OtherConstants
from ._auxiliary import process_message, create_signature, BittrexConnection
from ._abc import WebSocket

try:
    from cfscrape import create_scraper as Session
except ImportError:
    from requests import Session
from time import sleep

try:
    # import Queue as queue
    from Queue import Queue
except ImportError:
    from queue import Queue
from events import Events
from ._exceptions import *

logger = logging.getLogger(__name__)


class BittrexSocket(WebSocket):

    def __init__(self, url=None):
        self.control_queue = None
        self.invokes = []
        self.tickers = None
        self.connection = None
        self.threads = []
        self.credentials = None
        self._on_public_callback = None
        self._on_private_callback = None
        self.url = BittrexParameters.URL if url is None else url
        self._assign_callbacks()
        self._start_main_thread()

    def _assign_callbacks(self):
        self._on_public_callback = Events()
        self._on_public_callback.on_change += self.on_public
        self._on_private_callback = Events()
        self._on_private_callback.on_change += self.on_private

    def _start_main_thread(self):
        self.control_queue = Queue()
        self.control_queue.put(ConnectEvent())
        thread = Thread(target=self.control_queue_handler, name='ControlQueueThread')
        thread.daemon = True
        self.threads.append(thread)
        thread.start()

    def control_queue_handler(self):
        while True:
            event = self.control_queue.get()
            if event is not None:
                if event.type == EventTypes.CONNECT:
                    self._handle_connect()
                elif event.type == EventTypes.SUBSCRIBE:
                    self._handle_subscribe(event.invoke, event.payload)
                elif event.type == EventTypes.RECONNECT:
                    self._handle_reconnect(event.error_message)
                elif event.type == EventTypes.CLOSE:
                    self.connection.conn.close()
                    break
                self.control_queue.task_done()

    def _handle_connect(self):
        connection = Connection(self.url, Session())
        hub = connection.register_hub(BittrexParameters.HUB)
        connection.received += self._on_debug
        connection.error += self.on_error
        hub.client.on(BittrexParameters.MARKET_DELTA, self._on_public)
        hub.client.on(BittrexParameters.SUMMARY_DELTA, self._on_public)
        hub.client.on(BittrexParameters.SUMMARY_DELTA_LITE, self._on_public)
        hub.client.on(BittrexParameters.BALANCE_DELTA, self._on_private)
        hub.client.on(BittrexParameters.ORDER_DELTA, self._on_private)
        self.connection = BittrexConnection(connection, hub)
        thread = Thread(target=self._connection_handler, name='SocketConnectionThread')
        thread.daemon = True
        self.threads.append(thread)
        thread.start()

    def _handle_reconnect(self, error_message):
        if error_message is not None:
            logger.error('{}.'.format(error_message))
        logger.error('Initiating reconnection procedure')
        events = []
        for item in self.invokes:
            event = SubscribeEvent(item['invoke'], [item['ticker']])
            events.append(event)
        # Reset previous connection
        self.invokes, self.connection = [], None
        # Restart
        self.control_queue.put(ConnectEvent())
        for event in events:
            self.control_queue.put(event)

    def _connection_handler(self):
        if str(type(Session())) == OtherConstants.CF_SESSION_TYPE:
            logger.info('Establishing connection to Bittrex through {}.'.format(self.url))
            logger.info('cfscrape detected, using it to bypass Cloudflare.')
        else:
            logger.info('Establishing connection to Bittrex through {}.'.format(self.url))
        try:
            e = self.connection.conn.start()
            if e.code == 1000:
                logger.info('Bittrex connection successfully closed.')
            elif e.code == 1006:
                event = ReconnectEvent(e.message)
                self.control_queue.put(event)
            elif e.code == -1:
                logger.error(
                    'Undocumented error message received with code -1 and payload: {}. '
                    'Report to https://github.com/slazarov/python-bittrex-websocket'.format(e.message))
                event = ReconnectEvent(None)
                self.control_queue.put(event)
        except Exception as e:
            print(e)

    def _handle_subscribe(self, invoke, payload):
        while self.connection.conn.started is False:
            sleep(1)
        else:
            if invoke in [BittrexMethods.SUBSCRIBE_TO_EXCHANGE_DELTAS, BittrexMethods.QUERY_EXCHANGE_STATE]:
                for ticker in payload[0]:
                    self.invokes.append({'invoke': invoke, 'ticker': ticker})
                    self.connection.corehub.server.invoke(invoke, ticker)
                    logger.info('Successfully subscribed to [{}] for [{}].'.format(invoke, ticker))
            elif invoke == BittrexMethods.GET_AUTH_CONTENT:
                self.connection.corehub.server.invoke(invoke, payload[0])
                self.invokes.append({'invoke': invoke, 'ticker': payload[0]})
                logger.info('Retrieving authentication challenge.')
            elif invoke == BittrexMethods.AUTHENTICATE:
                self.connection.corehub.server.invoke(invoke, payload[0], payload[1])
                logger.info('Challenge retrieved. Sending authentication. Awaiting messages...')
                # No need to append invoke list, because AUTHENTICATE is called from successful GET_AUTH_CONTENT.
            else:
                self.invokes.append({'invoke': invoke, 'ticker': None})
                self.connection.corehub.server.invoke(invoke)
                logger.info('Successfully invoked [{}].'.format(invoke))

    # ==============
    # Public Methods
    # ==============

    def subscribe_to_exchange_deltas(self, tickers):
        if type(tickers) is list:
            invoke = BittrexMethods.SUBSCRIBE_TO_EXCHANGE_DELTAS
            event = SubscribeEvent(invoke, tickers)
            self.control_queue.put(event)
        else:
            raise TypeError(ErrorMessages.INVALID_TICKER_INPUT)

    def subscribe_to_summary_deltas(self):
        invoke = BittrexMethods.SUBSCRIBE_TO_SUMMARY_DELTAS
        event = SubscribeEvent(invoke, None)
        self.control_queue.put(event)

    def subscribe_to_summary_lite_deltas(self):
        invoke = BittrexMethods.SUBSCRIBE_TO_SUMMARY_LITE_DELTAS
        event = SubscribeEvent(invoke, None)
        self.control_queue.put(event)

    def query_summary_state(self):
        invoke = BittrexMethods.QUERY_SUMMARY_STATE
        event = SubscribeEvent(invoke, None)
        self.control_queue.put(event)

    def query_exchange_state(self, tickers):
        if type(tickers) is list:
            invoke = BittrexMethods.QUERY_EXCHANGE_STATE
            event = SubscribeEvent(invoke, tickers)
            self.control_queue.put(event)
        else:
            raise TypeError(ErrorMessages.INVALID_TICKER_INPUT)

    def authenticate(self, api_key, api_secret):
        self.credentials = {'api_key': api_key, 'api_secret': api_secret}
        event = SubscribeEvent(BittrexMethods.GET_AUTH_CONTENT, api_key)
        self.control_queue.put(event)

    def disconnect(self):
        self.control_queue.put(CloseEvent())

    # =======================
    # Private Channel Methods
    # =======================

    def _on_public(self, args):
        msg = process_message(args)
        if 'D' in msg:
            if len(msg['D'][0]) > 3:
                msg['invoke_type'] = BittrexMethods.SUBSCRIBE_TO_SUMMARY_DELTAS
            else:
                msg['invoke_type'] = BittrexMethods.SUBSCRIBE_TO_SUMMARY_LITE_DELTAS
        else:
            msg['invoke_type'] = BittrexMethods.SUBSCRIBE_TO_EXCHANGE_DELTAS
        self._on_public_callback.on_change(msg)

    def _on_private(self, args):
        self._on_private_callback.on_change(process_message(args))

    def _on_debug(self, **kwargs):
        # `QueryExchangeState`, `QuerySummaryState` and `GetAuthContext` are received in the debug channel.
        self._is_query_invoke(kwargs)

    def _is_query_invoke(self, kwargs):
        if 'R' in kwargs and type(kwargs['R']) is not bool:
            invoke = self.invokes[int(kwargs['I'])]['invoke']
            if invoke == BittrexMethods.GET_AUTH_CONTENT:
                signature = create_signature(self.credentials['api_secret'], kwargs['R'])
                event = SubscribeEvent(BittrexMethods.AUTHENTICATE, self.credentials['api_key'], signature)
                self.control_queue.put(event)
            else:
                msg = process_message(kwargs['R'])
                if msg is not None:
                    msg['invoke_type'] = invoke
                    self._on_public_callback.on_change(msg)

    # ======================
    # Public Channel Methods
    # ======================

    def on_public(self, msg):
        pass

    def on_private(self, msg):
        pass

    def on_error(self, args):
        logger.error(args)

    # =============
    # Other Methods
    # =============

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
