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

# Table of contents
* [bittrex\-websocket](#bittrex-websocket)
* [Table of contents](#table-of-contents)
* [Testing needed](#testing-needed)
* [What can I use it for?](#what-can-i-use-it-for)
* [Motivation](#motivation)
* [Road map](#road-map)
* [Dependencies](#dependencies)
* [Installation](#installation)
* [Methods](#methods)
  * [Subscribe Methods](#subscribe-methods)
  * [Unsubscribe Methods](#unsubscribe-methods)
  * [Other Methods](#other-methods)
* [Message channels](#message-channels)
* [Sample usage](#sample-usage)
* [Change log](#change-log)
* [Support](#support)

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

# Road map

### Notices
On 11 Jan 2018 the names of the unsubscribe methods will change from:
```
unsubscribe_to_orderbook
unsubscribe_to_orderbook_update
unsubscribe_to_trades
unsubscribe_to_ticker_update
```
to
```
unsubscribe_from_orderbook
unsubscribe_from_orderbook_update
unsubscribe_from_trades
unsubscribe_from_ticker_update
```

### Currently in development
* Socket reconnection handling
* Test scripts
* Code cleanup, optimization
* Lots of stuff, waiting for suggestions

### Done
* ~~More user friendly subscription to the exchange channels.~~
* ~~Pypi~~

# Dependencies
To successfully install the package the following dependencies must be met:
* [requests[security]](https://github.com/requests/requests)
  * g++, make, libffi-dev, openssl-dev
* [signalr-client](https://github.com/TargetProcess/signalr-client-py)
  * g++, make

I have added a Dockerfile for а quick setup. Please check the docker folder.

I am only adding this as a precaution, in most case you will not have to do anything at all as these are prepackaged with your python installation.

# Installation
#### Pypi (most stable)
```python
pip install bittrex-websocket
```
#### Github (master)
```python
pip install git+https://github.com/slazarov/python-bittrex-websocket.git
```
#### Github (work in progress branch)
```python
pip install git+https://github.com/slazarov/python-bittrex-websocket.git@next-version-number
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

def enable_log(file_name=None):
    """
    Enables logging.

    :param file_name: The name of the log file, located in the same directory as the executing script.
    :type file_name: str
    """

def disable_log():
    """
    Disables logging.
    """
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
To receive live data feed you must instantiate the websocket and use one of its subscribe methods. For the various subscription methods check above. Example:
##### Subscribe to a single ticker
```python
# Tickers
tickers = ['ETH-ZEC'] # use lists
ws = MySocket()
ws.subscribe_to_orderbook(tickers)
# Do some stuff and trade for infinite profit
ws.disconnect()
```
##### Subscribe to multiple tickers
```python
# Tickers
tickers = ['BTC-ETH', 'BTC-NEO', 'BTC-ZEC', 'ETH-NEO', 'ETH-ZEC'] # use lists
ws = MySocket()
ws.subscribe_to_ticker_update(tickers)
# Do some stuff and trade for infinite profit
ws.disconnect()
```

Let's get some 'practical' examples.

Note that with library updates, the methods and data structure might change, so check the examples folder for the most up to date examples.
#### Record trades
```python
from __future__ import print_function
from time import sleep
from bittrex_websocket.websocket_client import BittrexSocket


def main():
    class MySocket(BittrexSocket):
        def on_open(self):
            self.trade_history = {}

        def on_trades(self, msg):
            # Create entry for the ticker in the trade_history dict
            if msg['ticker'] not in self.trade_history:
                self.trade_history[msg['ticker']] = []
            # Add history nounce
            self.trade_history[msg['ticker']].append(msg)
            # Ping
            print('[Trades]: {}'.format(msg['ticker']))

    # Create the socket instance
    ws = MySocket()
    # Enable logging
    ws.enable_log()
    # Define tickers
    tickers = ['BTC-ETH', 'BTC-XMR']
    # Subscribe to trade fills
    ws.subscribe_to_trades(tickers)

    while len(set(tickers) - set(ws.trade_history)) > 0:
        sleep(1)
    else:
        for ticker in ws.trade_history.keys():
            print('Printing {} trade history.'.format(ticker))
            for trade in ws.trade_history[ticker]:
                print(trade)
        ws.disconnect()

if __name__ == "__main__":
    main()
```

#### Live/Real-time order book
```python
from __future__ import print_function
from time import sleep
from bittrex_websocket.websocket_client import BittrexSocket


def main():
    class MySocket(BittrexSocket):
        def on_orderbook(self, msg):
            print('[OrderBook]: {}'.format(msg['MarketName']))

    # Create the socket instance
    ws = MySocket()
    # Enable logging
    ws.enable_log()
    # Define tickers
    tickers = ['BTC-ETH', 'BTC-NEO', 'BTC-ZEC', 'ETH-NEO', 'ETH-ZEC']
    # Subscribe to live order book
    ws.subscribe_to_orderbook(tickers)

    while True:
        i = 0
        sync_states = ws.get_order_book_sync_state()
        for state in sync_states.values():
            if state == 3:
                i += 1
        if i == len(tickers):
            print('We are fully synced. Hooray!')
            for ticker in tickers:
                ob = ws.get_order_book(ticker)
                name = ob['MarketName']
                quantity = str(ob['Buys'][0]['Quantity'])
                price = str(ob['Buys'][0]['Rate'])
                print('Ticker: ' + name + ', Bids depth 0: ' + quantity + '@' + price)
            ws.disconnect()
            break
        else:
            sleep(1)

if __name__ == "__main__":
    main()
```
#### Ticker general information update
```python
from __future__ import print_function
from time import sleep
from bittrex_websocket.websocket_client import BittrexSocket


def main():
    class MySocket(BittrexSocket):
        def on_open(self):
            self.ticker_updates_container = {}

        def on_ticker_update(self, msg):
            name = msg['MarketName']
            if name not in self.ticker_updates_container:
                self.ticker_updates_container[name] = msg
                print('Just received ticker update for {}.'.format(name))

    # Create the socket instance
    ws = MySocket()
    # Enable logging
    ws.enable_log()
    # Define tickers
    tickers = ['BTC-ETH', 'BTC-NEO', 'BTC-ZEC', 'ETH-NEO', 'ETH-ZEC']
    # Subscribe to ticker information
    ws.subscribe_to_ticker_update(tickers)

    while len(ws.ticker_updates_container) < len(tickers):
        sleep(1)
    else:
        print('We have received updates for all tickers. Closing...')
        ws.disconnect()

if __name__ == "__main__":
    main()
```
# Change log
0.0.5.1
* Updated cfscrape minimum version requirement ([Issue #12](https://github.com/slazarov/python-bittrex-websocket/issues/12)).

0.0.5
* Fixed [Issue #9](https://github.com/slazarov/python-bittrex-websocket/issues/9) relating to `subscribe_to_orderbook_update` handling in internal method `_on_tick_update`
* Added custom logger as per [PR #10](https://github.com/slazarov/python-bittrex-websocket/issues/10) and [Issue #8](https://github.com/slazarov/python-bittrex-websocket/issues/8) in order to avoid conflicts with other `basicConfig` setups
  * Added two new methods `enable_log` and `disable_log`. Check [Other Methods](#other-methods).
  * Logging is now disabled on startup. You have to enable it.
* **Experimental**: Calling `subscribe_to_ticker_update` without a specified ticker subscribes to all tickers in the message stream ([Issue #4](https://github.com/slazarov/python-bittrex-websocket/issues/4)).
* Minor code optimizations (removed unnecessary class Common)

0.0.4 - Changed the behaviour of how on_ticker_update channel works:
The message now contains a single ticker instead of a dictionary of all subscribed tickers.

0.0.3 - Removed left over code from initial release version that was throwing errors (had no effect on performance).

0.0.2 - Major improvements:

* Additional un/subscribe and order book sync state querying methods added.
* Better connection and thread management.
* Code optimisations
* Better code documentation
* Added additional connection URLs

0.0.1 - Initial release on github.

# Support
If you find this package helpful and would like to support it, you can do it through here:


| Coin          | Address                                    |
| ------------- |:------------------------------------------:|
| BTC           | 18n4eKg8PB1USs5f95MK34JA4KmaV1YhT2         |
| ETH           | 0xf5a6431ac4acd8b1e5c8b56b9b45e04cdea20e6e |
| LTC           | LZT8o523jwa8ZmgMjPLNMJeVeBnLuAvRvc         |
| ZEC           | t1dhA8QqVsXHR8jGp34a1EY8mM7bZ9FjhTW        |
