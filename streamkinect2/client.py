"""
Client
======
"""

from logging import getLogger

# Global logging object
log = getLogger(__name__)

class Client(object):
    """Client"""
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def ping(self):
        pass

