"""
Test ZeroConf service discovery.

"""
from logging import getLogger
from streamkinect2.server import Server, ServerBrowser
from streamkinect2.common import EndpointType
from .util import TestListener, wait_for_server_add, wait_for_server_remove

log = getLogger(__name__)

def test_discovery_before_creation():
    listener = TestListener()
    browser = ServerBrowser(listener)

    with Server() as server:
        log.info('Created server "{0}"'.format(server.name))

        assert wait_for_server_add(listener, server.name)

        for s in listener.servers:
            if s.name == server.name:
                log.info('Discovered server has endpoint {0} which should be {1}'.format(
                    s.endpoint, server.endpoints[EndpointType.control]))
                assert s.endpoint == server.endpoints[EndpointType.control]

    assert wait_for_server_remove(listener, server.name)

def test_discovery_after_creation():
    with Server() as server:
        log.info('Created server "{0}"'.format(server.name))

        listener = TestListener()
        browser = ServerBrowser(listener)

        assert wait_for_server_add(listener, server.name)

        for s in listener.servers:
            if s.name == server.name:
                log.info('Discovered server has endpoint {0} which should be {1}'.format(
                    s.endpoint, server.endpoints[EndpointType.control]))
                assert s.endpoint == server.endpoints[EndpointType.control]

    assert wait_for_server_remove(listener, server.name)
