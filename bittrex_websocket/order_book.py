#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/order_book.py
# Stanislav Lazarov

from bittrex_websocket.websocket_client import BittrexSocket
from bittrex_websocket.constants import BittrexMethods
from ._queue_events import ConfirmEvent, SyncEvent
import logging
from .constants import EventTypes
from collections import deque
from time import sleep, time
from events import Events

logger = logging.getLogger(__name__)


class OrderBook(BittrexSocket):
    def __init__(self, url=None, retry_timeout=None, max_retries=None):
        super(OrderBook, self).__init__(url, retry_timeout, max_retries)
        self._on_ping = Events()
        self._on_ping.on_change += self.on_ping
        self.order_nounces = {}
        self.order_books = {}

    def get_order_book(self, ticker):
        if ticker in self.order_books:
            return self.order_books[ticker]

    def control_queue_handler(self):
        while True:
            event = self.control_queue.get()
            if event is not None:
                if event.type == EventTypes.CONNECT:
                    self._handle_connect()
                elif event.type == EventTypes.SUBSCRIBE:
                    self._handle_subscribe(event)
                elif event.type == EventTypes.RECONNECT:
                    self._handle_reconnect(event.error_message)
                elif event.type == EventTypes.CONFIRM_OB:
                    self._confirm_order_book(event.ticker, event.order_nounces)
                elif event.type == EventTypes.SYNC_OB:
                    self._sync_order_book(event.ticker, event.order_nounces)
                elif event.type == EventTypes.CLOSE:
                    self.connection.conn.close()
                    break
                self.control_queue.task_done()

    def subscribe_to_orderbook(self, ticker):
        self.subscribe_to_exchange_deltas(ticker)

    def _handle_subscribe_for_ticker(self, invoke, payload):
        if invoke in [BittrexMethods.SUBSCRIBE_TO_EXCHANGE_DELTAS, BittrexMethods.QUERY_EXCHANGE_STATE]:
            for ticker in payload[0]:
                self.connection.corehub.server.invoke(invoke, ticker)
                self.invokes.append({'invoke': invoke, 'ticker': ticker})
                logger.info('Successfully subscribed to [{}] for [{}].'.format(invoke, ticker))
            return True
        elif invoke is None:
            return True
        return False

    def on_public(self, msg):
        if msg['invoke_type'] == BittrexMethods.SUBSCRIBE_TO_EXCHANGE_DELTAS:
            ticker = msg['M']
            if ticker not in self.order_nounces:
                self.order_nounces[ticker] = deque()
                self.query_exchange_state([ticker])
            elif ticker in self.order_nounces:
                if self.order_nounces[ticker] is False:
                    pass
                else:
                    self.order_nounces[ticker].append(msg)
            if ticker in self.order_books:
                if self.order_nounces[ticker]:
                    # event = ConfirmEvent(ticker, self.order_nounces[ticker])
                    self._confirm_order_book(ticker, self.order_nounces[ticker])
                    self.order_nounces[ticker] = False
                    # self.control_queue.put(event)
                else:
                    # event = SyncEvent(ticker, msg)
                    # self.control_queue.put(event)
                    self._sync_order_book(ticker, msg)
        elif msg['invoke_type'] == BittrexMethods.QUERY_EXCHANGE_STATE:
            ticker = msg['ticker']
            self.order_books[ticker] = msg
            for i in range(len(self.invokes)):
                if self.invokes[i]['ticker'] == ticker and self.invokes[i]['invoke'] == msg['invoke_type']:
                    self.invokes[i]['invoke'] = None
                    break

    def _confirm_order_book(self, ticker, order_nounces):
        for delta in order_nounces:
            if self._sync_order_book(ticker, delta):
                return

    def _sync_order_book(self, ticker, order_data):
        # Syncs the order book for the pair, given the most recent data from the socket
        nounce_diff = order_data['N'] - self.order_books[ticker]['N']
        if nounce_diff == 1:
            self.order_books[ticker]['N'] = order_data['N']
            # Start syncing
            for side in [['Z', True], ['S', False]]:
                made_change = False
                for item in order_data[side[0]]:
                    # TYPE 0: New order entries at matching price
                    # -> ADD to order book
                    if item['TY'] == 0:
                        self.order_books[ticker][side[0]].append(
                            {
                                'Q': item['Q'],
                                'R': item['R']
                            })
                        made_change = True

                    # TYPE 1: Cancelled / filled order entries at matching price
                    # -> DELETE from the order book
                    elif item['TY'] == 1:
                        for i, existing_order in enumerate(
                                self.order_books[ticker][side[0]]):
                            if existing_order['R'] == item['R']:
                                del self.order_books[ticker][side[0]][i]
                                # made_change = True
                                break

                    # TYPE 2: Changed order entries at matching price (partial fills, cancellations)
                    # -> EDIT the order book
                    elif item['TY'] == 2:
                        for existing_order in self.order_books[ticker][side[0]]:
                            if existing_order['R'] == item['R']:
                                existing_order['Q'] = item['Q']
                                # made_change = True
                                break

                if made_change:
                    # Sort by price, with respect to BUY(desc) or SELL(asc)
                    self.order_books[ticker][side[0]] = sorted(
                        self.order_books[ticker][side[0]], key=lambda k: k['R'], reverse=side[1])
                    # Add nounce unix timestamp
                    self.order_books[ticker]['timestamp'] = time()
            self._on_ping.on_change(ticker)
            return True
        # The next nounce will trigger a sync.
        elif nounce_diff == 0:
            return True
        # The order book snapshot nounce is ahead. Discard this nounce.
        elif nounce_diff < 0:
            return False
        else:
            # Experimental resync
            logger.error(
                '[Subscription][{}][{}]: Out of sync. Trying to resync...'.format(BittrexMethods.QUERY_EXCHANGE_STATE,
                                                                                  ticker))
            self.order_nounces.pop(ticker)
            self.order_books.pop(ticker)

    def on_ping(self, msg):
        pass
