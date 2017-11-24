#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/order_book.py
# Stanislav Lazarov

import queue
from copy import deepcopy
from threading import Thread
from time import sleep, time

from requests import get

from bittrex_websocket.websocket_client import BittrexSocket


class OrderBook(BittrexSocket):
    def __init__(self, tickers: [] = None, book_depth: int = 10, conn_type: str = 'normal'):
        if tickers is None:
            self.tickers = ['BTC-ETH']
        else:
            self.tickers = tickers
        super(OrderBook, self).__init__(tickers=self.tickers, conn_type=conn_type)
        self.book_depth = book_depth
        self.tick_queue = queue.Queue()
        self.snapshot_ls = deepcopy(self.tickers)
        self.orderbook_events = queue.Queue()
        self.api_order_books = {}
        self.socket_order_books = {}

    def _go(self):
        # Create socket connections
        self._start()
        # Get static snapshopts
        self.api_order_books = self.get_static_snapshots()
        # Match and confirm order books
        self.confirm_orderbook()
        # Start syncing with updates queue
        self.sync()

    def _get_subscribe_commands(self):
        return ['SubscribeToExchangeDeltas', 'queryExchangeState']

    def get_static_snapshots(self):
        order_queue = queue.Queue()
        num_threads = min(len(self.tickers), 10)
        order_books = {}

        for ticker in self.tickers:
            # Load the queue with api_tickers
            order_queue.put(ticker)
            # Pre-order order books
            order_books[ticker] = \
                {
                    'buy': None,
                    'sell': None,
                    'MarketName': ticker
                }

        def _retrieve(q, result):
            while not q.empty():
                work = q.get(False)
                try:
                    api_url = 'https://bittrex.com/api/v1.1/public/getorderbook'
                    payload = {'market': work, 'type': 'both'}
                    data = get(api_url, payload).json()['result']
                    result[work] = \
                        {
                            'buy': data['buy'],
                            'sell': data['sell'],
                            'MarketName': work,
                        }
                except Exception as e:
                    print(e)
                    break
                q.task_done()

        print('Retrieving order book snapshot...')
        for j in range(num_threads):
            worker = Thread(target=_retrieve, args=(order_queue, order_books))
            worker.setDaemon(True)
            worker.start()

        order_queue.join()
        print('Order book snapshot retrieved.')
        return order_books

    def confirm_orderbook(self):
        def _get_queue(queue_object1):
            try:
                event = queue_object1.get(False)
            except queue.Empty:
                sleep(0.5)
            else:
                if event is not None and _confirm(event):
                    queue_object1.task_done()

        def _confirm(event):
            # Currently confirms only the BUY side.
            side_matched = False
            j = 0
            ticker_del = -1
            for order in event['Buys']:
                if side_matched is False:
                    order_matched = False
                    for ticker in self.api_order_books:
                        if order_matched is False:
                            for k, order2 in enumerate(self.api_order_books[ticker]['buy']):
                                if order == order2:
                                    j += 1
                                    order_matched = True
                                    if j == 5:
                                        j = 0
                                        side_matched = True
                                        ticker_del = ticker
                                    del self.api_order_books[ticker]['buy'][k]
                                    break
                        else:
                            break
                else:
                    del self.api_order_books[ticker_del]
                    event['MarketName'] = ticker_del
                    del event['Fills']
                    event['Buys'] = event['Buys'][0:self.book_depth]
                    event['Sells'] = event['Sells'][0:self.book_depth]
                    self.socket_order_books[ticker_del] = event
                    return True

        # Wait until all the snapshot requests are received from the websocket
        while self.orderbook_events.unfinished_tasks < len(self.tickers):
            sleep(0.5)
        else:
            print('Order books\' name confirmation in progress...')
            # Wait until the order book snapshots are identified and confirmed
            while len(self.socket_order_books) < len(self.tickers):
                _get_queue(self.orderbook_events)
            else:
                print('Order books\' name confirmed. Start syncing...')

    def sync(self):
        while True:
            # Wait for the order books to be confirmed.
            if self.socket_order_books != {}:
                while True:
                    try:
                        event = self.tick_queue.get()
                    except queue.Empty:
                        pass
                    else:
                        if event is not None:
                            self._sync_order_book(event)
                            self.tick_queue.task_done()

    def _sync_order_book(self, order_data):
        # Syncs the order book for the pair given the most recent data from the socket
        pair_name = order_data['MarketName']
        nounce_diff = order_data['Nounce'] - self.socket_order_books[pair_name]['Nounce']
        if nounce_diff == 1:
            self.socket_order_books[pair_name]['Nounce'] = order_data['Nounce']
            # Start syncing
            for side in [['Buys', True], ['Sells', False]]:
                made_change = False

                for order in order_data[side[0]]:
                    # TYPE 0: New order entries at matching price
                    # -> ADD to order book
                    if order['Type'] == 0:
                        self.socket_order_books[pair_name][side[0]].append(
                            {
                                'Quantity': order['Quantity'],
                                'Rate': order['Rate']
                            })
                        made_change = True

                    # TYPE 1: Cancelled / filled order entries at matching price
                    # -> DELETE from the order book
                    elif order['Type'] == 1:
                        for i, existing_order in enumerate(
                                self.socket_order_books[pair_name][side[0]]):
                            if existing_order['Rate'] == order['Rate']:
                                del self.socket_order_books[pair_name][side[0]][i]
                                made_change = True
                                break

                    # TYPE 2: Changed order entries at matching price (partial fills, cancellations)
                    # -> EDIT the order book
                    elif order['Type'] == 2:
                        for existing_order in self.socket_order_books[pair_name][side[0]]:
                            if existing_order['Rate'] == order['Rate']:
                                existing_order['Quantity'] = order['Quantity']
                                made_change = True
                                break

                if made_change:
                    # Sort by price, with respect to BUY(desc) or SELL(asc)
                    self.socket_order_books[pair_name][side[0]] = sorted(
                        self.socket_order_books[pair_name][side[0]],
                        key=lambda k: k['Rate'],
                        reverse=side[1])
                    # Put depth to 10
                    self.socket_order_books[pair_name][side[0]] = \
                        self.socket_order_books[pair_name][side[0]][
                        0:self.book_depth]
                    # Add nounce unix timestamp
                    self.socket_order_books[pair_name]['NounceStamp'] = time()
        elif nounce_diff <= 0:
            return
        else:
            raise NotImplementedError("Implement nounce resync!")

    # Debug information, shows all data
    def debug(self, **kwargs):
        # Orderbook snapshot:
        if 'R' in kwargs and type(kwargs['R']) is not bool:
            self.orderbook_events.put(kwargs['R'])

    def ticker_data(self, *args, **kwargs):
        self.tick_queue.put(args[0])


if __name__ == "__main__":
    tickers = ['BTC-ETH', 'ETH-1ST', 'BTC-1ST', 'BTC-NEO', 'ETH-NEO']
    order_book = OrderBook(tickers, conn_type='cloudflare')
    order_book.run()

    # Do some sample work
    # Wait until the order book snapshots are identified and confirmed
    while len(order_book.socket_order_books) < len(order_book.tickers):
        sleep(5)
    else:
        for ticker in order_book.socket_order_books.values():
            name = ticker['MarketName']
            quantity = str(ticker['Buys'][0]['Quantity'])
            price = str(ticker['Buys'][0]['Rate'])
            print('Ticker: ' + name + ', Bids depth 0: ' + quantity + '@' + price)
        order_book.stop()
