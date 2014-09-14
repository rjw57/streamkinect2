"""
Server
======
"""
from collections import namedtuple
from logging import getLogger
import socket
import uuid
import weakref

from blinker import Signal
from tornado.ioloop import IOLoop
import zeroconf
import zmq
from zmq.eventloop.zmqstream import ZMQStream

from .common import EndpointType, MessageType, make_msg, parse_msg
from .compress import DepthFrameCompressor

# Global zeroconf object pool keyed by bind address
_ZC_POOL = {}
def _get_zeroconf(bindaddress):
    try:
        return _ZC_POOL[bindaddress]
    except KeyError:
        _ZC_POOL[bindaddress] = zeroconf.Zeroconf(bindaddress)
        return _ZC_POOL[bindaddress]

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

class _KinectRecord(namedtuple('_KinectRecord',
        ['kinect', 'endpoints', 'streams', 'depth_compresser'])):
    pass

class Server(object):
    """A server capable of streaming Kinect2 data to interested clients.

    Servers may have their lifetime managed by using them within a ``with`` statement::

        with Server() as s:
            # server is running
            pass
        # server has stopped

    *address* and *port* are the bind address (as a decimal-dotted IP address)
    and port from which to start serving. If *port* is None, a random port is
    chosen. If *address* is *None* then attempt to infer a sensible default.

    *name* should be some human-readable string describing the server. If
    *None* then a sensible default name is used.

    *zmq_ctx* should be the zmq context to create servers in. If *None*, then
    :py:meth:`zmq.Context.instance` is used to get the global instance.

    If not *None*, *io_loop* is the event loop to pass to
    :py:class:`zmq.eventloop.zmqstream.ZMQStream` used to communicate with the
    cleint. If *None* then global IOLoop instance is used.

    If *announce* is True then the server will be announced over ZeroConf when
    it starts running.

    .. py:attribute:: address

        The address bound to as a decimal-dotted string.

    .. py:attribute:: endpoints

        The zeromq endpoints for this server. A *dict*-like object keyed by
        endpoint type. (See :py:class:`streamkinect2.common.EndpointType`.)

    .. py:attribute:: is_running

        *True* when the server is running, *False* otherwise.

    .. py:attribute:: kinects

        :py:class:`list` of kinect devices managed by this server. See :py:meth:`add_kinect`.

    """
    def __init__(self, address=None, start_immediately=False,
            name=None, zmq_ctx=None, io_loop=None, announce=True):
        # Choose a sensible name if none is specified
        if name is None:
            import getpass
            import platform
            name = 'Kinect {0}'.format(uuid.uuid4())

        # Get a zeroconf instance appropriate to the bind address
        self._zc = _get_zeroconf(address)
        if address is None:
            address = self._zc.intf # Is this a private attribute?

        # Set public attributes
        self.is_running = False
        self.name = name
        self.address = address
        self.endpoints = {}

        self._announce = announce

        # zmq streams for each endpoint
        self._streams = {}
        self._io_loop = io_loop

        # kinects which we manage. Keyed by device id.
        self._kinects = { }

        if zmq_ctx is None:
            zmq_ctx = zmq.Context.instance()
        self._zmq_ctx = zmq_ctx

        if start_immediately:
            self.start()

    def __del__(self):
        if self.is_running:
            self.stop()

    def add_kinect(self, kinect):
        """Add a Kinect device to this server. *kinect* should be a object
        implementing the same interface as
        :py:class:`streamkinect2.mock.MockKinect`.

        """
        endpoints, streams = {}, {}

        # Create zeromq sockets
        endpoints_to_create = [
            (zmq.PUB, EndpointType.depth),
        ]
        for type, key in endpoints_to_create:
            streams[key], endpoints[key] = self._create_and_bind_socket(type)

        depth_compresser = DepthFrameCompressor(kinect, io_loop=self._io_loop)
        self._kinects[kinect.unique_kinect_id] = _KinectRecord(kinect, endpoints,
                streams, depth_compresser)

        # Register our interest in compressed frames
        DepthFrameCompressor.on_compressed_frame.connect(
                self._on_compressed_frame, sender=depth_compresser)

    def remove_kinect(self, kinect):
        """Remove a Kinect device previously added via :py:meth:`add_kinect`."""
        # Find this kinect's record
        record = self._kinects[kinect.unique_kinect_id]

        # Remove it from the list
        del self._kinects[kinect.unique_kinect_id]

        # Disconnect signal handlers
        DepthFrameCompressor.on_compressed_frame.disconnect(
                self._on_compressed_frame, sender=record.depth_compresser)

    @property
    def kinects(self):
        # Return a list rather than exposing the fact that we store kinects in
        # a set.
        return list(k.kinect for k in self._kinects.values())

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
        ]
        for type, key in endpoints_to_create:
            self._streams[key], self.endpoints[key] = self._create_and_bind_socket(type)

        # Listen for incoming messages
        self._streams[EndpointType.control].on_recv_stream(self._control_recv)

        # Use the control endpoint's port as the port to advertise on zeroconf
        control_port = int(self.endpoints[EndpointType.control].split(':')[2])

        # Create a Zeroconf service info for ourselves
        self._zc_info = zeroconf.ServiceInfo(_ZC_SERVICE_TYPE,
            '.'.join((self.name, _ZC_SERVICE_TYPE)),
            address=socket.inet_aton(self.address), port=control_port,
            properties={})

        if self._announce:
            # register ourselves with zeroconf
            log.info('Registering server "{0}" with Zeroconf'.format(self.name))
            self._zc.registerService(self._zc_info)

        self.is_running = True

    def stop(self):
        """Explicitly stop the server. If the server is not running this has no
        effect beyond logging a warning.

        """
        if not self.is_running:
            log.warn('Server already stopped')
            return

        if self._announce:
            # unregister ourselves with zeroconf
            log.info('Unregistering server "{0}" with Zeroconf'.format(self.name))
            self._zc.unregisterService(self._zc_info)

        # close the sockets
        for s in self._streams.values():
            s.socket.close()
        self._streams = {}

        self.is_running = False

    def _current_me(self):
        devices = []
        for device in self._kinects.values():
            devices.append({
                'id': device.kinect.unique_kinect_id,
                'endpoints': dict((k.name, v) for k, v in device.endpoints.items()),
            })

        return {
            'version': 1,
            'name': self.name,
            'endpoints': dict((k.name, v) for k, v in self.endpoints.items()),
            'devices': devices,
        }

    def _handle_control(self, type, payload):
        """Handle a control message. Return a pair giving the type and payload of the response."""

        if type == MessageType.ping:
            log.info('Got ping from client')
            return MessageType.pong, None
        elif type == MessageType.who:
            return MessageType.me, self._current_me()
        else:
            log.warn('Unknown message type from client: "{0}"'.format(type))
            return MessageType.error, {
                'code': 400, 'reason': 'Unknown message type "{0}"'.format(type)
            }

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

    def _control_recv(self, stream, msg):
        # Read message
        try:
            type, payload = parse_msg(msg)
        except ValueError as e:
            stream.send_multipart(make_msg(MessageType.error, {
                'code': 400,
                'reason': str(e),
            }))
            log.warn('Server received a bad message: {0}'.format(e))
            return

        # Handle control packet and receive response type and payload
        r_type, r_payload = self._handle_control(type, payload)

        # Send response
        stream.send_multipart(make_msg(r_type, r_payload))

    def _on_compressed_frame(self, depth_compresser, compressed_frame):
        kinect_id = depth_compresser.kinect.unique_kinect_id
        try:
            record = self._kinects[kinect_id]
        except KeyError:
            log.warn('Got depth from from unknown kinect "{0}"'.format(kinect_id))

        # Send data to clients
        stream = record.streams[EndpointType.depth]
        stream.send(compressed_frame)
        stream.flush()

class ServerBrowser(object):
    """An object which listens for kinect2 streaming servers on the network.
    The object will keep listening as long as it is alive and so if you want to
    continue to receive notification of servers, you should keep it around.

    *io_loop* is an instance of :py:class:`tornado.ioloop.IOLoop` which should
    be used to schedule sending signals. If *None* then the global instance is
    used. This is needed because server discovery happens on a separate thread
    to the tornado event loop which is used for the rest of the network
    communication. Hence, when a server is discovered, the browser co-ordinates
    with the event loop to call the :py:meth:`add_server` and
    :py:meth:`remove_server` methods on the main IOLoop thread.

    *address* is an explicit bind IP address for an interface to listen on as a
    decimal-dotted string or *None* to use the default.

    """
    on_add_server = Signal()
    """Signal emitted when a new server is discovered on the network. Receivers
    should take a single keyword argument, *server_info*, which will be an
    instance of :py:class:`ServerInfo` describing the server."""

    on_remove_server = Signal()
    """Signal emitted when a server removes itself from the network. Receivers
    should take a single keyword argument, *server_info*, which will be an
    instance of :py:class:`ServerInfo` describing the server."""

    def __init__(self, io_loop=None, address=None):
        self._io_loop = io_loop or IOLoop.instance()

        # A browser. Note the use of a weak reference to us.
        self._browser = zeroconf.ServiceBrowser(_get_zeroconf(address),
                _ZC_SERVICE_TYPE, ServerBrowser._Listener(weakref.ref(self)))

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
            browser._io_loop.add_callback(
                    browser.on_add_server.send, browser, server_info=info)

        def removeService(self, zeroconf, type, name):
            browser = self.browser_ref()
            if browser is None:
                return

            # Skip types we don't know about
            if type != _ZC_SERVICE_TYPE:
                return  # pragma: no cover

            log.info('Service removed: {0}'.format(name))

            try:
                info = self._servers[name]
                del self._servers[name]
                browser._io_loop.add_callback(
                        browser.on_remove_server.send, browser, server_info=info)
            except KeyError: # pragma: no cover
                log.warn('Ignoring server which we know nothing about')
