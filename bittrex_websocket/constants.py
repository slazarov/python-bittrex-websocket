#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/constants.py
# Stanislav Lazarov

INVALID_SUB = 'Subscription type is invalid or not implemented. ' \
              'Available options: OrderBook, OrderBookUpdate, Trades'
INVALID_SUB_CHANGE = 'Subscription change is invalid. Available options: True/False'
SNAPSHOT_OFF = -1  # 'Not initiated'
SNAPSHOT_QUEUED = 0  # Sent to queue for processing
SNAPSHOT_SENT = 1  # Invoked, not processed
SNAPSHOT_RCVD = 2  # Received, not processed
SNAPSHOT_ON = 3  # Received, processed
SUB_STATE_OFF = False
SUB_STATE_ON = True
SUB_STATE_DISCONNECTED = None
SUB_TYPE_ORDERBOOK = 'OrderBook'
SUB_TYPE_ORDERBOOKUPDATE = 'OrderBookUpdate'
SUB_TYPE_TRADES = 'Trades'
SUB_TYPE_TICKERUPDATE = 'TickerUpdate'
SUB_TYPE_ORDERBOOK_DEPTH = 'OrderBookDepth'
CALLBACK_EXCHANGE_DELTAS = 'SubscribeToExchangeDeltas'
CALLBACK_SUMMARY_DELTAS = 'SubscribeToSummaryDeltas'
CALLBACK_STATE_OFF = 0
CALLBACK_STATE_ON = 1
CALLBACK_STATE_ON_ALLTICKERS = 2
ALL_TICKERS = 'ALL_TICKERS'
CON_STATE_DROP = False

# --------
# Messages
# --------
_CONN_PREFIX = '[Connection][{}]:'
_SUB_PREFIX = '[Subscription][{}][{}]: '
MSG_INFO_CONN_ESTABLISHING = _CONN_PREFIX + 'Trying to establish connection to Bittrex through {}.'
MSG_INFO_RECONNECT = _SUB_PREFIX + 'Initiating reconnection procedure.'
MSG_INFO_CONN_INIT_RECONNECT = _CONN_PREFIX + 'Initiating reconnection procedure for all relevant subscriptions.'
NSG_INFO_ORDER_BOOK_REQUESTED = _SUB_PREFIX + 'Order book snapshot requested.'
NSG_INFO_ORDER_BOOK_RECEIVED = _SUB_PREFIX + 'Order book snapshot synced.'
MSG_ERROR_CONN_SOCKET = _CONN_PREFIX + 'Timeout for url {}. Please check your internet connection is on.'
MSG_ERROR_CONN_FAILURE = _CONN_PREFIX + 'Failed to establish connection through supplied URLS. Leaving to ' \
                                        'watchdog...'
MSG_ERROR_CONN_TIMEOUT = _CONN_PREFIX + 'Timeout for url {} after {} seconds.'
MSG_INFO_CONNECTED = _CONN_PREFIX + 'Connection to Bittrex established successfully through {}'
MSG_ERROR_SOCKET_WEBSOCKETBADSTATUS = 'Please report error to ' \
                                      'https://github.com/slazarov/python-bittrex-websocket, ' \
                                      'Error:WebSocketBadStatusException'
MSG_ERROR_SOCKET_WEBSOCKETCONNECTIONCLOSED = 'Please report error to ' \
                                             'https://github.com/slazarov/python-bittrex-websocket, ' \
                                             'Error:Init_connection_WebSocketConnectionClosedException'
MSG_ERROR_GEVENT = _CONN_PREFIX + 'Caught {} in gevent. Don\'t worry.'
MSG_ERROR_CONN_MISSING_SCHEMA = _CONN_PREFIX + 'Invalid URL: {}'
MSG_ERROR_CONN_HTTP = _CONN_PREFIX + 'Failed to establish connection through {}'
