"""
Test basic client
"""

import streamkinect2

class TestClient:
    def setup(self):
        # Start a server for this client
        self.server = streamkinect2.Server()

    def test_ping(self):
        client = streamkinect2.Client(self.server.endpoint)
        client.ping()
