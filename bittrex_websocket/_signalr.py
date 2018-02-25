import signalr
import gevent
from ._exceptions import WebSocketConnectionClosedException


class Connection(signalr.Connection):
    def __init__(self, url, session):
        super(Connection, self).__init__(url, session)
        self.error_trap = None

    def start(self):
        self.starting.fire()

        negotiate_data = self.__transport.negotiate()
        self.token = negotiate_data['ConnectionToken']

        listener = self.__transport.start()

        def wrapped_listener():

            # listener()
            # gevent.sleep()

            try:
                listener()
                gevent.sleep()
            except Exception as e:
                self.close()
                self.error_trap = e

        self.__greenlet = gevent.spawn(wrapped_listener)
        self.started = True

    def wait(self, timeout=30):
        gevent.joinall([self.__greenlet], timeout)
        if self.error_trap is not None:
            return self.error_trap
