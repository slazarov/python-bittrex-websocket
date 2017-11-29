#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/auxiliary.py
# Stanislav Lazarov

from uuid import uuid4

INVALID_SUB = 'Subscription type is invalid or not implemented. ' \
              'Available options: OrderBook, OrderBookUpdate, Trades'
INVALID_SUB_CHANGE = 'Subscription change is invalid. Available options: True/False'


class Ticker(object):
    def __init__(self):
        self.list = {}
        self.sub_types = ['OrderBook', 'OrderBookUpdate', 'Trades', 'TickerUpdate']

    def _create_structure(self):
        d = \
            {
                self.sub_types[0]: dict(self._set_default_subscription(), **{'SnapshotStatus': None}),
                self.sub_types[1]: self._set_default_subscription(),
                self.sub_types[2]: self._set_default_subscription(),
                self.sub_types[3]: self._set_default_subscription()
            }
        return d

    @staticmethod
    def _set_default_subscription():
        d = {'Active': False, 'ConnectionID': None}
        return d

    def add(self, ticker):
        self.list[ticker] = self._create_structure()

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

    def get_sub_types(self):
        return self.sub_types


class BittrexConnection(object):
    def __init__(self, conn, corehub):
        self.conn = conn
        self.corehub = corehub
        self.id = uuid4().hex
        self.conn_state = False

    def activate(self):
        self.conn_state = True

    def deactivate(self):
        self.conn_state = False


class Event(object):
    """
    Event is base class providing an interface
    for all subsequent(inherited) events.
    """
    pass


class ConnectEvent(Event):
    def __init__(self, conn_obj):
        self.type = 'CONNECT'
        self.conn_obj = conn_obj


class SubscribeEvent(Event):
    """
    Handles the event of subscribing
    specific ticker(s) to specific channels.
    """

    def __init__(self, tickers, conn_object, sub_type):
        """
        Initialises the MarketEvent.
        """
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
