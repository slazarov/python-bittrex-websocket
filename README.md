# bittrex-websocket
**Python** websocket client ([SignalR](https://pypi.python.org/pypi/signalr-client/0.0.7)) for getting live streaming data from [Bittrex Exchange](http://bittrex.com).

The library is mainly written in Python3 but should support Python2 with the same functionality, please report any issues.

If you prefer asyncio (Python>=3.5), try my other library https://github.com/slazarov/python-bittrex-websocket-aio.

# My plans for the websocket client

Bittrex released their [official beta websocket documentation](https://github.com/Bittrex/beta) on 27-March-2018.
The major changes were the removal of the need to bypass Cloudflare and the introduction of new public (`Lite Summary Delta`) and private (`Balance Delta` & `Order Delta`) channels.

Following that, I decided to repurpose the client as a higher level Bittrex API which users can use to build on. The major changes are:

* ~~Existing methods will be restructured in order to mimic the official ones, i.e `subscribe_to_orderbook_update` will become `subscribe_to_exchange_deltas`. This would make referencing the official documentation more clear and will reduce confusion.~~
* ~~`QueryExchangeState` will become a public method so that users can invoke it freely.~~
* The method `subscribe_to_orderbook` will be removed and instead placed as a separate module. Before the latter happens, users can use the legacy library.
* ~~Private, account specific methods will be implemented, i.e `Balance Delta` & `Order Delta`~~
* ~~Replacement of the legacy `on_channels` with only two channels for the public and private streams.~~

My goal is to maintain the interface of the two socket versions as similar as possible and leave the choice between async/gevent and Python2/3 to the users.
Saying that, I still prefer the async version.

### Disclaimer

*I am not associated with Bittrex. Use the library at your own risk, I don't bear any responsibility if you end up losing your money.*

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
* [What can I use it for?](#what-can-i-use-it-for)
* [Notices](#notices)
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
* [Other libraries](#other-libraries)
* [Support](#support)
* [Motivation](#motivation)


# What can I use it for?
You can use it for various purposes, some examples include:
* maintaining live order book
* recording trade history
* analysing order flow

Use your imagination.

# Notices
**14/04/2018**

The async version of the socket has been released: [python-bittrex-websocket-aio](https://github.com/slazarov/python-bittrex-websocket-aio).

**27/03/2018**

Bittrex has published officicial beta [documentation](https://github.com/Bittrex/beta).

# Road map


# Dependencies
To successfully install the package the following dependencies must be met:

* [requests[security]](https://github.com/requests/requests)
  * g++, make, libffi-dev, openssl-dev
* [signalr-client](https://github.com/slazarov/signalr-client-py)
  * g++, make

I have added a Dockerfile for а quick setup. Please check the docker folder. The example.py is not always up to date.

I am only adding this as a precaution, in most case you will not have to do anything at all as these are prepackaged with your python installation.

# Installation

The library can be installed through Github and PyPi. For the latest updates, use Github.

```python
pip install git+https://github.com/slazarov/python-bittrex-websocket.git
pip install git+https://github.com/slazarov/python-bittrex-websocket.git@next-version-number
pip install bittrex-websocket
```
# Methods
#### Subscribe Methods
```python
def subscribe_to_exchange_deltas(self, tickers):
    """
    Allows the caller to receive real-time updates to the state of a SINGLE market.
    Upon subscribing, the callback will be invoked with market deltas as they occur.

    This feed only contains updates to exchange state. To form a complete picture of
    exchange state, users must first call QueryExchangeState and merge deltas into
    the data structure returned in that call.

    :param tickers: A list of tickers you are interested in.
    :type tickers: []
    """


def subscribe_to_summary_deltas(self):
    """
    Allows the caller to receive real-time updates of the state of ALL markets.
    Upon subscribing, the callback will be invoked with market deltas as they occur.

    Summary delta callbacks are verbose. A subset of the same data limited to the
    market name, the last price, and the base currency volume can be obtained via
    `subscribe_to_summary_lite_deltas`.

    https://github.com/Bittrex/beta#subscribetosummarydeltas
    """

def subscribe_to_summary_lite_deltas(self):
    """
    Similar to `subscribe_to_summary_deltas`.
    Shows only market name, last price and base currency volume.

    """

def query_summary_state(self):
    """
    Allows the caller to retrieve the full state for all markets.
    """

def query_exchange_state(self, tickers):
    """
    Allows the caller to retrieve the full order book for a specific market.

    :param tickers: A list of tickers you are interested in.
    :type tickers: []
    """

def authenticate(self, api_key, api_secret):
    """
    Verifies a user’s identity to the server and begins receiving account-level notifications

    :param api_key: Your api_key with the relevant permissions.
    :type api_key: str
    :param api_secret: Your api_secret with the relevant permissions.
    :type api_secret: str
    """
```

#### Other Methods

```python
def disconnect(self):
    """
    Disconnects the socket.
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
```python
def on_public(self, msg):
    # The main channel for all public methods.

def on_private(self, msg):
    # The main channel for all private methods.

def on_error(self, error):
    # Receive error message from the SignalR connection.

```

# Sample usage
Check the examples folder.

# Change log
1.0.0.0 - 15/04/2018
* As per the [road map](#my-plans-for-the-websocket-client)

0.0.7.3 - 06/04/2018
* Set cfscrape >=1.9.5

0.0.7.2 - 31/03/2018
* Added third connection URL.

0.0.7.1 - 31/03/2018
* Removed wsaccel: no particular socket benefits
* Fixed RecursionError as per [Issue #52](https://github.com/slazarov/python-bittrex-websocket/issues/52)

0.0.7.0 - 25/02/2018
* New reconnection methods implemented. Problem was within `gevent`, because connection failures within it are not raised in the main script.
* Added wsaccel for better socket performance.
* Set websocket-client minimum version to 0.47.0

0.0.6.4 - 24/02/2018
* Fixed order book syncing bug when more than 1 connection is online due to wrong connection/thread name.

0.0.6.3 - 18/02/2018
* Major changes to how the code handles order book syncing. Syncing is done significantly faster than previous versions, i.e full sync of all Bittrex tickers takes ca. 4 minutes.
* Fixed `on_open` bug as per [Issue #21](https://github.com/slazarov/python-bittrex-websocket/issues/21)

0.0.6.2.2
* Update cfscrape>=1.9.2 and gevent>=1.3a1
* Reorder imports in websocket_client to safeguard against SSL recursion errors.

0.0.6.2
* Every 5400s (1hr30) the script will force reconnection.
* Every reconnection (including the above) will be done with a fresh cookie
* Upon reconnection the script will check if the connection has been running for more than 600s (10mins). If it has been running for less it will use the backup url.

0.0.6.1
* Set websocket-client==0.46.0

0.0.6
* Reconnection - Experimental
* Fixed a bug when subscribing to multiple subscription types at once resulted in opening unnecessary connections even though there is sufficient capacity in the existing [Commit 7fd21c](https://github.com/slazarov/python-bittrex-websocket/commit/7fd21cad87a8bd7c88070bab0fd5774b0324332e)
* Numerous code optimizations

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

# Other libraries
**[Python Bittrex Autosell](https://github.com/slazarov/python-bittrex-autosell)**

Python CLI tool to auto sell coins on Bittrex.

It is used in the cases when you want to auto sell a specific coin for another, but there is no direct market, so you have to use an intermediate market.

# Motivation
I am fairly new to Python and in my experience the best way to learn something is through actual practice. At the same time I am currently actively trading on Bittrex, hence the reason why I decided to build the Bittrex websocket client. I am publishing my code for a few reasons. Firstly, I want to make a contribution to the community, secondly the code needs lots of improvements and it would be great to work on it as a team, thirdly I haven't seen any other Python Bittrex websocket clients so far.

I have been largely motivated by the following projects and people:

* Daniel Paquin: [gdax-python](https://github.com/danpaquin/gdax-python) - a websocket client for GDAX. The project really helped me around using threads and structuring the code.

* [David Parlevliet](https://github.com/dparlevliet) - saw his SignalR code initially which included Bittrex specific commands. Saved me a lot of time in researching.

* Eric Somdahl: [python-bittrex](https://github.com/ericsomdahl/python-bittrex) - great python bindings for Bittrex. Highly recommend it, I use it in conjuction with the websocket client.