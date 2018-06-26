#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/constants.py
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
    RECONNECT = 'RECONNECT'


class BittrexParameters(Constant):
    # Connection parameters
    URL = 'https://socket.bittrex.com/signalr'
    HUB = 'c2'
    # Callbacks
    MARKET_DELTA = 'uE'
    SUMMARY_DELTA = 'uS'
    SUMMARY_DELTA_LITE = 'uL'
    BALANCE_DELTA = 'uB'
    ORDER_DELTA = 'uO'
    # Retry
    CONNECTION_TIMEOUT = 10
    RETRY_TIMEOUT = 5
    MAX_RETRIES = None


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
    UNHANDLED_EXCEPTION = '\nUnhandled {}.' \
                          '\nAuto-reconnection is disabled for unhandled exceptions.' \
                          '\nReport to https://github.com/slazarov/python-bittrex-websocket.'
    CONNECTION_TIMEOUTED = 'Connection timeout after {} seconds. Sending a reconnection signal.'


class InfoMessages(Constant):
    SUCCESSFUL_DISCONNECT = 'Bittrex connection successfully closed.'
    RECONNECTION_COUNT_FINITE = 'Previous reconnection failed. Retrying in {} seconds. Reconnection attempt {} out of {}.'
    RECONNECTION_COUNT_INFINITE = 'Previous reconnection failed. Retrying in {} seconds. Reconnection attempt {}.'


class OtherConstants(Constant):
    CF_SESSION_TYPE = '<class \'cfscrape.CloudflareScraper\'>'
    SOCKET_CONNECTION_THREAD = 'SocketConnectionThread'
    SIGNALR_LISTENER_THREAD = 'SignalRListenerThread'
