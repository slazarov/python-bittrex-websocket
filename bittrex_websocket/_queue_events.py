#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/_queue_events.py
# Stanislav Lazarov

from .constants import EventTypes


class Event(object):
    """
    Event is base class providing an interface
    for all subsequent(inherited) events.
    """


class ConnectEvent(Event):
    """
    Handles the event of creating a new connection.
    """

    def __init__(self):
        self.type = EventTypes.CONNECT


class SubscribeEvent(Event):
    """
    Handles the event of subscribing specific ticker(s) to specific channels.
    """

    def __init__(self, invoke, *payload):
        self.type = EventTypes.SUBSCRIBE
        self.invoke = invoke
        self.payload = payload


class ReconnectEvent(Event):
    """
    Handles the event reconnection.
    """

    def __init__(self, error_message):
        self.type = EventTypes.RECONNECT
        self.error_message = error_message


class CloseEvent(Event):
    """
    Handles the event of closing the socket.
    """

    def __init__(self):
        self.type = EventTypes.CLOSE


class ConfirmEvent(Event):
    """
    Handles the event of confirm the order book.
    """

    def __init__(self, ticker, order_nounces):
        self.type = EventTypes.CONFIRM_OB
        self.ticker = ticker
        self.order_nounces = order_nounces


class SyncEvent(Event):
    """
    Handles the event of syncing the order book.
    """

    def __init__(self, ticker, order_nounces):
        self.type = EventTypes.SYNC_OB
        self.ticker = ticker
        self.order_nounces = order_nounces
