from requests.exceptions import HTTPError, MissingSchema, ConnectionError
from urllib3.contrib.pyopenssl import SocketError
from urllib3.exceptions import TimeoutError as TimeoutErrorUrlLib
from websocket import WebSocketConnectionClosedException, WebSocketBadStatusException, WebSocketTimeoutException

try:
    class TimeoutError(TimeoutError):
        def __init__(self):
            super(TimeoutError, self).__init__()

except NameError:
    class TimeoutError(Exception):
        def __init__(self):
            super(TimeoutError, self).__init__()


class WebSocketConnectionClosedByUser(Exception):
    pass
