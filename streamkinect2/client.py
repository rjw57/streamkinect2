"""
Client
======
"""

from logging import getLogger

import zmq
from zmq.eventloop.zmqstream import ZMQStream

from .server import EndpointType

# Global logging object
log = getLogger(__name__)

class Client(object):
    """Client"""
    def __init__(self, control_endpoint, zmq_ctx=None):
        if zmq_ctx is None:
            zmq_ctx = zmq.Context.instance()
        self._zmq_ctx = zmq_ctx

        self.endpoints = {
            EndpointType.control: control_endpoint
        }

        control_socket = self._zmq_ctx.socket(zmq.REQ)
        control_socket.connect(control_endpoint)

        self._sockets = {
            EndpointType.control: control_socket
        }

    def ping(self):
        pass

