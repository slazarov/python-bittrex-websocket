#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/_auxiliary.py
# Stanislav Lazarov

import logging
from time import sleep
from uuid import uuid4

from .constants import *

# =========================
# Classless/General Methods
# =========================

logger = logging.getLogger(__name__)


def find_ticker_type(tickers):
    ticker_type = type(tickers)
    if ticker_type is list:
        return tickers
    elif ticker_type is str:
        tickers = [tickers]
        return tickers


class Ticker(object):
    def __init__(self):
        self.list = {}
        self.sub_types = [SUB_TYPE_ORDERBOOK,
                          SUB_TYPE_ORDERBOOKUPDATE,
                          SUB_TYPE_TRADES,
                          SUB_TYPE_TICKERUPDATE]

    def _create_structure(self):
        d = \
            {
                SUB_TYPE_ORDERBOOK: dict(self._set_default_subscription(),
                                         **{'SnapshotState': 0,
                                            'OrderBookDepth': 10,
                                            'NouncesRcvd': 0,
                                            'InternalQueue': None}),
                SUB_TYPE_ORDERBOOKUPDATE: self._set_default_subscription(),
                SUB_TYPE_TRADES: self._set_default_subscription(),
                SUB_TYPE_TICKERUPDATE: self._set_default_subscription(),
                'Name': None
            }
        return d

    @staticmethod
    def _set_default_subscription():
        d = {'Active': SUB_STATE_OFF, 'ConnectionID': None}
        return d

    def enable(self, tickers, sub_type, conn_id):
        tickers_list = find_ticker_type(tickers)
        for ticker in tickers_list:
            self._add(ticker)
            self.change_sub_state(ticker, sub_type, SUB_STATE_ON)
            self._assign_conn_id(ticker, sub_type, conn_id)
            logger.info('[Subscription][{}][{}]: Enabled.'.format(sub_type, ticker))

    def disable(self, tickers, sub_type):
        tickers_list = find_ticker_type(tickers)
        for ticker in tickers_list:
            self.change_sub_state(ticker, sub_type, SUB_STATE_OFF)
            self._assign_conn_id(ticker, sub_type, None)
            if sub_type == SUB_TYPE_ORDERBOOK:
                self.reset_snapshot(ticker)
            logger.info('[Subscription][{}][{}]: Disabled.'.format(sub_type, ticker))

    def _add(self, ticker):
        if ticker not in self.list:
            self.list[ticker] = self._create_structure()
            self.list[ticker]['Name'] = ticker

    def remove(self, ticker):
        try:
            del self.list[ticker]
        except KeyError:
            raise KeyError('No such ticker found in the list.')

    def change_sub_state(self, ticker, sub_type, sub_state):
        """
        Changes the state of the specific subscription for the given ticker.

        :param ticker: Ticker name
        :type ticker: str
        :param sub_type: SUB_TYPE_ORDERBOOK; SUB_TYPE_ORDERBOOKUPDATE; SUB_TYPE_TRADES; SUB_TYPE_TICKERUPDATE
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
        """
        Check if the subscription for the specific ticker is in/active.

        :param ticker: Ticker name
        :type ticker: str
        :param sub_type: SUB_TYPE_ORDERBOOK; SUB_TYPE_ORDERBOOKUPDATE; SUB_TYPE_TRADES; SUB_TYPE_TICKERUPDATE
        :type sub_type: string
        :return: True(==SUB_STATE_ON) for Active; False(==SUB_STATE_OFF) for Inactive
        :rtype: bool
        """

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
        :type conn_id: str or None
        """
        self.list[ticker][sub_type]['ConnectionID'] = conn_id

    def remove_conn_id(self, tickers, sub_type):
        if type(tickers) is not []:
            tickers = [tickers]
        for ticker in tickers:
            self.list[ticker][sub_type]['ConnectionID'] = None

    def set_book_depth(self, tickers, book_depth):
        tickers_list = find_ticker_type(tickers)
        for ticker in tickers_list:
            timeout = 0
            while timeout < 40:
                while ticker not in self.list:
                    sleep(0.5)
                    timeout += 0.5
                else:
                    self.list[ticker][SUB_TYPE_ORDERBOOK]['OrderBookDepth'] = book_depth
                    logger.info(
                        '[Subscription][{}][{}]: Order book depth set to {}.'.format(SUB_TYPE_ORDERBOOK, ticker,
                                                                                     book_depth))
                    break
            else:
                logger.info(
                    '[Subscription][{}][{}]: Failed to set order book depth to {}.'.format(SUB_TYPE_ORDERBOOK,
                                                                                           ticker,
                                                                                           book_depth))

    def get_book_depth(self, ticker):
        return self.list[ticker][SUB_TYPE_ORDERBOOK]['OrderBookDepth']

    def set_snapshot_state(self, ticker, state):
        self.list[ticker]['OrderBook']['SnapshotState'] = state

    def get_snapshot_state(self, ticker):
        return self.list[ticker]['OrderBook']['SnapshotState']

    def empty_order_book_queue(self, ticker):
        self.list[ticker]['OrderBook']['Queue'] = []

    def get_sub_types(self):
        return self.sub_types

    # Still unused, putting it in case of future demand
    def get_conn_id(self, ticker, sub_type):
        return self.list[ticker][sub_type]['ConnectionID']

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
        cb_sum_delta = CALLBACK_SUMMARY_DELTAS
        cb_exch_delta = CALLBACK_EXCHANGE_DELTAS
        for ticker in self.list.values():
            for cb in ticker:
                if type(ticker[cb]) is dict:
                    if self.get_sub_state(ticker['Name'], cb) is SUB_STATE_ON:
                        conn_id = ticker[cb]['ConnectionID']
                        if cb is SUB_TYPE_TICKERUPDATE:
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

    def get_subscription_events(self, conn_id):
        cmds = []
        for ticker in self.list.keys():
            for sub_type in self.list[ticker]:
                try:
                    sub_state = self.get_sub_state(ticker, sub_type)
                except TypeError:
                    # The dict contains 'Name' as well as subscription types, skip if 'Name'
                    continue
                else:
                    if sub_state is SUB_STATE_ON:
                        if self.get_sub_state(ticker, sub_type) is SUB_STATE_ON:
                            if self.get_conn_id(ticker, sub_type) == conn_id:
                                if sub_type is SUB_TYPE_ORDERBOOK:
                                    cmds.append({
                                        'sub_type': SUB_TYPE_ORDERBOOK,
                                        'ticker': ticker,
                                        'depth': self.get_book_depth(ticker)
                                    })
                                else:
                                    cmds.append({
                                        'sub_type': sub_type,
                                        'ticker': ticker,
                                    })
        return cmds

    def sort_by_sub_state(self):
        d = {}
        for ticker in self.list.keys():
            for sub_type in self.sub_types:
                state = self.list[ticker][sub_type]['Active']
                item = {state: {ticker: self.list[ticker][sub_type]}}
                d.update(item)
        return d

    def sort_by_conn_id(self, conn_id):
        d = {}
        for ticker in self.list.keys():
            for sub_type in self.sub_types:
                if self.get_conn_id(ticker, sub_type) == conn_id:
                    if sub_type in d:
                        d[sub_type][ticker] = self.list[ticker][sub_type]
                    else:
                        d.update({sub_type: {ticker: self.list[ticker][sub_type]}})
        return d

    def sort_by_sub_types(self):
        # TO BE IMPLEMENTED WHEN THE OCCASION RISES
        pass

    def get_sub_type_conn_id(self, ticker, sub_type):
        if ticker in self.list:
            return self.list[ticker][sub_type]['ConnectionID']
        else:
            return False

    def increment_nounces(self, ticker):
        self.list[ticker][SUB_TYPE_ORDERBOOK]['NouncesRcvd'] += 1

    def get_nounces(self, ticker):
        return self.list[ticker][SUB_TYPE_ORDERBOOK]['NouncesRcvd']

    def reset_snapshot(self, ticker):
        self.list[ticker][SUB_TYPE_ORDERBOOK]['NouncesRcvd'] = 0
        self.list[ticker][SUB_TYPE_ORDERBOOK]['SnapshotState'] = 0
        self.list[ticker][SUB_TYPE_ORDERBOOK]['InternalQueue'] = None
        logger.info(
            '[Subscription][{}][{}]: Snapshot nounce, state and internal queue are reset.'.format(SUB_TYPE_ORDERBOOK,
                                                                                                  ticker))


class BittrexConnection(object):
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

    @staticmethod
    def _create_structure():
        d = {CALLBACK_EXCHANGE_DELTAS: CALLBACK_STATE_OFF,
             CALLBACK_SUMMARY_DELTAS: CALLBACK_STATE_OFF}
        return d
