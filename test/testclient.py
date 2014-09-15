"""
Test basic client
"""
from logging import getLogger

from nose.tools import raises

from streamkinect2.client import Client
from streamkinect2.server import Server
from streamkinect2.common import EndpointType
from streamkinect2.mock import MockKinect

from .util import AsyncTestCase

log = getLogger(__name__)

class TestClientConnection(AsyncTestCase):
    def setUp(self):
        super(TestClientConnection, self).setUp()

        # Start a server for this client
        self.server = Server(address='127.0.0.1',
                start_immediately=True, io_loop=self.io_loop, announce=False)
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

class TestBasicClient(AsyncTestCase):
    def setUp(self):
        super(TestBasicClient, self).setUp()

        # Start a server for this client
        self.server = Server(address='127.0.0.1',
            start_immediately=True, io_loop=self.io_loop, announce=False)

        # Start the client. Use a fast heartbeat to make testing quick
        control_endpoint = self.server.endpoints[EndpointType.control]
        log.info('Started server with control endpoint: {0}'.format(control_endpoint))
        self.client = Client(control_endpoint,
                connect_immediately=True, io_loop=self.io_loop,
                heartbeat_period=250)

    def tearDown(self):
        super(TestBasicClient, self).tearDown()

        self.client.disconnect()
        self.server.stop()

    def test_control_endpoint(self):
        control_endpoint = self.server.endpoints[EndpointType.control]
        log.info('Testing client control endpoint {0} matches server endpoint {1}'.format(
            self.client.endpoints[EndpointType.control], control_endpoint))
        assert self.client.endpoints[EndpointType.control] == control_endpoint

    def test_device_before_connect(self):
        self.server.add_kinect(MockKinect())
        self.keep_checking(lambda: len(self.client.kinect_ids) == 1)
        self.wait()

    def test_device_after_connect_heartbeat(self):
        self.keep_checking(lambda: self.client.server_name is not None)
        self.wait()

        self.server.add_kinect(MockKinect())

        self.keep_checking(lambda: len(self.client.kinect_ids) == 1)
        self.wait()

    def test_add_signal_device_after_connect(self):
        self.keep_checking(lambda: self.client.server_name is not None)
        self.wait()

        k = MockKinect()

        state = { 'n_kinect_added': 0, 'n_kinect_removed': 0 }

        @self.client.on_add_kinect.connect_via(self.client)
        def on_add(client, kinect_id):
            log.info('Add kinect {0}'.format(kinect_id))
            assert kinect_id == k.unique_kinect_id
            state['n_kinect_added'] += 1

        @self.client.on_remove_kinect.connect_via(self.client)
        def on_add(client, kinect_id):
            log.info('Remove kinect {0}'.format(kinect_id))
            assert kinect_id == k.unique_kinect_id
            state['n_kinect_removed'] += 1

        self.server.add_kinect(k)
        self.keep_checking(lambda: state['n_kinect_added'] == 1)
        self.wait()

        self.server.remove_kinect(k)
        self.keep_checking(lambda: state['n_kinect_removed'] == 1)
        self.wait()

    def test_server_name(self):
        def condition():
            return self.client.server_name == self.server.name

        self.keep_checking(condition)
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

        for _ in range(state['n_pings']):
            self.client.ping(pong)

        self.keep_checking(lambda: state['n_pongs'] == state['n_pings'])
        self.wait()

    @raises(ValueError)
    def test_cannot_receive_depth_frames_from_bad_device(self):
        k = MockKinect()
        self.client.enable_depth_frames(k.unique_kinect_id)

    def test_receives_depth_frames(self):
        k = MockKinect()

        state = { 'n_depth_frames': 0 }
        @self.client.on_depth_frame.connect_via(self.client)
        def on_depth_frame(client, depth_frame, kinect_id):
            assert k.unique_kinect_id == kinect_id
            state['n_depth_frames'] += 1

        @self.client.on_add_kinect.connect_via(self.client)
        def on_add_kinect(client, kinect_id):
            assert client == self.client
            assert kinect_id == k.unique_kinect_id
            client.enable_depth_frames(kinect_id)

        with k:
            self.server.add_kinect(k)
            self.keep_checking(lambda: state['n_depth_frames'] > 1)
            self.wait()
