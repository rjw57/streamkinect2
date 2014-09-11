"""
Client
======

"""
import json
from logging import getLogger
import functools

import zmq
from zmq.eventloop.zmqstream import ZMQStream

from .common import EndpointType, ProtocolError

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

    .. py:attribute:: server_name

        A string giving a human-readable name for the server or *None* if the
        server has not yet replied to our initial query.

    .. py:attribute:: endpoints

        A :py:class:`dict` of endpoint addresses keyed by
        :py:class:`streamkinect2common.EndpointType`.

    .. py:attribute:: is_connected

        *True* if the client is connected. *False* otherwise.

    """
    def __init__(self, control_endpoint, connect_immediately=False, zmq_ctx=None, io_loop=None):
        self.is_connected = False
        self.server_name = None
        self.endpoints = {
            EndpointType.control: control_endpoint
        }
        self.kinect_ids = []

        if zmq_ctx is None:
            zmq_ctx = zmq.Context.instance()
        self._zmq_ctx = zmq_ctx

        self._io_loop = io_loop

        # Sequence number of all messages
        self._sequence_number = 0

        # Callables to handle responses keyed by sequence number
        self._response_handlers = {}

        if connect_immediately:
            self.connect()

    def ping(self, pong_cb=None):
        """Send a 'ping' request to the server. If *pong_cb* is not *None*, it
        is a callable which is called with no arguments when the pong response
        has been received.

        """
        self._ensure_connected()

        def pong(seq, type, payload, pong_cb=pong_cb):
            if pong_cb is not None:
                pong_cb()

        self._control_send('ping', recv_cb=pong)

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

        self._who_me()

    def disconnect(self):
        """Explicitly disconnect the client."""
        if not self.is_connected:
            log.warn('Client not connected')
            return

        # TODO: check if disconnect() on the sockets is necessary
        self._control_stream = None

        self.is_connected = False

    def _who_me(self):
        """Request the list of endpoints from the server.

        """
        # Handler function
        def got_me(seq, type, payload):
            if type != 'me':
                raise ProtocolError('Expected me list but got "{0}" instead'.format(type))

            log.info('Received "me" from server')

            if 'version' not in payload or payload['version'] != 1:
                log.error('me had wrong or missing version')
                raise ProtocolError('unknown server protocol')

            # Fill in server information
            self.server_name = payload['name']
            log.info('Server identifies itself as "{0}"'.format(self.server_name))

            # Extract kinects
            devices = payload['devices']
            self.kinect_ids = list(d['id'] for d in devices)

            # Fill in out endpoint list from payload
            endpoints = payload['endpoints']
            for endpoint_type in EndpointType:
                try:
                    self.endpoints[endpoint_type] = endpoints[endpoint_type.name]
                    log.info('Server added "{0.name}" endpoint at "{1}"'.format(
                        endpoint_type, endpoints[endpoint_type.name]))
                except KeyError:
                    # Skip endpoints we don't know about
                    pass

        # Send packet
        log.info('Requesting server identity')
        self._control_send('who', recv_cb=got_me)

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
        Takes care of adding a "seq" field to the object with an
        auto-incremented sequence number. The message sent to the server is::

            {
                "seq":      <generated sequence number>,
                "type":     type,
                "payload":  payload # formatted as a JSON object
            }

        If *recv_cb* is not *None*, it is a callable which is called with the
        type and Python object representing the response payload from the
        server.

        """
        self._sequence_number += 1
        seq = self._sequence_number
        if recv_cb is not None:
            self._response_handlers[seq] = recv_cb
        msg = { 'seq': seq, 'type': type, 'payload': payload, }
        self._control_stream.send_json(msg)

    def _control_recv(self, msg):
        """Called when there is something to be received on the control socket."""
        # Read JSON message
        try:
            msg = json.loads((b''.join(msg)).decode('utf8'))
        except ValueError:
            log.warn('Client ignoring invalid control packet')
            return

        # Check packet has required fields
        if 'seq' not in msg:
            log.warn('Client ignoring control packet lacking sequence number')
            return
        if 'type' not in msg:
            log.warn('Client ignoring control packet lacking type')
            return

        seq, type = msg['seq'], msg['type']
        payload = msg['payload'] if 'payload' in msg else None

        # Do we have a recv handler?
        try:
            recv_cb = self._response_handlers[seq]
        except KeyError:
            # Nope, just drop it
            return

        # Call the callback
        del self._response_handlers[seq]
        recv_cb(seq, type, payload)
