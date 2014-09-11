"""
Test basic client
"""
from logging import getLogger

from nose.tools import raises
from tornado.testing import AsyncTestCase
from zmq.eventloop.ioloop import ZMQIOLoop

from streamkinect2.client import Client
from streamkinect2.server import Server
from streamkinect2.common import EndpointType

log = getLogger(__name__)

class TestClientConnection(AsyncTestCase):
    def setUp(self):
        super(TestClientConnection, self).setUp()

        # Start a server for this client
        self.server = Server(start_immediately=True, io_loop=self.io_loop)
        self.endpoint = self.server.endpoints[EndpointType.control]

    def tearDown(self):
        super(TestClientConnection, self).tearDown()
        self.server.stop()

    @raises(RuntimeError)
    def test_client_must_be_connected(self):
        client = Client(self.endpoint, io_loop=self.io_loop)
        client.ping()

    def test_client_with_statement(self):
        with Client(self.endpoint, io_loop=self.io_loop) as client:
            assert client.is_connected
        assert not client.is_connected

    def test_explicit_connect_disconnect(self):
        client = Client(self.endpoint, io_loop=self.io_loop)
        assert not client.is_connected
        client.connect()
        assert client.is_connected
        client.disconnect()
        assert not client.is_connected

    def test_immediate_connect(self):
        client = Client(self.endpoint, connect_immediately=True, io_loop=self.io_loop)
        assert client.is_connected
        client.disconnect()
        assert not client.is_connected

    # Use a ZMQ-compatible I/O loop so that we can use `ZMQStream`.
    def get_new_ioloop(self):
        return ZMQIOLoop()

class TestBasicClient(AsyncTestCase):
    def setUp(self):
        super(TestBasicClient, self).setUp()

        # Start a server for this client
        self.server = Server(start_immediately=True, io_loop=self.io_loop)

        # Start the client
        control_endpoint = self.server.endpoints[EndpointType.control]
        self.client = Client(control_endpoint,
                connect_immediately=True, io_loop=self.io_loop)

    def tearDown(self):
        super(TestBasicClient, self).tearDown()

        self.client.disconnect()
        self.server.stop()

    def test_control_endpoint(self):
        control_endpoint = self.server.endpoints[EndpointType.control]
        assert self.client.endpoints[EndpointType.control] == control_endpoint

    def test_ping(self):
        def pong():
            log.info('Got pong from server')
            self.stop(True)

        self.client.ping(pong)
        assert self.wait()

    def test_many_pings(self):
        state = { 'n_pings': 10, 'n_pongs': 0 }
        def pong():
            log.info('Got pong from server')
            state['n_pongs'] += 1
            if state['n_pings'] == state['n_pongs']:
                self.stop(True)

        for _ in range(state['n_pings']):
            self.client.ping(pong)

        assert self.wait()

    # Use a ZMQ-compatible I/O loop so that we can use `ZMQStream`.
    def get_new_ioloop(self):
        return ZMQIOLoop()
