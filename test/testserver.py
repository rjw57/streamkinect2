"""
Basic server support
"""

from logging import getLogger
from streamkinect2 import Server

log = getLogger(__name__)

def test_no_server_start():
    s = Server(start_immediately=False)
    assert not s.is_running

def test_server_start():
    s = Server()
    assert s.is_running
    s.stop()
    assert not s.is_running
