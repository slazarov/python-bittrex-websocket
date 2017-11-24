# bittrex-websocket
Python websocket for Bittrex

*Disclaimer: I am not associated with Bittrex. Use the library at your own risk, I don't bear any responsibility if you end up losing your money.


### Sample usage
```import bittrex_websocket
from time import sleep

if __name__ == "__main__":
    tickers = ['BTC-ETH', 'ETH-1ST', 'BTC-1ST', 'BTC-NEO', 'ETH-NEO']
    order_book = bittrex_websocket.OrderBook(tickers)
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

```
