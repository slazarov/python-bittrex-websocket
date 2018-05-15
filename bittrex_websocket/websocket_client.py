#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/websocket_client.py
# Stanislav Lazarov

from ._signalr import Connection
import logging
from ._logger import add_stream_logger, remove_stream_logger
from threading import Thread
from ._queue_events import *
from .constants import EventTypes, BittrexParameters, BittrexMethods, ErrorMessages, InfoMessages, OtherConstants
from ._auxiliary import process_message, create_signature, clear_queue, BittrexConnection
from ._abc import WebSocket

try:
    from cfscrape import create_scraper as Session
except ImportError:
    from requests import Session
from time import sleep, time

try:
    from Queue import Queue
except ImportError:
    from queue import Queue
from events import Events
from ._exceptions import *

logger = logging.getLogger(__name__)


class BittrexSocket(WebSocket):

    def __init__(self, url=None, retry_timeout=None, max_retries=None):
        """
        :param url: Custom connection url
        :type url: str or None
        :param retry_timeout: Seconds between connection retries (DEFAULT = 10)
        :type retry_timeout: int
        :param max_retries: Maximum retries before quiting
        :type max_retries: int
        """
        self.url = BittrexParameters.URL if url is None else url
        self.retry_timeout = BittrexParameters.RETRY_TIMEOUT if retry_timeout is None else retry_timeout
        self.max_retries = BittrexParameters.MAX_RETRIES if max_retries is None else max_retries
        self.retry_fail = 0
        self.last_retry = None
        self.control_queue = None
        self.invokes = []
        self.tickers = None
        self.connection = None
        self.threads = []
        self.credentials = None
        self._on_public_callback = None
        self._on_private_callback = None
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
                    self._handle_subscribe(event)
                elif event.type == EventTypes.RECONNECT:
                    self._handle_reconnect(event.error_message)
                elif event.type == EventTypes.CLOSE:
                    self.connection.conn.close()
                    break
                self.control_queue.task_done()

    def _handle_connect(self):
        if self.last_retry is not None and time() - self.last_retry >= 60:
            logger.debug('Last reconnection was more than 60 seconds ago. Resetting retry counter.')
            self.retry_fail = 0
        else:
            self.last_retry = time()
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
        thread = Thread(target=self._connection_handler, name=OtherConstants.SOCKET_CONNECTION_THREAD)
        thread.daemon = True
        self.threads.append(thread)
        thread.start()

    def _handle_reconnect(self, error_message):
        if error_message is not None:
            logger.error('{}.'.format(error_message))
        logger.debug('Initiating reconnection procedure')
        for i, thread in enumerate(self.threads):
            if thread.name == OtherConstants.SOCKET_CONNECTION_THREAD:
                thread.join()
                self.threads.pop(i)
        events = []
        for item in self.invokes:
            event = SubscribeEvent(item['invoke'], [item['ticker']])
            events.append(event)
        # Reset previous connection
        self.invokes, self.connection = [], None
        # Restart
        if 0 <= self.retry_fail <= self.retry_fail + 1 if self.max_retries is None else self.max_retries:
            # Don't delay the first reconnection.
            if BittrexParameters.MAX_RETRIES is not None:
                logger.debug(InfoMessages.RECONNECTION_COUNT_FINITE.format(self.retry_timeout, self.retry_fail + 1,
                                                                           BittrexParameters.MAX_RETRIES))
            else:
                logger.debug(InfoMessages.RECONNECTION_COUNT_INFINITE.format(self.retry_timeout, self.retry_fail + 1))
            if self.retry_fail > 0:
                sleep(self.retry_timeout)
            self.retry_fail += 1
            self.control_queue.put(ConnectEvent())
            for event in events:
                self.control_queue.put(event)
        else:
            logger.debug('Maximum reconnection retries reached. Closing the socket instance.')
            self.control_queue.put(CloseEvent())

    def _connection_handler(self):
        def _get_err_msg(exception):
            error_message = 'Exception = {}, Message = <{}>'.format(type(exception), exception)
            return error_message

        if str(type(Session())) == OtherConstants.CF_SESSION_TYPE:
            logger.info('Establishing connection to Bittrex through {}.'.format(self.url))
            logger.info('cfscrape detected, will try to bypass Cloudflare if enabled.')
        else:
            logger.info('Establishing connection to Bittrex through {}.'.format(self.url))
        try:
            self.connection.conn.start()
        except WebSocketConnectionClosedByUser:
            logger.info(InfoMessages.SUCCESSFUL_DISCONNECT)
        except WebSocketConnectionClosedException as e:
            self.control_queue.put(ReconnectEvent(_get_err_msg(e)))
        except TimeoutError as e:
            self.control_queue.put(ReconnectEvent(_get_err_msg(e)))
        except ConnectionError:
            pass
            # Commenting it for the time being. It should be handled in _handle_subscribe.
            # event = ReconnectEvent(None)
            # self.control_queue.put(event)
        except Exception as e:
            logger.error(ErrorMessages.UNHANDLED_EXCEPTION.format(_get_err_msg(e)))
            self.disconnect()
            # event = ReconnectEvent(None)
            # self.control_queue.put(event)

    def _handle_subscribe(self, sub_event):
        invoke, payload = sub_event.invoke, sub_event.payload
        i = 0
        while self.connection.conn.started is False:
            sleep(1)
            i += 1
            if i == BittrexParameters.CONNECTION_TIMEOUT:
                logger.error(ErrorMessages.CONNECTION_TIMEOUTED.format(BittrexParameters.CONNECTION_TIMEOUT))
                self.invokes.append({'invoke': invoke, 'ticker': payload[0][0]})
                for event in self.control_queue.queue:
                    self.invokes.append({'invoke': event.invoke, 'ticker': event.payload[0][0]})
                clear_queue(self.control_queue)
                self.control_queue.put(ReconnectEvent(None))
                return
        else:
            if invoke in [BittrexMethods.SUBSCRIBE_TO_EXCHANGE_DELTAS, BittrexMethods.QUERY_EXCHANGE_STATE]:
                for ticker in payload[0]:
                    self.invokes.append({'invoke': invoke, 'ticker': ticker})
                    self.connection.corehub.server.invoke(invoke, ticker)
                    logger.info('Successfully subscribed to [{}] for [{}].'.format(invoke, ticker))
            elif invoke == BittrexMethods.GET_AUTH_CONTENT:
                # The reconnection procedures puts the key in a tuple and it fails, hence the little quick fix.
                key = payload[0][0] if type(payload[0]) == list else payload[0]
                self.connection.corehub.server.invoke(invoke, key)
                self.invokes.append({'invoke': invoke, 'ticker': key})
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
        try:
            [thread.join() for thread in reversed(self.threads)]
        except RuntimeError:
            # If disconnect is called within, the ControlQueueThread will try to join itself
            # RuntimeError: cannot join current thread
            pass

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
        if self.connection.conn.started is False:
            self.connection.conn.started = True
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
