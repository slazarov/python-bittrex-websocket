# from bittrex_websocket.auxiliary import *
import logging

from bittrex_websocket.constants import *
from bittrex_websocket.websocket_client import BittrexSocket

try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass


def add_stream_logger(level=logging.DEBUG, format_type=logging.BASIC_FORMAT):
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter(format_type)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


logging.getLogger(__name__).addHandler(NullHandler())
