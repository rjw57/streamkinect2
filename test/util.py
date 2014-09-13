"""
Common utilities for tests.
"""

from tornado.testing import AsyncTestCase as TornadoAsyncTestCase
from zmq.eventloop.ioloop import ZMQIOLoop

class AsyncTestCase(TornadoAsyncTestCase):
    """Test case subclass with some common idioms for our tests."""

    def get_new_ioloop(self):
        """Return a ZMQ-compatible I/O loop so that we can use `ZMQStream`."""
        return ZMQIOLoop()

    def keep_checking(self, condition):
        """Perdiodically call *condition*, waiting for it to be true
        eventually. Note that one still has to call `self.wait()` after this
        method.

        """
        if condition():
            self.stop()
        else:
            self.io_loop.call_later(0.1, self.keep_checking, condition)
