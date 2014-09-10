from collections import namedtuple
import json
from logging import getLogger
import socket
import uuid

import zeroconf

# Create our global zeroconf object
_ZC = zeroconf.Zeroconf()

# Our Zeroconf service type
_ZC_SERVICE_TYPE = '_kinect2._tcp.local.'

# Global logging object
log = getLogger(__name__)

ServerInfo = namedtuple('ServiceInfo', ['name', 'endpoint'])
ServerInfo.__doc__ = """Kinect2 Stream server information.

.. :py:attribute:: name
    Server-provided name

.. :py:attribute:: endpoint
    ZeroMQ endpoint for this server

"""

class _ZeroconfListener(object):
    def __init__(self, listener):
        self.listener = listener

        # List of ServerInfo records keyed by FQDN
        self._servers = { }

    def addService(self, zeroconf, type, name):
        # Skip types we don't know about
        if type != _ZC_SERVICE_TYPE:
            return
        assert name.endswith('.' + _ZC_SERVICE_TYPE)

        log.info('Service discovered: {0}'.format(name))
        short_name = name[:-(len(_ZC_SERVICE_TYPE)+1)]

        info = ServerInfo(name=short_name, endpoint='foo')
        self._servers[name] = info
        self.listener.add_server(info)

    def removeService(self, zeroconf, type, name):
        # Skip types we don't know about
        if type != _ZC_SERVICE_TYPE:
            return

        log.info('Service removed: {0}'.format(name))

        try:
            info = self._servers[name]
            del self._servers[name]
            self.listener.remove_server(info)
        except KeyError:
            log.warn('Ignoring server which we know nothing about')

    def _addedServer(self, name, info):
        for l in self._listeners:
            l.addServer(info)

    def _removedServer(Self, name, info):
        for l in self._listeners:
            l.removeServer(info)

def new_server_browser(listener):
    return zeroconf.ServiceBrowser(_ZC, _ZC_SERVICE_TYPE, _ZeroconfListener(listener))

class Server(object):
    def __init__(self, start_immediately=True, name=None):
        # Choose a unique name if none is specified
        if name is None:
            name = 'Kinect2 {0}'.format(uuid.uuid4())

        # Set public attributes
        self.name = name

        properties = { }

        # Create a Zeroconf service info for ourselves
        self._zc_info = zeroconf.ServiceInfo(_ZC_SERVICE_TYPE,
            '.'.join((self.name, _ZC_SERVICE_TYPE)),
            socket.inet_aton("10.0.1.2"), 1234,
            properties=json.dumps(properties).encode('utf8'))

        if start_immediately:
            self.start()

    def start(self):
        # register ourselves with zeroconf
        log.info('Registering server "{0}" with Zeroconf'.format(self.name))
        _ZC.registerService(self._zc_info)

    def stop(self):
        # unregister ourselves with zeroconf
        log.info('Unregistering server "{0}" with Zeroconf'.format(self.name))
        _ZC.unregisterService(self._zc_info)
