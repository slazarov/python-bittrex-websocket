from __future__ import print_function

from time import sleep

from bittrex_websocket.websocket_client import BittrexSocket


def main():
    class MySocket(BittrexSocket):
        def on_orderbook(self, msg):
            print('ding')

    ws = MySocket()
    tickers = ['BTC-ETH', 'BTC-NEO', 'BTC-ZEC', 'ETH-NEO', 'ETH-ZEC']
    ws.subscribe_to_orderbook(tickers)

    while True:
        i = 0
        for ticker in tickers:
            if ws.tickers.get_snapshot_state(ticker) == ws.tickers.SNAPSHOT_ON:
                i += 1
        if i == len(tickers):
            for ticker in tickers:
                ob = ws.get_order_book(ticker)
                name = ob['MarketName']
                quantity = str(ob['Buys'][0]['Quantity'])
                price = str(ob['Buys'][0]['Rate'])
                print('Ticker: ' + name + ', Bids depth 0: ' + quantity + '@' + price)
            break
        else:
            sleep(1)


if __name__ == "__main__":
    main()
