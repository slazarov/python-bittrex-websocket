import signalr
from threading import Thread
from ._exceptions import WebSocketConnectionClosedByUser

import logging

logger = logging.getLogger(__name__)

try:
    from Queue import Queue
except ImportError:
    from queue import Queue

try:
    from ujson import dumps, loads
except:
    from json import dumps, loads


class Connection(signalr.Connection, object):
    def __init__(self, url, session):
        super(Connection, self).__init__(url, session)
        self.__transport = WebSocketsTransport(session, self)
        self.exception = None
        self.queue = Queue()
        self.__queue_handler = None

    def start(self):
        self.starting.fire()

        negotiate_data = self.__transport.negotiate()
        self.token = negotiate_data['ConnectionToken']

        listener = self.__transport.start()

        def wrapped_listener():
            while self.is_open:
                try:
                    listener()
                except Exception as e:
                    event = QueueEvent(event_type='ERROR', payload=e)
                    self.queue.put(event)
                    self.is_open = False
                    self.exception = e
            else:
                self.started = False

        self.is_open = True
        self.__listener_thread = Thread(target=wrapped_listener, name='SignalrListener')
        self.__listener_thread.daemon = True
        self.__listener_thread.start()
        self.queue_handler()

    def queue_handler(self):
        while True:
            event = self.queue.get()
            try:
                if event is not None:
                    if event.type == 'SEND':
                        self.__transport.send(event.payload)
                    elif event.type == 'ERROR':
                        self.exit_gracefully()
                        raise self.exception
                    elif event.type == 'CLOSE':
                        self.exit_gracefully()
                        raise WebSocketConnectionClosedByUser('Connection closed by user.')
            finally:
                self.queue.task_done()

    def send(self, data):
        event = QueueEvent(event_type='SEND', payload=data)
        self.queue.put(event)

    def close(self):
        event = QueueEvent(event_type='CLOSE', payload=None)
        self.queue.put(event)

    def exit_gracefully(self):
        self.is_open = False
        self.__transport.close()
        self.__listener_thread.join()


#################
# UJSON support #
#################

class WebSocketsTransport(signalr.transports._ws_transport.WebSocketsTransport, object):
    def __init__(self, session, connection):
        super(WebSocketsTransport, self).__init__(session, connection)
        self.ws = None
        self.__requests = {}

    def _handle_notification(self, message):
        if len(message) > 0:
            data = loads(message)
            self._connection.received.fire(**data)

    def send(self, data):
        self.ws.send(dumps(data))


################
# Queue Events #
################

class QueueEvent(object):
    def __init__(self, event_type, payload):
        self.type = event_type
        self.payload = payload


class ErrorEvent(object):
    def __init__(self, code, message):
        self.code = code
        self.message = message
