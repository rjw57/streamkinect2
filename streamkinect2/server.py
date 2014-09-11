"""
Server
======
"""
from collections import namedtuple
import json
from logging import getLogger
import socket
import uuid
import weakref

import zeroconf
import zmq
from zmq.eventloop.zmqstream import ZMQStream

from .common import EndpointType

# Create our global zeroconf object
_ZC = zeroconf.Zeroconf()

# Our Zeroconf service type
_ZC_SERVICE_TYPE = '_kinect2._tcp.local.'

# Global logging object
log = getLogger(__name__)

class ServerInfo(namedtuple('ServerInfo', ['name', 'endpoint'])):
    """Kinect2 Stream server information.

    This is a subclass of the bultin :py:class:`tuple` class with named accessors
    for convenience. The tuple holds *name*, *endpoint* pairs.

    .. py:attribute:: name

        A server-provided human-readable name for the server.

    .. py:attribute:: endpoint

        Connection information for control channel which should be passed to
        :py:class:`streamkinect2.client.Client`.
    """

class Server(object):
    """A server capable of streaming Kinect2 data to interested clients.

    Servers may have their lifetime managed by using them within a ``with`` statement::

        with Server() as s:
            # server is running
            pass
        # server has stopped

    *address* and *port* are the bind address (as a decimal-dotted IP address)
    and port from which to start serving. If *port* is None, a random port is
    chosen. If *address* is '*None* then attempt to infer a sensible default.

    *name* should be some human-readable string describing the server. If
    *None* then a sensible default name is used.

    *zmq_ctx* should be the zmq context to create servers in. If *None*, then
    :py:meth:`zmq.Context.instance` is used to get the global instance.

    If not *None*, *io_loop* is the event loop to pass to
    :py:class:`zmq.eventloop.zmqstream.ZMQStream` used to communicate with the
    cleint. If *None* then global IO loop is used.

    .. py:attribute:: address

        The address bound to as a decimal-dotted string.

    .. py:attribute:: endpoints

        The zeromq endpoints for this server. A *dict*-like object keyed by
        endpoint type. (See :py:class:`streamkinect2.common.EndpointType`.)

    .. py:attribute:: is_running

        *True* when the server is running, *False* otherwise.

    """
    def __init__(self, address=None, start_immediately=False, name=None, zmq_ctx=None, io_loop=None):
        # Choose a unique name if none is specified
        if name is None:
            name = 'Kinect2 {0}'.format(uuid.uuid4())

        if address is None:
            address = _ZC.intf # Is this a private attribute?

        # Set public attributes
        self.is_running = False
        self.name = name
        self.address = address
        self.endpoints = {}

        # zmq streams for each endpoint
        self._streams = {}
        self._io_loop = io_loop

        if zmq_ctx is None:
            zmq_ctx = zmq.Context.instance()
        self._zmq_ctx = zmq_ctx

        if start_immediately:
            self.start()

    def __del__(self):
        if self.is_running:
            self.stop()

    def start(self):
        """Explicitly start the server. If the server is already running, this
        has no effect beyond logging a warning.

        """
        if self.is_running:
            log.warn('Server already running')
            return

        # Create zeromq sockets
        endpoints_to_create = [
            (zmq.REP, EndpointType.control),
            (zmq.PUB, EndpointType.depth),
        ]
        for type, key in endpoints_to_create:
            self._streams[key], self.endpoints[key] = self._create_and_bind_socket(type)

        # Listen for incoming messages
        self._streams[EndpointType.control].on_recv(self._control_recv)

        # Use the control endpoint's port as the port to advertise on zeroconf
        control_port = int(self.endpoints[EndpointType.control].split(':')[2])

        # Create a Zeroconf service info for ourselves
        self._zc_info = zeroconf.ServiceInfo(_ZC_SERVICE_TYPE,
            '.'.join((self.name, _ZC_SERVICE_TYPE)),
            address=socket.inet_aton(self.address), port=control_port,
            properties={})

        # register ourselves with zeroconf
        log.info('Registering server "{0}" with Zeroconf'.format(self.name))
        _ZC.registerService(self._zc_info)

        self.is_running = True

    def stop(self):
        """Explicitly stop the server. If the server is not running this has no
        effect beyond logging a warning.

        """
        if not self.is_running:
            log.warn('Server already stopped')
            return

        # unregister ourselves with zeroconf
        log.info('Unregistering server "{0}" with Zeroconf'.format(self.name))
        _ZC.unregisterService(self._zc_info)

        # close the sockets
        for s in self._streams.values():
            s.socket.close()
        self._streams = {}

        self.is_running = False

    def _handle_control(self, type, payload):
        """Handle a control message. Return a pair giving the type and payload of the response."""

        if type == 'ping':
            return 'pong', None
        else:
            return 'error', { 'message': 'Unknown message type "{0}"'.format(type) }

    def _create_and_bind_socket(self, type):
        """Create and bind a socket of the specified type. Returns the ZMQStream
        and endpoint address.

        """
        socket = self._zmq_ctx.socket(type)
        port = socket.bind_to_random_port('tcp://{0}'.format(self.address))
        return ZMQStream(socket, self._io_loop), 'tcp://{0}:{1}'.format(self.address, port)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()

    def _control_recv(self, msg):
        # Read JSON message
        try:
            msg = json.loads((b''.join(msg)).decode('utf8'))
        except ValueError:
            log.warn('Server ignoring invalid control packet')
            return

        # Check packet has required fields
        if 'seq' not in msg:
            log.warn('Server ignoring control packet lacking sequence number')
            return
        if 'type' not in msg:
            log.warn('Server ignoring control packet lacking type')
            return

        seq, type = msg['seq'], msg['type']
        payload = msg['payload'] if 'payload' in msg else None

        # Handle control packet and receive response type and payload
        r_type, r_payload = self._handle_control(type, payload)

        # Send response
        self._streams[EndpointType.control].send_json(
            { 'seq': seq, 'type': r_type, 'payload': r_payload }
        )

class ServerBrowser(object):
    """An object which listens for kinect2 streaming servers on the network.
    The object will keep listening as long as it is alive and so if you want to
    continue to receive notification of servers, you should keep it around.

    *listener* is an object which should have two methods which both take a
    single :py:class:`ServerInfo` instance as their only argument. The methods
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

            # Form control endpoint address
            endpoint = 'tcp://{0}:{1}'.format(address, port)
            info = ServerInfo(name=short_name, endpoint=endpoint)

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
