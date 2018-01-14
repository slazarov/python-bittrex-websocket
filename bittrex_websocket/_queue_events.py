#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/_queue_events.py
# Stanislav Lazarov

from ._auxiliary import Ticker, find_ticker_type
from .constants import *


class Event(object):
    """
    Event is base class providing an interface
    for all subsequent(inherited) events.
    """


class ConnectEvent(Event):
    """
    Handles the event of creating a new connection.
    """

    def __init__(self, conn_object):
        self.type = 'CONNECT'
        self.conn_obj = conn_object


class DisconnectEvent(Event):
    """
    Handles the event of disconnecting connections.
    """

    def __init__(self, conn_object=None):
        self.type = 'DISCONNECT'
        if conn_object is not None:
            self.conn_object = [conn_object]
        else:
            self.conn_object = conn_object


class SubscribeEvent(Event):
    """
    Handles the event of subscribing
    specific ticker(s) to specific channels.

    TO BE IMPLEMENTED:
    Invoke 'SubscribeToExchangeDeltas' only if required.
    """

    def __init__(self, tickers, conn_object, sub_type):
        self.type = 'SUBSCRIBE'
        self.tickers = find_ticker_type(tickers)
        self.conn_object = conn_object
        self.server_callback = None
        self.server_callback_no_payload = None
        self.sub_type = sub_type
        if sub_type not in Ticker().get_sub_types():
            raise SystemError(INVALID_SUB)
        else:
            if sub_type == SUB_TYPE_TICKERUPDATE:
                self.server_callback_no_payload = [CALLBACK_SUMMARY_DELTAS]
            else:
                self.server_callback = [CALLBACK_EXCHANGE_DELTAS]


class SubscribeInternalEvent(Event):
    """
    If the ticker is already in the tickers list and it shares a subscription
    callback for the new subscription request, then we don't have to invoke
    a request to Bittrex but only enable the subscription state internally,
    because the messages are received but are filtered.
    """

    def __init__(self, tickers, conn_object, sub_type):
        self.type = 'SUBSCRIBE_INTERNAL'
        self.tickers = self._find_ticker_type(tickers)
        self.conn_object = conn_object
        self.sub_type = sub_type

    @staticmethod
    def _find_ticker_type(tickers):
        ticker_type = type(tickers)
        if ticker_type is list:
            return tickers
        elif ticker_type is str:
            tickers = [tickers]
            return tickers


class UnsubscribeEvent(Event):
    """
    There is no direct method to revoke a subscription apart from:
    1.) Closing the connection
    2.) Suppressing the messages
    """

    def __init__(self, ticker, tickers_list, sub_type, unsub_type=True):
        self.type = 'UNSUBSCRIBE'
        self.ticker = ticker
        self.sub_type = sub_type
        self.conn_id = self._get_conn_id(tickers_list)
        self.unsub_type = unsub_type

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

    def _get_conn_object(self, tickers_list, conn_list):
        conn_id = tickers_list.list[self.ticker][self.sub_type]['ConnectionID']
        return conn_list[conn_id]


class SnapshotEvent(Event):
    """
    Handles the event of invoking a snapshot request for a specific ticker.
    """

    def __init__(self, ticker, conn_object):
        self.type = 'SNAPSHOT'
        self.ticker = ticker
        self.conn_object = conn_object


class IsFirstRunEvent(Event):
    """
    Handles the event of checking if the websocket has been initiated already or if it's the first run.
    """

    def __init__(self, tickers, sub_type):
        self.type = 'IS_FIRST_RUN'
        self.tickers = tickers
        self.sub_type = sub_type


class IsRunningEvent(Event):
    """
    Handles the event of analysing existing connections
    and checking if they can be reused or a new has to be opened.
    """

    def __init__(self, tickers, sub_type):
        self.type = 'IS_RUNNING'
        self.tickers = tickers
        self.sub_type = sub_type


class ReconnectEvent(Event):

    def __init__(self, ticker, sub_type, book_depth=None):
        self.type = 'RECONNECT'
        self.tickers = ticker
        self.sub_type = sub_type
        self.book_depth = book_depth
