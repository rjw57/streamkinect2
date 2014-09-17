#!/usr/bin/env python
"""
Simple benchmark of how fast depth frames are delivered.

"""
import logging
import threading
import time

from tornado.ioloop import IOLoop, PeriodicCallback
from streamkinect2.server import ServerBrowser
from streamkinect2.client import Client

# Install the zmq ioloop
from zmq.eventloop import ioloop
ioloop.install()

# Get our logger
log = logging.getLogger(__name__)

class Benchmark(object):
    def __init__(self, client, kinect_id, io_loop=None):
        self.client = client
        self.kinect_id = kinect_id
        self.io_loop = io_loop or IOLoop.instance()

        self.count = 0
        self.start = time.time()

        # Enable depth streaming
        Client.on_depth_frame.connect(self.on_depth_frame, sender=self.client)
        self.client.enable_depth_frames(self.kinect_id)

        self.report_callback = PeriodicCallback(self._report, 1000, self.io_loop)
        self.report_callback.start()

    def shutdown(self):
        self.report_callback.stop()

    def on_depth_frame(self, client, depth_frame, kinect_id):
        if self.client is not client or kinect_id != self.kinect_id:
            return
        self.count += 1

    def _report(self):
        now = time.time()
        delta = now - self.start
        log.info('Kinect "{0}", {1} frames in {2:.0f} seconds => {3:1f} fps'.format(
            self.kinect_id, self.count, delta, self.count/delta))

class ClientWrapper(object):
    def __init__(self, client, io_loop=None):
        self.client = client
        self.io_loop = io_loop or ioloop.IOLoop.instance()

        # Set of benchmark objects keyed by kinect id
        self.benchmarks = { }

        Client.on_add_kinect.connect(self.on_add_kinect, sender=client)
        Client.on_remove_kinect.connect(self.on_remove_kinect, sender=client)

    def shutdown(self):
        for b in self.benchmarks.values():
            b.shutdown()
        self.benchmarks = { }

    def on_add_kinect(self, client, kinect_id):
        log.info('"{0}" added kinect "{1}"'.format(client.server_name, kinect_id))
        self.benchmarks[kinect_id] = Benchmark(client, kinect_id, self.io_loop)

    def on_remove_kinect(self, client, kinect_id):
        log.info('"{0}" removed kinect "{1}"'.format(client.server_name, kinect_id))
        if kinect_id in self.benchmarks:
            del self.benchmarks[kinect_id]

class IOLoopThread(threading.Thread):
    def __init__(self):
        super(IOLoopThread, self).__init__()

        # A map of ClientWrapper, endpoint pairs indexed by client
        self.clients = { }

        # A set of server endpoints which we've discovered
        self.endpoints = set()

    def run(self):
        log.info('Creating server browser...')

        # Create the server browser and wire up event handlers
        browser = ServerBrowser()
        ServerBrowser.on_add_server.connect(self.on_add_server, sender=browser)
        ServerBrowser.on_remove_server.connect(self.on_remove_server, sender=browser)

        # Periodic callback checking for servers on the network we don't have clients for
        server_check_cb = PeriodicCallback(self.check_servers, 5000)
        server_check_cb.start()

        # Run the ioloop
        log.info('Running...')
        ioloop.IOLoop.instance().start()
        log.info('Stopping')

    def stop(self):
        io_loop = ioloop.IOLoop.instance()
        io_loop.add_callback(io_loop.stop)
        self.join(3)

    def check_servers(self):
        # Form a set of endpoints which have clients
        current_endpoints = set(x[1] for x in self.clients.values())

        # Any endpoints left over?
        for ep in self.endpoints.difference(current_endpoints):
            log.info('Attempting connect to {0} which Zeroconf still advertises'.format(ep))
            self.connect_to_server(ep)

    def on_add_server(self, browser, server_info):
        log.info('Discovered server "{0.name}" at "{0.endpoint}"'.format(server_info))
        self.connect_to_server(server_info.endpoint)

    def connect_to_server(self, endpoint):
        # Create, wire up, remember and connect the client
        client = Client(endpoint)
        Client.on_disconnect.connect(self.on_client_disconnect, sender=client)
        self.clients[client] = (ClientWrapper(client), endpoint)
        client.connect()

        self.endpoints.add(endpoint)

    def on_remove_server(self, browser, server_info):
        log.info('Server "{0.name}" at "{0.endpoint}" went away'.format(server_info))
        if server_info.endpoint in self.endpoints:
            self.endpoints.remove(server_info.endpoint)

    def on_client_disconnect(self, client):
        if client not in self.clients:
            return
        log.info('Client for "{0}" disconnected'.format(client.server_name))
        self.clients[client][0].shutdown()
        del self.clients[client]

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
