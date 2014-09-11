"""
Test basic client
"""

from tornado.testing import AsyncTestCase
from zmq.eventloop.ioloop import ZMQIOLoop

from streamkinect2.client import Client
from streamkinect2.server import Server, EndpointType

class TestClient(AsyncTestCase):
    def setUp(self):
        # Start a server for this client
        self.server = Server(start_immediately=True)

    def tearDown(self):
        self.server.stop()

    def test_control_endpoint(self):
        control_endpoint = self.server.endpoints[EndpointType.control]
        client = Client(control_endpoint)
        assert client.endpoints[EndpointType.control] == control_endpoint

    def test_ping(self):
        client = Client(self.server.endpoints[EndpointType.control])
        client.ping()

    # Use a ZMQ-compatible I/O loop so that we can use `ZMQStream`.
    def get_new_ioloop(self):
        return ZMQIOLoop()
