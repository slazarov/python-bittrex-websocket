# bittrex-websocket
**Python** websocket client ([SignalR](https://pypi.python.org/pypi/signalr-client/0.0.7)) for getting live streaming data from [Bittrex Exchange](http://bittrex.com).

The library is mainly written in Python3 but should support Python2 with the same functionality, please report any issues.
### Disclaimer

*I am not associated with Bittrex. Use the library at your own risk, I don't bear any responsibility if you end up losing your money.*

*As of **24 Nov 2017**, there is still no official websocket documentation.*

*The code is licensed under the MIT license. Please consider the following message:*
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

# Testing needed
It's a newly published library so please test it and report for any bugs.
Much appreciated.

# What can I use it for?
You can use it for various purposes, some examples include:
* maintaining live order book
* recording trade history
* analysing order flow

Use your imagination.

# Motivation
I am fairly new to Python and in my experience the best way to learn something is through actual practice. At the same time I am currently actively trading on Bittrex, hence the reason why I decided to build the Bittrex websocket client. I am publishing my code for a few reasons. Firstly, I want to make a contribution to the community, secondly the code needs lots of improvements and it would be great to work on it as a team, thirdly I haven't seen any other Python Bittrex websocket clients so far.

I have been largely motivated by the following projects and people:

* Daniel Paquin: [gdax-python](https://github.com/danpaquin/gdax-python) - a websocket client for GDAX. The project really helped me around using threads and structuring the code.

* [David Parlevliet](https://github.com/dparlevliet) - saw his SignalR code initially which included Bittrex specific commands. Saved me a lot of time in researching.

* Eric Somdahl: [python-bittrex](https://github.com/ericsomdahl/python-bittrex) - great python bindings for Bittrex. Highly recommend it, I use it in conjuction with the websocket client.

# Currently in development
* Test scripts
* PyPi
* Better documentation
* Code cleanup, optimization
* Better error handling
* Lots of stuff, waiting for suggestions

# Done
* ~~More user friendly subscription to the exchange channels.~~

# Dependencies
To successfully install the package the following dependencies must be met:
* [requests[security]](https://github.com/requests/requests)
  * g++, make, libffi-dev, openssl-dev
* [signalr-client](https://github.com/TargetProcess/signalr-client-py)
  * g++, make

I have added a Dockerfile for а quick setup. Please check the docker folder.

I am only adding this as a precaution, in most case you will not have to do anything at all as these are prepackaged with your python installation.

# Installation
```python
pip install git+https://github.com/slazarov/python-bittrex-websocket.git
```
# Methods
#### Subscribe Methods
```python
    def subscribe_to_orderbook(self, tickers, book_depth=10):
        """
        Subscribe and maintain the live order book for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        :param book_depth: The desired depth of the order book to be maintained.
        :type book_depth: int
        """

    def subscribe_to_orderbook_update(self, tickers):
        """
        Subscribe to order book updates for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """

    def subscribe_to_trades(self, tickers):
        """
        Subscribe and receive tick data(executed trades) for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """

    def subscribe_to_ticker_update(self, tickers):
        """
        Subscribe and receive general data updates for a set of ticker(s). Example output:

        {
            'MarketName': 'BTC-ADA',
            'High': 7.65e-06,
            'Low': 4.78e-06,
            'Volume': 1352355429.5288217,
            'Last': 7.2e-06,
            'BaseVolume': 7937.59243908,
            'TimeStamp': '2017-11-28T15:02:17.7',
            'Bid': 7.2e-06,
            'Ask': 7.21e-06,
            'OpenBuyOrders': 4452,
            'OpenSellOrders': 3275,
            'PrevDay': 5.02e-06,
            'Created': '2017-09-29T07:01:58.873'
        }

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """

```

#### Unsubscribe Methods

```python
    def unsubscribe_to_orderbook(self, tickers):
        """
        Unsubscribe from real time order for specific set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """

    def unsubscribe_to_orderbook_update(self, tickers):
        """
        Unsubscribe from order book updates for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """

    def unsubscribe_to_trades(self, tickers):
        """
        Unsubscribe from receiving tick data(executed trades) for a set of ticker(s)

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """

    def unsubscribe_to_ticker_update(self, tickers):
        """
        Unsubscribe from receiving general data updates for a set of ticker(s).

        :param tickers: A list of tickers you are interested in.
        :type tickers: []
        """
```

#### Other Methods

```python
    def get_order_book(self, ticker=None):
        """
        Returns the most recently updated order book for the specific ticker.
        If no ticker is specified, returns a dictionary with the order books of
        all subscribed tickers.

        :param ticker: The specific ticker you want the order book for.
        :type ticker: str
        """

    def get_order_book_sync_state(self, tickers=None):
        """
        Returns the sync state of the order book for the specific ticker(s).
        If no ticker is specified, returns the state for all tickers.
        The sync states are:

            Not initiated = 0
            Invoked, not synced = 1
            Received, not synced, not processing = 2
            Received, synced, processing = 3

        :param tickers: The specific ticker(s) and it's order book sync state you are interested in.
        :type tickers: []
        """

    def disconnect(self):
        """
        Disconnects the connections and stops the websocket instance.
        """
```

# Websocket client
To receive live data feed you must subscribe to the websocket.
##### Subscribe to a single ticker
```python
# Parameters
tickers = tickers = ['BTC-ETH']
conn_type='cloudflare'
ws = bittrex_websocket.BittrexSocket(tickers, conn_type)
ws.run()
# Do some stuff and trade for infinite profit
ws.stop()
```
##### Subscribe to multiple tickers
```python
# Parameters
tickers = tickers = ['BTC-ETH', 'ETH-1ST', 'BTC-1ST', 'BTC-NEO', 'ETH-NEO']
ws = bittrex_websocket.BittrexSocket(tickers)
ws.run()
# Do some stuff and trade for infinite profit
ws.stop()
```
# Message channels
The websocket clients starts a separate thread upon initialization with further subthreads for each connection (currently 20 tickers per connection). There are several methods which could be overwritten. Please check the actual code for further information and examples.
```python
    def on_open(self):
        # Called before initiating the first websocket connection
        # Use it when you want to add some opening logic.

    def on_close(self):
        # Called before closing the websocket instance.
        # Use it when you want to add any closing logic.

    def on_error(self, error):
        # Error handler

    def on_orderbook(self, msg):
        # The main channel of subscribe_to_orderbook().

    def on_orderbook_update(self, msg):
        # The main channel of subscribe_to_orderbook_update().

    def on_trades(self, msg):
        # The main channel of subscribe_to_trades().

    def on_ticker_update(self, msg):
        # The main channel of subscribe_to_ticker_update().
```

# Sample usage
Some sample examples to get you started.
#### Simple logic
```python
import bittrex_websocket
from time import sleep

if __name__ == "__main__":
    class MyBittrexSocket(bittrex_websocket.BittrexSocket):
        def on_open(self):
            self.nounces = []
            self.msg_count = 0

        def on_debug(self, **kwargs):
            pass

        def on_message(self, *args, **kwargs):
            self.nounces.append(args[0])
            self.msg_count += 1


    t = ['BTC-ETH', 'ETH-1ST', 'BTC-1ST', 'BTC-NEO', 'ETH-NEO']
    ws = MyBittrexSocket(t)
    ws.run()
    while ws.msg_count < 20:
        sleep(1)
        continue
    else:
        for msg in ws.nounces:
            print(msg)
    ws.stop()

```

#### Live/Real-time order book
```python
import bittrex_websocket
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
# Change log
0.0.1 - Initial release on github.

# Support
If you find this package helpful and would like to support it, you can do it through here:


| Coin          | Address                                    |
| ------------- |:------------------------------------------:|
| BTC           | 18n4eKg8PB1USs5f95MK34JA4KmaV1YhT2         |
| ETH           | 0xf5a6431ac4acd8b1e5c8b56b9b45e04cdea20e6e |
| LTC           | LZT8o523jwa8ZmgMjPLNMJeVeBnLuAvRvc         |
| ZEC           | t1dhA8QqVsXHR8jGp34a1EY8mM7bZ9FjhTW        |
