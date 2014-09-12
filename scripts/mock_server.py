#!/usr/bin/env python
"""
Simple server using the mock Kinect.

"""
import logging
import threading

from streamkinect2.server import Server
from streamkinect2.mock import MockKinect

# Install the zmq ioloop
from zmq.eventloop import ioloop
ioloop.install()

# Get our logger
log = logging.getLogger(__name__)

class IOLoopThread(threading.Thread):
    def run(self):
        # Create the server
        log.info('Creating server')
        server = Server()

        # Add mock kinect device to server
        server.add_kinect(MockKinect())

        # With the server running...
        log.info('Running server...')
        with server:
            # Run the ioloop
            ioloop.IOLoop.instance().start()

        # The server has now stopped
        log.info('Stopped')

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
