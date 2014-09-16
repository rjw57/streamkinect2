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
    def __init__(self, io_loop=None):
        self.io_loop = io_loop or IOLoop.instance()
        self.records = {}
        self.client_kinects = {}
        self.report_callback = PeriodicCallback(self._report, 1000, self.io_loop)
        self.report_callback.start()

    def on_depth_frame(self, client, depth_frame, kinect_id):
        self.records[kinect_id]['count'] += 1

    def on_add_kinect(self, client, kinect_id):
        client.on_depth_frame.connect(self.on_depth_frame, sender=client)

        log.info('Enabling depth streaming on kinect "{0}"'.format(kinect_id))
        client.enable_depth_frames(kinect_id)

        self.records[kinect_id] = { 'start': time.time(), 'count': 0, }
        self.client_kinects[client].add(kinect_id)

    def on_remove_kinect(self, client, kinect_id):
        log.info('Kinect {0} went away'.format(kinect_id))
        self.client_kinects[client].remove(kinect_id)
        del self.records[kinect_id]

    def new_client(self, client, io_loop):
        """Called when a new client has been created. Enable depth streaming on all
        devices and benchmark result."""

        self.client_kinects[client] = set()

        # Register interest in devices
        client.on_add_kinect.connect(self.on_add_kinect, sender=client)
        client.on_remove_kinect.connect(self.on_remove_kinect, sender=client)

    def removed_client(self, client, io_loop):
        """Called when a new client has been created. Enable depth streaming on all
        devices and benchmark result."""

        for kin_id in self.client_kinects[client]:
            del self.records[kin_id]

        del self.client_kinects[client]

        # Register disinterest in devices
        client.on_add_kinect.disconnect(self.on_add_kinect, sender=client)
        client.on_remove_kinect.disconnect(self.on_remove_kinect, sender=client)

    def _report(self):
        now = time.time()
        for k, v in self.records.items():
            delta = now - v['start']
            log.info('Kinect "{0}", {1} frames in {2:.0f} seconds => {3:1f} fps'.format(
                k, v['count'], delta, v['count']/delta))

# Our listening class
class Listener(object):
    def __init__(self, browser, benchmark, io_loop = None):
        self.benchmark = benchmark

        self.io_loop = io_loop or IOLoop.instance()
        browser.on_add_server.connect(self.add_server, sender=browser)
        browser.on_remove_server.connect(self.remove_server, sender=browser)

        # Keep a reference to browser since we remain interested and do not
        # wish it garbage collected.
        self.browser = browser

        # Keep a list of clients for each server which appears
        self.clients = {}

    def add_server(self, browser, server_info):
        log.info('Discovered server "{0.name}" at "{0.endpoint}"'.format(server_info))
        client = Client(server_info.endpoint, connect_immediately=True)
        @client.on_disconnect.connect_via(client)
        def on_disconnect(_client, server_info=server_info, browser=browser):
            self.remove_server(browser, server_info)
        self.clients[server_info.name] = client
        self.benchmark.new_client(client, self.io_loop)

    def remove_server(self, browser, server_info):
        log.info('Server "{0.name}" at "{0.endpoint}" went away'.format(server_info))
        try:
            client = self.clients[server_info.name]
        except KeyError:
            # We didn't have a client for this server
            return
        self.benchmark.removed_client(client, self.io_loop)
        client.disconnect()
        del self.clients[server_info.name]

class IOLoopThread(threading.Thread):
    def run(self):
        # Create the server browser
        log.info('Creating server browser...')
        listener = Listener(ServerBrowser(), Benchmark())

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
