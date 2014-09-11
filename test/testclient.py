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
from streamkinect2.mock import MockKinect

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

    def test_event_endpoint(self):
        event_endpoint = self.server.endpoints[EndpointType.event]

        def condition():
            try:
                client_event_endpoint = self.client.endpoints[EndpointType.event]
            except KeyError:
                return False
            return client_event_endpoint == event_endpoint

        def keep_checking():
            if condition():
                self.stop()
            else:
                self.io_loop.call_later(0.1, keep_checking)
        self.io_loop.add_callback(keep_checking)

        # Wait for client to discover the event endpoint
        self.wait()

    def test_device_before_connect(self):
        self.server.add_kinect(MockKinect())

        def condition():
            return len(self.client.kinect_ids) == 1

        def keep_checking():
            if condition():
                self.stop()
            else:
                self.io_loop.call_later(0.1, keep_checking)
        self.io_loop.add_callback(keep_checking)
        self.wait()

    def test_server_name(self):
        def condition():
            return self.client.server_name == self.server.name

        def keep_checking():
            if condition():
                self.stop()
            else:
                self.io_loop.call_later(0.1, keep_checking)
        self.io_loop.add_callback(keep_checking)

        # Wait for client
        self.wait()

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
