#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/constants.py
# Stanislav Lazarov

INVALID_SUB = 'Subscription type is invalid or not implemented. ' \
              'Available options: OrderBook, OrderBookUpdate, Trades'
INVALID_SUB_CHANGE = 'Subscription change is invalid. Available options: True/False'
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
CALLBACK_EXCHANGE_DELTAS = 'SubscribeToExchangeDeltas'
CALLBACK_SUMMARY_DELTAS = 'SubscribeToSummaryDeltas'
CALLBACK_STATE_OFF = 0
CALLBACK_STATE_ON = 1
CALLBACK_STATE_ON_ALLTICKERS = 2
ALL_TICKERS = 'ALL_TICKERS'
