"""
Server
======
"""
from collections import namedtuple
from logging import getLogger
import json
import socket
import uuid
import weakref

import zeroconf
import zmq

# Create our global zeroconf object
_ZC = zeroconf.Zeroconf()

# Our Zeroconf service type
_ZC_SERVICE_TYPE = '_kinect2._tcp.local.'

# Global logging object
log = getLogger(__name__)

ServerInfo = namedtuple('ServerInfo', ['name', 'endpoint'])
ServerInfo.__doc__ = """Kinect2 Stream server information.

This is a subclass of the bultin :py:class:`tuple` class with named accessors
for convenience. The tuple holds *name*, *endpoint* pairs. The *name* is the
server-provided human-readable name for the server. The *endpoint* contains
connection information which should be passed to
:py:class:`streamkinect2.client.Client`.
"""

class Server(object):
    """A server capable of streaming Kinect2 data to interested clients.

    *address* and *port* are the bind address (as a decimal-dotted IP address)
    and port from which to start serving. If *port* is None, a random port is
    chosen. If *address* is '*None* then attempt to infer a sensible default.

    *name* should be some human-readable string describing the server. If
    *None* then a sensible default name is used.

    .. py:attribute:: address

        The address bound to as a decimal-dotted string.

    .. py:attribute:: port

        The port bound to.

    .. py:attribute:: endpoint

        The zeromq endpoint address for this server.

    .. py:attribute:: is_running

        *True* when the server is running, *False* otherwise.

    """
    def __init__(self, address=None, port=None, start_immediately=True, name=None):
        # Choose a unique name if none is specified
        if name is None:
            name = 'Kinect2 {0}'.format(uuid.uuid4())

        if address is None:
            address = _ZC.intf # Is this a private attribute?

        # Create a zeromq socket
        ctx = zmq.Context.instance()
        self._socket = ctx.socket(zmq.PUB)
        if port is None:
            port = self._socket.bind_to_random_port('tcp://{0}'.format(address))
        else:
            self._socket.bind('tcp://{0}:{1}'.format(address, port))

        # Set public attributes
        self.name = name
        self.address = address
        self.port = port
        self.endpoint = 'tcp://{0}:{1}'.format(address, port)
        self.is_running = False

        properties = { 'endpoint': self.endpoint, }

        # Create a Zeroconf service info for ourselves
        self._zc_info = zeroconf.ServiceInfo(_ZC_SERVICE_TYPE,
            '.'.join((self.name, _ZC_SERVICE_TYPE)),
            address=socket.inet_aton(self.address), port=self.port,
            properties=json.dumps(properties).encode('utf8'))

        if start_immediately:
            self.start()

    def __del__(self):
        if self.is_running:
            self.stop()

    def start(self):
        # register ourselves with zeroconf
        log.info('Registering server "{0}" with Zeroconf'.format(self.name))
        _ZC.registerService(self._zc_info)

        self.is_running = True

    def stop(self):
        if self._socket.closed:
            log.error('Server already stopped')
            return

        # unregister ourselves with zeroconf
        log.info('Unregistering server "{0}" with Zeroconf'.format(self.name))
        _ZC.unregisterService(self._zc_info)

        # close the socket
        self._socket.close()

        self.is_running = False

class ServerBrowser(object):
    """An object which listens for kinect2 streaming servers on the network.
    The object will keep listening as long as it is alive and so if you want to
    continue to receive notification of servers, you should keep it around.

    *listener* is an object which should have two methods which both take a
    single py:class`ServerInfo` instance as their only argument. The methods
    should be called :py:meth:`add_server` and :py:meth:`remove_server` and,
    unsurprisingly, will be called when servers are added and removed from the
    network.

    """
    def __init__(self, listener):
        self.listener = listener

        # A browser. Note the use of a weak reference to us.
        self._browser = zeroconf.ServiceBrowser(_ZC, _ZC_SERVICE_TYPE,
                ServerBrowser._Listener(weakref.ref(self)))

    class _Listener(object):
        """Listen for ZeroConf service announcements. The browser object is
        kept as a weak reference so that we don't end up with circular references.

        """
        def __init__(self, browser_ref):
            self.browser_ref = browser_ref

            # List of ServerInfo records keyed by FQDN
            self._servers = { }

        def addService(self, zeroconf, type, name):
            browser = self.browser_ref()
            if browser is None:
                return
            listener = browser.listener

            # Skip types we don't know about
            if type != _ZC_SERVICE_TYPE:
                return  # pragma: no cover
            assert name.endswith('.' + _ZC_SERVICE_TYPE)

            log.info('Service discovered: {0}'.format(name))
            short_name = name[:-(len(_ZC_SERVICE_TYPE)+1)]

            zc_info = zeroconf.getServiceInfo(type, name)
            address = socket.inet_ntoa(zc_info.getAddress())
            port = zc_info.getPort()

            # Use endpoint from server if possible
            try:
                props = json.loads(zc_info.getText().decode('utf8'))
                endpoint = props['endpoint']
            except (ValueError, KeyError):
                log.warn('Server did not specify an endpoint. Guessing a sensible value.')
                endpoint = 'tcp://{0}:{1}'.format(address, port)

            info = ServerInfo(name=short_name, endpoint=props['endpoint'])

            self._servers[name] = info
            listener.add_server(info)

        def removeService(self, zeroconf, type, name):
            browser = self.browser_ref()
            if browser is None:
                return
            listener = browser.listener

            # Skip types we don't know about
            if type != _ZC_SERVICE_TYPE:
                return  # pragma: no cover

            log.info('Service removed: {0}'.format(name))

            try:
                info = self._servers[name]
                del self._servers[name]
                listener.remove_server(info)
            except KeyError: # pragma: no cover
                log.warn('Ignoring server which we know nothing about')
