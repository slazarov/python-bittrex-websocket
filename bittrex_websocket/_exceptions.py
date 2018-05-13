from requests.exceptions import HTTPError, MissingSchema
from urllib3.contrib.pyopenssl import SocketError
from websocket import WebSocketConnectionClosedException, WebSocketBadStatusException
from requests.exceptions import ConnectionError


class WebSocketConnectionClosedByUser(Exception):
    pass
