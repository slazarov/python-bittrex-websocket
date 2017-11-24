# bittrex-websocket
**Python3** websocket client ([SignalR](https://pypi.python.org/pypi/signalr-client/0.0.7)) for getting live streaming data from [Bittrex Exchange](http://bittrex.com).

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

# What can I use it for?
You can use it for various purposes, some examples include:
* maintaining live order book
* recording trade history
* analysing order flow

Use your imagination

# Motivation
I am fairly new to Python and in my experience the best way to learn something is through actual practice. At the same time I am currently actively trading on Bittrex, hence the reason why I decided to build the Bittrex websocket client. I am publishing my code for a few reasons. Firstly, I want to make a contribution to the community, secondly the code needs lots of improvements and it would be great to work on it as a team, thirdly I haven't seen any other Python Bittrex websocket clients so far.

I have been largely motivated by the following projects and people:

* Daniel Paquin: [gdax-python](https://github.com/danpaquin/gdax-python) - a websocket client for GDAX. The project really helped me around using threads and structuring the code.

* [David Parlevliet](https://github.com/dparlevliet) - saw his SignalR code initially which included Bittrex specific commands. Saved me a lot of time in researching.

* Eric Somdahl: [python-bittrex](https://github.com/ericsomdahl/python-bittrex) - great python bindings for Bittrex. Highly recommend it, I use it in conjuction with the websocket client.

# To do
* Test scripts
* PyPi
* Better documentation
* Code cleanup, optimization
* Better error handling
* Lots of stuff, waiting for suggestions

# Dependencies
To successfully install the package the following dependencies must be met:
* [requests[security]](https://github.com/requests/requests)
  * g++, make, libffi-dev, openssl-dev
* [signalr-client](https://github.com/TargetProcess/signalr-client-py)
  * g++, make

I have added a Dockerfile for а quick setup. Please check the docker folder.

# Installation
```python
pip install git+https://github.com/slazarov/python-bittrex-websocket.git
```
# Parameters
##### bittrex_websocket.BittrexSocket(tickers, conn_type)
        :param tickers: a list of tickers, single tickers should also be supplied as a list. Default: ['ETH-BTC']
        :type tickers: []
        :param conn_type: 'normal' direct connection or 'cloudflare' workaround. Default: 'normal
        :type conn_type: str
##### bittrex_websocket.OrderBook(tickers, book_depth, conn_type)
        :param book_depth: The depth of the order book, Default: 10
        :type book_depth: int

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
# Websocket methods
The websocket clients starts a separate thread upon initialization with further subthreads for each connection (currently 20 tickers per connection). There are several methods which could be overwritten. Please check the actual code for further information and examples.
##### on_open
Called before initiating the websocket connection
Use it when you want to add optional parameters
##### on_close
Called after closing the websocket connection
Use it when you want to add any closing logic.
##### on_debug
Debug information, shows all data, this is where you get order book snapshots.
Please check bittrex_websocket.OrderBook for further information.
##### on_close
Handle any errors from the websocket here.
Future releases will handle errors without having to do it yourself.
##### on_message
This is the main method which you will use. Messages contain the order flow stream. Check bittrex_websocket.BittrexSocket for the structure and further information.

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
