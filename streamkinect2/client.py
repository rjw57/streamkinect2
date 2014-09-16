"""
Client
======

"""
from collections import namedtuple, deque
from logging import getLogger
import functools

from blinker import Signal
import tornado.ioloop
import zmq
from zmq.eventloop.zmqstream import ZMQStream

from .common import EndpointType, ProtocolError, MessageType
from .common import make_msg, parse_msg

# Global logging object
log = getLogger(__name__)

class Client(object):
    """Client for a streaming kinect2 server.

    Usually the client will be used with a ``with`` statement::

        with Client(endpoint) as c:
            # c is connected here
            pass
        # c is disconnected here

    *control_endpoint* is the zeromq control endpoint for the server which
    should be connected to.

    If not *None*, *zmq_ctx* is the zeromq context to create sockets in. If
    *zmq_ctx* is *None*, the global context returned by
    :py:meth:`zmq.Context.instance` is used.

    If not *None*, *io_loop* is the event loop to pass to
    :py:class:`zmq.eventloop.zmqstream.ZMQStream` used to listen to responses
    from the server. If *None* then global IO loop is used.

    If *connect_immediately* is *True* then the client attempts to connect when
    constructed. If *False* then :py:meth:`connect` must be used explicitly.

    *heartbeat_period* is the delay, in milliseconds, between "heartbeat"
    requests to the server. These are used to ensure the server is still alive.

    .. py:attribute:: server_name

        A string giving a human-readable name for the server or *None* if the
        server has not yet replied to our initial query.

    .. py:attribute:: endpoints

        A :py:class:`dict` of endpoint addresses keyed by
        :py:class:`streamkinect2common.EndpointType`.

    .. py:attribute:: is_connected

        *True* if the client is connected. *False* otherwise.

    """

    on_connect = Signal()
    """A signal which is emitted when the client connects to a server."""

    on_disconnect = Signal()
    """A signal which is emitted when the client disconnects from a server."""

    on_add_kinect = Signal()
    """A signal which is emitted when a new kinect device is available. Handlers
    should accept a single keyword argument *kinect_id* which is the unique id
    associated with the new device."""

    on_remove_kinect = Signal()
    """A signal which is emitted when a kinect device is removed. Handlers
    should accept a single keyword argument *kinect_id* which is the unique id
    associated with the new device."""

    on_depth_frame = Signal()
    """A signal which is emitted when a new depth frame is available. Handlers
    should accept two keyword arguments: *depth_frame* which will be an
    instance of an object with the same interface as :py:class:`DepthFrame` and
    *kinect_id* which will be the unique id of the kinect device producing the
    depth frame."""

    def __init__(self, control_endpoint, connect_immediately=False, zmq_ctx=None, io_loop=None,
            heartbeat_period=10000):
        self.is_connected = False
        self.server_name = None
        self.endpoints = {
            EndpointType.control: control_endpoint
        }

        if zmq_ctx is None:
            zmq_ctx = zmq.Context.instance()
        self._zmq_ctx = zmq_ctx

        self._io_loop = io_loop

        self._response_handlers = deque()

        # Heartbeat callback and period
        self._heartbeat_period = heartbeat_period
        self._heartbeat_callback = None

        # Dictionary of device records keyed by id
        self._kinect_records = {}

        if connect_immediately:
            self.connect()

    @property
    def kinect_ids(self):
        return list(self._kinect_records.keys())

    def ping(self, pong_cb=None):
        """Send a 'ping' request to the server. If *pong_cb* is not *None*, it
        is a callable which is called with no arguments when the pong response
        has been received.

        """
        self._ensure_connected()

        def pong(type, payload, pong_cb=pong_cb):
            if pong_cb is not None:
                pong_cb()

        self._control_send(MessageType.ping, recv_cb=pong)

    def enable_depth_frames(self, kinect_id):
        """Enable streaming of depth frames. *kinect_id* is the id of the
        device which should have streaming enabled.

        :raises ValueError: if *kinect_id* does not correspond to a connected device

        """
        try:
           record = self._kinect_records[kinect_id]
        except KeyError:
            raise ValueError('Kinect id "{0}" does not correspond to a connected device'.format(
                kinect_id))

        # Create subscriber stream
        socket = self._zmq_ctx.socket(zmq.SUB)
        socket.connect(record.endpoints[EndpointType.depth])
        socket.setsockopt_string(zmq.SUBSCRIBE, u'')
        stream = ZMQStream(socket, self._io_loop)
        record.streams[EndpointType.depth] = stream

        # Fire signal on incoming depth frame
        def on_recv(msg, kinect_id=kinect_id):
            # TODO: decompress frame
            self.on_depth_frame.send(self, kinect_id=kinect_id, depth_frame=None)

        # Wire up callback
        stream.on_recv(on_recv)

    def connect(self):
        """Explicitly connect the client."""
        if self.is_connected:
            log.warn('Client already connected')
            return

        # Create, connect and wire up control socket listener
        control_endpoint = self.endpoints[EndpointType.control]
        control_socket = self._zmq_ctx.socket(zmq.REQ)
        control_socket.connect(control_endpoint)
        self._control_stream = ZMQStream(control_socket, self._io_loop)
        self._control_stream.on_recv(self._control_recv)

        self.is_connected = True

        # Kick off an initial "who-me" request
        self._who_me()

        # Create and start the heartbeat callbacl
        self._heartbeat_callback = tornado.ioloop.PeriodicCallback(
                self._who_me, self._heartbeat_period, self._io_loop)
        self._heartbeat_callback.start()

        # Finally, signal connection
        self.on_connect.send(self)

    def disconnect(self):
        """Explicitly disconnect the client."""
        if not self.is_connected:
            log.warn('Client not connected')
            return

        # Stop heartbeat callback
        if self._heartbeat_callback is not None:
            self._heartbeat_callback.stop()
        self._heartbeat_callback = None

        # TODO: check if disconnect() on the sockets is necessary
        self._control_stream = None

        self.is_connected = False

        # Finally, signal disconnection
        self.on_disconnect.send(self)

    _KinectRecord = namedtuple('_KinectRecord', ['endpoints', 'streams'])

    def _who_me(self):
        """Request the list of endpoints from the server.

        """
        # Handler function
        def got_me(type, payload):
            if type != MessageType.me:
                raise ProtocolError('Expected me list but got "{0}" instead'.format(type))

            log.info('Received "me" from server')

            if payload is None or 'version' not in payload or payload['version'] != 1:
                log.error('me had wrong or missing version')
                raise ProtocolError('unknown server protocol')

            # Fill in server information
            self.server_name = payload['name']
            log.info('Server identifies itself as "{0}"'.format(self.server_name))

            # Remember the old kinect ids
            old_kinect_ids = set(self._kinect_records.keys())

            # Extract kinects
            devices = payload['devices']
            new_records = {}
            for device in devices:
                # Fetch or create the record for this device
                try:
                    record = self._kinect_records[device['id']]
                except KeyError:
                    record = Client._KinectRecord(endpoints={}, streams={})
                new_records[device['id']] = record

                # Fill in endpoint and stream dictionaries for device
                for ep_type in EndpointType:
                    # See if this endpoint is in the payload
                    ep = None
                    try:
                        ep = device['endpoints'][ep_type.name]
                    except KeyError:
                        pass

                    if ep is None and ep_type in record.endpoints:
                        # Endpoint has gone away but was there
                        del record.endpoints[ep_type]
                        del record.streams[ep_type]
                    elif ep is not None:
                        # Is this a new or changed endpoint endpoint?
                        if ep_type not in record.endpoints or record.endpoints[ep_type] != ep:
                            # Record new/changed endpoint
                            record.endpoints[ep_type] = ep

                            # Initially there are no streams for any endpoint to avoid
                            # subscribing to services we do not need.
                            record.streams[ep_type] = None

            # Update kinect records
            self._kinect_records = new_records

            # Fill in out server endpoint list from payload
            endpoints = payload['endpoints']
            for endpoint_type in EndpointType:
                try:
                    self.endpoints[endpoint_type] = endpoints[endpoint_type.name]
                    log.info('Server added "{0.name}" endpoint at "{1}"'.format(
                        endpoint_type, endpoints[endpoint_type.name]))
                except KeyError:
                    # Skip endpoints we don't know about
                    pass

            # Send {add,remove}_kinect events...
            new_kinect_ids = set(self._kinect_records.keys())

            # ... for devices in new list and not in old
            for k_id in new_kinect_ids.difference(old_kinect_ids):
                self.on_add_kinect.send(self, kinect_id=k_id)

            # ... for devices in old list and not in new
            for k_id in old_kinect_ids.difference(new_kinect_ids):
                self.on_remove_kinect.send(self, kinect_id=k_id)

        # Send packet
        log.info('Requesting server identity')
        self._control_send(MessageType.who, recv_cb=got_me)

    def _ensure_connected(self):
        if not self.is_connected:
            raise RuntimeError('Client is not connected')

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    def _control_send(self, type, payload=None, recv_cb=None):
        """Send *payload* formatted as a JSON object along the control socket.
        If *recv_cb* is not *None*, it is a callable which is called with the
        type and Python object representing the response payload from the
        server. If there is no payload, None is passed.

        """
        self._response_handlers.append(recv_cb)
        self._control_stream.send_multipart(make_msg(type, payload))

    def _control_recv(self, msg):
        """Called when there is something to be received on the control socket."""
        # Parse message
        type, payload = parse_msg(msg)

        # Do we have a recv handler?
        handler = self._response_handlers.popleft()
        if handler is not None:
            handler(type, payload)
