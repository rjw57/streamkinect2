"""
Test basic client
"""

from streamkinect2.client import Client
from streamkinect2.server import Server

class TestClient:
    def setup(self):
        # Start a server for this client
        self.server = Server()

    def test_ping(self):
        client = Client(self.server.endpoint)
        client.ping()
