"""
Test ZeroConf service discovery.

"""
from logging import getLogger
from tornado.testing import AsyncTestCase
from zmq.eventloop.ioloop import ZMQIOLoop
from streamkinect2.server import Server, ServerBrowser
from streamkinect2.common import EndpointType

log = getLogger(__name__)

class TestDiscovery(AsyncTestCase):
    class Listener(object):
        def __init__(self, browser):
            self.servers = set()
            browser.on_add_server.connect(self.add_server, sender=browser)
            browser.on_remove_server.connect(self.remove_server, sender=browser)

        def add_server(self, browser, server_info):
            log.info('Listener told to add server: {0}'.format(server_info))
            self.servers.add(server_info)

        def remove_server(self, browser, server_info):
            log.info('Listener told to remove server: {0}'.format(server_info))
            self.servers.remove(server_info)

    def wait_for_server_add(self, listener, name):
        def condition():
            for s in listener.servers:
                if s.name == name:
                    return True
            return False

        def keep_checking():
            if condition():
                self.stop()
            else:
                self.io_loop.call_later(0.1, keep_checking)
        self.io_loop.add_callback(keep_checking)
        self.wait(condition)

    def wait_for_server_remove(self, listener, name):
        def condition():
            for s in listener.servers:
                if s.name == name:
                    return False
            return True

        def keep_checking():
            if condition():
                self.stop()
            else:
                self.io_loop.call_later(0.1, keep_checking)
        self.io_loop.add_callback(keep_checking)
        self.wait(condition)

    def test_discovery_before_creation(self):
        browser = ServerBrowser(io_loop=self.io_loop)
        listener = TestDiscovery.Listener(browser)

        with Server(io_loop=self.io_loop, address='127.0.0.1') as server:
            log.info('Created server "{0}"'.format(server.name))

            self.wait_for_server_add(listener, server.name)

            for s in listener.servers:
                if s.name == server.name:
                    log.info('Discovered server has endpoint {0} which should be {1}'.format(
                        s.endpoint, server.endpoints[EndpointType.control]))
                    assert s.endpoint == server.endpoints[EndpointType.control]

        self.wait_for_server_remove(listener, server.name)

    def test_discovery_after_creation(self):
        with Server(io_loop=self.io_loop, address='127.0.0.1') as server:
            log.info('Created server "{0}"'.format(server.name))

            browser = ServerBrowser(io_loop=self.io_loop)
            listener = TestDiscovery.Listener(browser)

            self.wait_for_server_add(listener, server.name)

            for s in listener.servers:
                if s.name == server.name:
                    log.info('Discovered server has endpoint {0} which should be {1}'.format(
                        s.endpoint, server.endpoints[EndpointType.control]))
                    assert s.endpoint == server.endpoints[EndpointType.control]

        self.wait_for_server_remove(listener, server.name)

    # Use a ZMQ-compatible I/O loop so that we can use `ZMQStream`.
    def get_new_ioloop(self):
        return ZMQIOLoop()
