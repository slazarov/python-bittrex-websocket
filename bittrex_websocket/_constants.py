#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/_constants.py
# Stanislav Lazarov


class Constant(object):
    """
    Event is base class providing an interface
    for all subsequent(inherited) constants.
    """


class EventTypes(Constant):
    CONNECT = 'CONNECT'
    SUBSCRIBE = 'SUBSCRIBE'
    CLOSE = 'CLOSE'


class BittrexParameters(Constant):
    # Connection parameters
    URL = 'https://beta.bittrex.com/signalr'
    HUB = 'c2'
    # Callbacks
    MARKET_DELTA = 'uE'
    SUMMARY_DELTA = 'uS'
    SUMMARY_DELTA_LITE = 'uL'
    BALANCE_DELTA = 'uB'
    ORDER_DELTA = 'uO'


class BittrexMethods(Constant):
    # Public methods
    SUBSCRIBE_TO_EXCHANGE_DELTAS = 'SubscribeToExchangeDeltas'
    SUBSCRIBE_TO_SUMMARY_DELTAS = 'SubscribeToSummaryDeltas'
    SUBSCRIBE_TO_SUMMARY_LITE_DELTAS = 'SubscribeToSummaryLiteDeltas'
    QUERY_SUMMARY_STATE = 'QuerySummaryState'
    QUERY_EXCHANGE_STATE = 'QueryExchangeState'
    GET_AUTH_CONTENT = 'GetAuthContext'
    AUTHENTICATE = 'Authenticate'


class ErrorMessages(Constant):
    INVALID_TICKER_INPUT = 'Tickers must be submitted as a list.'
