"""
Test ZeroConf service discovery.

"""
from logging import getLogger
import streamkinect2
from .util import TestListener, wait_for_server_add, wait_for_server_remove

log = getLogger(__name__)

def test_discovery_before_creation():
    listener = TestListener()
    browser = streamkinect2.ServerBrowser(listener)

    server = streamkinect2.Server()
    log.info('Created server "{0}"'.format(server.name))

    assert wait_for_server_add(listener, server.name)

    for s in listener.servers:
        if s.name == server.name:
            log.info('Discovered server has endpoint {0} which should be {1}'.format(
                s.endpoint, server.endpoint))
            assert s.endpoint == server.endpoint

    server.stop()
    assert wait_for_server_remove(listener, server.name)

def test_discovery_after_creation():
    server = streamkinect2.Server()
    log.info('Created server "{0}"'.format(server.name))

    listener = TestListener()
    browser = streamkinect2.ServerBrowser(listener)

    assert wait_for_server_add(listener, server.name)

    for s in listener.servers:
        if s.name == server.name:
            log.info('Discovered server has endpoint {0} which should be {1}'.format(
                s.endpoint, server.endpoint))
            assert s.endpoint == server.endpoint

    server.stop()
    assert wait_for_server_remove(listener, server.name)
