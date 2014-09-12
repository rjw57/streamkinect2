"""
Basic server support
"""

from logging import getLogger
from tornado.testing import AsyncTestCase
from zmq.eventloop.ioloop import ZMQIOLoop
from streamkinect2.server import Server
from streamkinect2.mock import MockKinect

log = getLogger(__name__)

def test_no_server_start():
    s = Server(start_immediately=False, address='127.0.0.1')
    assert not s.is_running

def test_server_start():
    s = Server(start_immediately=True, address='127.0.0.1')
    assert s.is_running
    s.stop()
    assert not s.is_running

def test_server_with_statement():
    s_copy = None
    with Server(address='127.0.0.1') as s:
        assert s.is_running
    assert not s.is_running

class TestServer(AsyncTestCase):
    def setUp(self):
        super(TestServer, self).setUp()
        self.server = Server(io_loop=self.io_loop, address='127.0.0.1')

    def tearDown(self):
        super(TestServer, self).tearDown()
        if self.server.is_running:
            self.server.stop()

    def test_adding_kinects_after_start(self):
        mock = MockKinect()
        with self.server:
            assert len(self.server.kinects) == 0
            self.server.add_kinect(mock)
            assert len(self.server.kinects) == 1
            assert self.server.kinects[0] is mock
            self.server.remove_kinect(mock)
            assert len(self.server.kinects) == 0

    def test_adding_kinects_before(self):
        mock = MockKinect()
        assert len(self.server.kinects) == 0
        self.server.add_kinect(mock)
        assert len(self.server.kinects) == 1
        assert self.server.kinects[0] is mock
        self.server.remove_kinect(mock)
        assert len(self.server.kinects) == 0

    # Use a ZMQ-compatible I/O loop so that we can use `ZMQStream`.
    def get_new_ioloop(self):
        return ZMQIOLoop()
