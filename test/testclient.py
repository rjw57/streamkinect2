"""
Test basic client
"""

from streamkinect2.client import Client
from streamkinect2.server import Server, EndpointType

class TestClient:
    def setup(self):
        # Start a server for this client
        self.server = Server(start_immediately=True)

    def teardown(self):
        self.server.stop()

    def test_ping(self):
        client = Client(self.server.endpoints[EndpointType.control])
        client.ping()
