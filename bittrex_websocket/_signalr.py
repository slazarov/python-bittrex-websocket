import signalr
from threading import Thread
from websocket import create_connection

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
        self.error_trap = None
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

        self.is_open = True
        self.__listener_thread = Thread(target=wrapped_listener)
        self.__listener_thread.start()
        self.started = True
        return self.queue_handler()

    def queue_handler(self):
        while True:
            event = self.queue.get()
            try:
                if event is not None:
                    if event.type == 'SEND':
                        self.__transport.send(event.payload)
                    elif event.type == 'ERROR':
                        code = self.assign_error_code(event.payload)
                        return ErrorEvent(code, event.payload.args[0])
                    elif event.type == 'CLOSE':
                        self.is_open = False
                        self.__listener_thread.join()
                        self.__transport.close()
                        return ErrorEvent(1000, 'Closed by user.')
            finally:
                self.queue.task_done()

    def wait(self, timeout=30):
        Thread.join(self.__listener_thread, timeout)
        if self.error_trap is not None:
            return self.error_trap

    def send(self, data):
        event = QueueEvent(event_type='SEND', payload=data)
        self.queue.put(event)

    def close(self):
        event = QueueEvent(event_type='CLOSE', payload=None)
        self.queue.put(event)

    @staticmethod
    def assign_error_code(error):
        if error.args[0] == 'Connection is already closed.':
            return 1006
        else:
            return -1


# Add ujson support
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


class QueueEvent(object):
    def __init__(self, event_type, payload):
        self.type = event_type
        self.payload = payload


class ErrorEvent(object):
    def __init__(self, code, message):
        self.code = code
        self.message = message
