#!/usr/bin/env python
"""
Simple client which pings each server as it is discovered.

"""
import logging

from tornado.ioloop import IOLoop
from streamkinect2.server import ServerBrowser
from streamkinect2.client import Client

# Install the zmq ioloop
from zmq.eventloop import ioloop
ioloop.install()

# Get our logger
log = logging.getLogger(__name__)

# Our listening class
class Listener(object):
    def __init__(self, io_loop = None):
        self.clients = {}
        self.io_loop = io_loop or IOLoop.instance()

    def add_server(self, server_info):
        log.info('Discovered server "{0.name}" at "{0.endpoint}"'.format(server_info))

        client = Client(server_info.endpoint, connect_immediately=True)
        self.clients[server_info.endpoint] = client

        def pong(server_info=server_info):
            log.info('Got pong from "{0.name}"'.format(server_info))
            del self.clients[server_info.endpoint]

        log.info('Pinging server "{0.name}"...'.format(server_info))
        client.ping(pong)

    def remove_server(self, server_info):
        log.info('Server "{0.name}" at "{0.endpoint}" went away'.format(server_info))

def main():
    # Set log level
    logging.basicConfig(level=logging.INFO)

    # Create the server
    log.info('Creating server browser...')
    browser = ServerBrowser(Listener())

    log.info('Running event loop...')
    try:
        # Run the ioloop
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        log.info('Keyboard interrupt received')
    log.info('Stopping')

if __name__ == '__main__':
    main()

