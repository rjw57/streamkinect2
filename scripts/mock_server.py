#!/usr/bin/env python
"""
Simple server using the mock Kinect.

"""
import logging

from streamkinect2.server import Server

# Install the zmq ioloop
from zmq.eventloop import ioloop
ioloop.install()

# Get our logger
log = logging.getLogger(__name__)

def main():
    # Set log level
    logging.basicConfig(level=logging.INFO)

    # Create the server
    log.info('Creating server')
    with Server():
        try:
            # Run the ioloop
            log.info('Running server...')
            ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            log.info('Keyboard interrupt received')
    log.info('Stopping')

if __name__ == '__main__':
    main()
