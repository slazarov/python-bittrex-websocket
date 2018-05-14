from requests.exceptions import HTTPError, MissingSchema, ConnectionError
from urllib3.contrib.pyopenssl import SocketError
from urllib3.exceptions import TimeoutError
from websocket import WebSocketConnectionClosedException, WebSocketBadStatusException, WebSocketTimeoutException


class WebSocketConnectionClosedByUser(Exception):
    pass
