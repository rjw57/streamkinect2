#!/usr/bin/env python
"""
Simple client which pings each server as it is discovered.

"""
import logging
import threading

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
    def __init__(self, browser, io_loop = None):
        self.clients = {}
        self.io_loop = io_loop or IOLoop.instance()
        browser.on_add_server.connect(self.add_server, sender=browser)
        browser.on_remove_server.connect(self.remove_server, sender=browser)

        # Keep a reference to browser since we remain interested and do not
        # wish it garbage collected.
        self.browser = browser

    def add_server(self, browser, server_info):
        log.info('Discovered server "{0.name}" at "{0.endpoint}"'.format(server_info))

        client = Client(server_info.endpoint, connect_immediately=True)
        self.clients[server_info.endpoint] = client

        def pong(server_info=server_info):
            log.info('Got pong from "{0.name}"'.format(server_info))
            self.clients[server_info.endpoint].disconnect()
            del self.clients[server_info.endpoint]

        log.info('Pinging server "{0.name}"...'.format(server_info))
        client.ping(pong)

    def remove_server(self, browser, server_info):
        log.info('Server "{0.name}" at "{0.endpoint}" went away'.format(server_info))

class IOLoopThread(threading.Thread):
    def run(self):
        # Create the server browser
        log.info('Creating server browser...')
        listener = Listener(ServerBrowser())

        # Run the ioloop
        log.info('Running...')
        ioloop.IOLoop.instance().start()

        log.info('Stopping')

    def stop(self):
        io_loop = ioloop.IOLoop.instance()
        io_loop.add_callback(io_loop.stop)
        self.join(3)

def main():
    # Set log level
    logging.basicConfig(level=logging.INFO)

    print('=============================================')
    print('Press Enter to exit')
    print('=============================================')

    # Start the event loop
    ioloop_thread = IOLoopThread()
    ioloop_thread.start()

    # Wait for input
    input()

    # Stop thread
    ioloop_thread.stop()

if __name__ == '__main__':
    main()
