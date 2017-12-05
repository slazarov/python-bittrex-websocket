#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/auxiliary.py
# Stanislav Lazarov

import logging
from time import sleep
from uuid import uuid4

INVALID_SUB = 'Subscription type is invalid or not implemented. ' \
              'Available options: OrderBook, OrderBookUpdate, Trades'
INVALID_SUB_CHANGE = 'Subscription change is invalid. Available options: True/False'


class Ticker(object):
    SNAPSHOT_OFF = 0  # 'Not initiated'
    SNAPSHOT_SENT = 1  # Invoked, not processed
    SNAPSHOT_RCVD = 2  # Received, not processed
    SNAPSHOT_ON = 3  # Received, processed
    SUB_STATE_OFF = False
    SUB_STATE_ON = True
    SUB_TYPE_ORDERBOOK = 'OrderBook'
    SUB_TYPE_ORDERBOOKUPDATE = 'OrderBookUpdate'
    SUB_TYPE_TRADES = 'Trades'
    SUB_TYPE_TICKERUPDATE = 'TickerUpdate'

    def __init__(self):
        self.list = {}
        self.sub_types = [self.SUB_TYPE_ORDERBOOK,
                          self.SUB_TYPE_ORDERBOOKUPDATE,
                          self.SUB_TYPE_TRADES,
                          self.SUB_TYPE_TICKERUPDATE]

    def _create_structure(self):
        d = \
            {
                self.SUB_TYPE_ORDERBOOK: dict(self._set_default_subscription(),
                                              **{'SnapshotState': 0, 'OrderBookDepth': 10}),
                self.SUB_TYPE_ORDERBOOKUPDATE: self._set_default_subscription(),
                self.SUB_TYPE_TRADES: self._set_default_subscription(),
                self.SUB_TYPE_TICKERUPDATE: self._set_default_subscription(),
                'Name': None
            }
        return d

    def _set_default_subscription(self):
        d = {'Active': self.SUB_STATE_OFF, 'ConnectionID': None}
        return d

    def enable(self, tickers, sub_type, conn_id):
        tickers_list = self._fix_type_error(tickers)
        for ticker in tickers_list:
            self._add(ticker)
            self._change_sub_state(ticker, sub_type, Ticker.SUB_STATE_ON)
            self._assign_conn_id(ticker, sub_type, conn_id)
            logging.debug('[Subscription][{}][{}]: Enabled.'.format(sub_type, ticker))

    def disable(self, tickers, sub_type, conn_id):
        tickers_list = self._fix_type_error(tickers)
        for ticker in tickers_list:
            self._change_sub_state(ticker, sub_type, Ticker.SUB_STATE_OFF)
            self._assign_conn_id(ticker, sub_type, None)
            logging.debug('[Subscription][{}][{}]: Disabled.'.format(sub_type, ticker))

    def _add(self, ticker):
        if ticker not in self.list:
            self.list[ticker] = self._create_structure()
            self.list[ticker]['Name'] = ticker

    def remove(self, ticker):
        try:
            del self.list[ticker]
        except KeyError:
            raise KeyError('No such ticker found in the list.')

    def _change_sub_state(self, ticker, sub_type, sub_state):
        """
        Changes the state of the specific subscription for the given ticker.

        :param ticker: Ticker name
        :type ticker: str
        :param sub_type: Subscription type; Options: OrderBook, OrderBookUpdate, Trades
        :type sub_type: string
        :param sub_state: Subscription state; Active == True, Inactive == False
        :type sub_state: bool
        """
        if sub_type not in self.sub_types:
            raise SystemError(INVALID_SUB)
        if type(sub_state) is not bool:
            raise SystemError(INVALID_SUB_CHANGE)
        self.list[ticker][sub_type]['Active'] = sub_state

    def get_sub_state(self, ticker, sub_type):
        if ticker in self.list:
            return self.list[ticker][sub_type]['Active']
        else:
            return False

    def get_ticker_subs(self, ticker):
        return self.list[ticker]

    def _assign_conn_id(self, ticker, sub_type, conn_id):
        """
        Assigns a connection id to the given ticker

        :param ticker: Ticker name
        :type ticker: str
        :param sub_type: The subscription type
        :type sub_type: str
        :param conn_id: ID of the connection
        :type conn_id: str
        """
        self.list[ticker][sub_type]['ConnectionID'] = conn_id

    def remove_conn_id(self, tickers, sub_type):
        if type(tickers) is not []:
            tickers = [tickers]
        for ticker in tickers:
            self.list[ticker][sub_type]['ConnectionID'] = None

    def set_book_depth(self, tickers, book_depth):
        tickers_list = self._fix_type_error(tickers)
        for ticker in tickers_list:
            timeout = 0
            while timeout < 40:
                while ticker not in self.list:
                    sleep(0.5)
                    timeout += 0.5
                else:
                    self.list[ticker]['OrderBook']['OrderBookDepth'] = book_depth
                    logging.debug(
                        '[Subscription][{}][{}]: Order book depth set to {}.'.format(self.SUB_TYPE_ORDERBOOK, ticker,
                                                                                     book_depth))
                    break
            else:
                logging.debug(
                    '[Subscription][{}][{}]: Failed to set order book depth to {}.'.format(self.SUB_TYPE_ORDERBOOK,
                                                                                           ticker,
                                                                                           book_depth))

    def set_snapshot_state(self, ticker, state):
        self.list[ticker]['OrderBook']['SnapshotState'] = state

    def get_snapshot_state(self, ticker):
        return self.list[ticker]['OrderBook']['SnapshotState']

    def empty_order_book_queue(self, ticker):
        self.list[ticker]['OrderBook']['Queue'] = []

    def get_sub_types(self):
        return self.sub_types

    def sort_by_callbacks(self):
        """
        Returns a dictionary with the following structure:
        {
            'ConnectionID':
                {
                    'CallbackType1': set('tickers'),
                    'CallbackType2': set('tickers'),
                    'Unique ticker count': Unique tickers in the connection:int,
                    'SubscribeToSummaryDeltas count': ticker count per specific callback:int,
                    'SubscribeToExchangeDeltas count': ticker count per specific callback
                }
        }
        """
        conns = {}
        cb_sum_delta = BittrexConnection.CALLBACK_SUMMARY_DELTAS
        cb_exch_delta = BittrexConnection.CALLBACK_EXCHANGE_DELTAS
        for ticker in self.list.values():
            for cb in ticker:
                if type(ticker[cb]) is dict:
                    if self.get_sub_state(ticker['Name'], cb) is self.SUB_STATE_ON:
                        conn_id = ticker[cb]['ConnectionID']
                        if cb is self.SUB_TYPE_TICKERUPDATE:
                            callback = cb_sum_delta
                        else:
                            callback = cb_exch_delta
                        try:
                            conns[conn_id][callback].add(ticker['Name'])
                        except KeyError:
                            # Create the set if it doesn't exist.
                            if conn_id not in conns:
                                struct = {conn_id: {callback: set()}}
                                conns.update(struct)
                            else:
                                struct = {callback: set()}
                                conns[conn_id].update(struct)
                            conns[conn_id][callback].add(ticker['Name'])

        # Count unique and per callback tickers in a connection
        for conn in conns.values():
            unique_tickers = set()
            for cb in conn.values():
                unique_tickers.update(cb)
            conn['Unique tickers count'] = len(unique_tickers)
            for cb in [cb_exch_delta, cb_sum_delta]:
                if cb in conn:
                    conn['{} count'.format(cb)] = len(conn[cb])
                else:
                    conn['{} count'.format(cb)] = 0
        return conns

    def get_sub_type_conn_id(self, ticker, sub_type):
        if ticker in self.list:
            return self.list[ticker][sub_type]['ConnectionID']
        else:
            return False

    @staticmethod
    def _fix_type_error(tickers):
        # Tickers should be [], even if there is a single ticker.
        if type(tickers) is not list:
            tickers = [tickers]
        return tickers


class BittrexConnection(object):
    CALLBACK_EXCHANGE_DELTAS = 'SubscribeToExchangeDeltas'
    CALLBACK_SUMMARY_DELTAS = 'SubscribeToSummaryDeltas'
    CALLBACK_STATE_OFF = False
    CALLBACK_STATE_ON = True

    def __init__(self, conn, corehub, max_tickers_per_conn=20):
        self.conn = conn
        self.corehub = corehub
        self.id = uuid4().hex
        self.state = False
        self.thread_name = None
        self.close_me = False
        self.ticker_count = 0
        self.max_tickers_per_conn = max_tickers_per_conn
        self.callbacks = self._create_structure()

    def activate(self):
        self.state = True

    def deactivate(self):
        self.state = False

    def close(self):
        self.close_me = True

    def assign_thread(self, thread_name):
        self.thread_name = thread_name

    def increment_ticker(self):
        self.ticker_count += 1

    def set_callback_state(self, callback, state):
        self.callbacks[callback] = state

    def _create_structure(self):
        d = {self.CALLBACK_EXCHANGE_DELTAS: False,
             self.CALLBACK_SUMMARY_DELTAS: False}
        return d


class Common(object):
    @staticmethod
    def find_ticker_type(tickers):
        ticker_type = type(tickers)
        if ticker_type is list:
            return tickers
        elif ticker_type is str:
            tickers = [tickers]
            return tickers
