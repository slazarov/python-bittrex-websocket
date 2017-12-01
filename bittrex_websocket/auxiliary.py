#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/auxiliary.py
# Stanislav Lazarov

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
        self.sub_types = ['OrderBook', 'OrderBookUpdate', 'Trades', 'TickerUpdate', 'Name']

    def _create_structure(self):
        d = \
            {
                self.SUB_TYPE_ORDERBOOK: dict(self._set_default_subscription(),
                                              **{'SnapshotState': 0, 'OrderBookDepth': 10}),
                self.SUB_TYPE_ORDERBOOKUPDATE: self._set_default_subscription(),
                self.SUB_TYPE_TRADES: self._set_default_subscription(),
                self.SUB_TYPE_TICKERUPDATE: self._set_default_subscription(),
                self.sub_types[4]: None
            }
        return d

    @staticmethod
    def _set_default_subscription():
        d = {'Active': False, 'ConnectionID': None}
        return d

    def add(self, ticker):
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
        :param sub_type: Subscription type; Options: OrderBook, OrderBookUpdate, Trades
        :type sub_type: string
        :param sub_state: Subscription state; Active == True, Inactive == False
        :type sub_state: bool
        """
        if sub_type not in ['OrderBook', 'OrderBookUpdate', 'Trades', 'TickerUpdate']:
            raise SystemError(INVALID_SUB)
        if type(sub_state) is not bool:
            raise SystemError(INVALID_SUB_CHANGE)
        self.list[ticker][sub_type]['Active'] = sub_state

    def get_ticker_subs(self, ticker):
        return self.list[ticker]

    def assign_conn_id(self, tickers, sub_type, conn_id):
        """
        Assigns a connection id to the given ticker(s)

        :param tickers: Tickers name
        :type tickers: []
        :param sub_type: The subscription type
        :type sub_type: str
        :param conn_id: ID of the connection
        :type conn_id: str
        """
        for ticker in tickers:
            self.list[ticker][sub_type]['ConnectionID'] = conn_id

    def remove_conn_id(self, tickers, sub_type):
        if type(tickers) is not []:
            tickers = [tickers]
        for ticker in tickers:
            self.list[ticker][sub_type]['ConnectionID'] = None

    def set_book_depth(self, tickers, book_depth):
        for ticker in tickers:
            self.list[ticker]['OrderBook']['OrderBookDepth'] = book_depth

    def set_snapshot_state(self, ticker, state):
        self.list[ticker]['OrderBook']['SnapshotState'] = state

    def get_snapshot_state(self, ticker):
        return self.list[ticker]['OrderBook']['SnapshotState']

    def empty_order_book_queue(self, ticker):
        self.list[ticker]['OrderBook']['Queue'] = []

    def get_sub_types(self):
        return self.sub_types


class BittrexConnection(object):
    def __init__(self, conn, corehub):
        self.conn = conn
        self.corehub = corehub
        self.id = uuid4().hex
        self.state = False
        self.thread_name = None
        self.close_me = False
        self.ticker_count = 0

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


class Event(object):
    """
    Event is base class providing an interface
    for all subsequent(inherited) events.
    """
    pass


class ConnectEvent(Event):
    """
    Handles the event of creating a new connection.
    """

    def __init__(self, conn_object):
        self.type = 'CONNECT'
        self.conn_obj = conn_object


class DisconnectEvent(Event):
    """
    Handles the event of disconnecting the connections and stopping the websocket instance.
    """

    def __init__(self):
        self.type = 'DISCONNECT'


class SubscribeEvent(Event):
    """
    Handles the event of subscribing
    specific ticker(s) to specific channels.
    """

    def __init__(self, tickers, conn_object, sub_type):
        self.type = 'SUBSCRIBE'
        self.tickers = tickers
        self.conn_object = conn_object
        self.client_callback = None
        self.server_callback = None
        if sub_type not in Ticker().get_sub_types():
            raise SystemError(INVALID_SUB)
        else:
            self.server_callback = ['SubscribeToExchangeDeltas']
            # Doesnt' work
            # self.server_callback = ['SubscribeToSummaryDeltas']


class UnsubscribeEvent(Event):
    """
    There is no direct method to revoke a subscription apart from:
    1.) Closing the connection
    2.) Suppressing the messages
    """

    def __init__(self, ticker, tickers_list, sub_type):
        self.type = 'UNSUBSCRIBE'
        self.ticker = ticker
        self.sub_type = sub_type
        self.conn_id = self._get_conn_id(tickers_list)

    """
    In the future I plan to use the connection
    object and revoke the callback instead of suppressing it. 
    Leaving it for now.
    
    def __init__(self, ticker, tickers_list, conn_list, sub_type):
        self.type = 'SUBSCRIBE'
        self.ticker = ticker
        self.sub_type = sub_type
        self.conn_object = self._get_conn_object(tickers_list, conn_list)
    """

    def _get_conn_id(self, tickers_list):
        conn_id = tickers_list.list[self.ticker][self.sub_type]['ConnectionID']
        return conn_id

    def _get_conn_object(self, tickers_list: Ticker, conn_list):
        conn_id = tickers_list.list[self.ticker][self.sub_type]['ConnectionID']
        return conn_list[conn_id]


class SnapshotEvent(Event):
    """
    Handles the event of invoking a snapshot request for a specific ticker
    """

    def __init__(self, ticker, conn_object):
        self.type = 'SNAPSHOT'
        self.ticker = ticker
        self.conn_object = conn_object
