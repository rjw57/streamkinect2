#!/usr/bin/env python
"""
Simple server using the mock Kinect.

"""
import logging
import threading

from streamkinect2.server import Server

# Install the zmq ioloop
from zmq.eventloop import ioloop
ioloop.install()

# Get our logger
log = logging.getLogger(__name__)

class IOLoopThread(threading.Thread):
    def run(self):
        # Create the server
        log.info('Creating server')
        with Server():
            # Run the ioloop
            log.info('Running server...')
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
