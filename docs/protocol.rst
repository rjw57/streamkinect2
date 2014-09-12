Network protocol
================

The network protocol is based on `Zeroconf
<https://en.wikipedia.org/wiki/Zero-configuration_networking>`_ for server
discovery and `ZeroMQ <http://zeromq.org/>`_ for communication.  The
architecture is a traditional client-server model with one server dealing with
zero, one or many clients. In practice there will probably be one server and
one client.  The transport is based entirely on ZeroMQ sockets and so it is
recommended that one read some of the `ZeroMQ guide
<http://zguide.zeromq.org/page:all>`_ before this document.

Server discovery
----------------

Servers advertise themselves over ZeroConf using the ``_kinect2._tcp`` service
type. The IP address and port associated with that service is converted into a
ZeroMQ endpoint as ``tcp://<address>:<port>`` and is used to find the "control"
endpoint of the server.

Endpoints
---------

Much like the USB protocol, each server advertises a number of "endpoints"
which are specified as a ZeroMQ address, usually of the form
``tcp://<address>:<port>``. The "control" endpoint is advertised over ZeroConf
and may be used to query other endpoints.  An endpoint is usually a ZeroMQ
socket pair, one on the client and one on the server.

Control Endpoint
````````````````

The "control" endpoint is a REP socket on the server which expects to be
connected to via a REQ socket on the client. Clients initiate communication
with a JSON-encoded object. The server will then respond with a JSON-encoded
object. This is repeated until the client disconnects.

All messages have the following form::

    {
        "seq": "<sequence number>",
        "type": "<string describing type of message>",
        "payload": "<optional JSON object whose schema is type dependant>"
    }

The server will copy the sequence number from the client message into its
reply. It is expected that the sequence number will increase monotonically with
each request/response pair but the server doesn't take note of the sequence
number at all; it is used as a convenience to associate requests with their
response on the client side.

Each message type has its own semantics and payload schema. Some messages may
only be sent by a client and some only by a server.

``ping`` type
~~~~~~~~~~~~~

A ``ping`` message MUST only be sent by a client. No payload is required. The
server MUST respond with an empty-payload message of type ``pong``.

``pong`` type
~~~~~~~~~~~~~

A ``pong`` message MUST only be sent by a server. It MUST do so in response to
a ``ping``.  No payload is required.

``who`` type
~~~~~~~~~~~~

A ``who`` message MUST only be sent by a client. No payload is required. The
server MUST respond with a ``me`` message.

``me`` type
~~~~~~~~~~~

A ``me`` messages MUST only be sent by a server. It MUST do so in
response to a ``who`` message. A payload MUST be present. The payload MUST be a
JSON object including at least a ``version`` field which should be the numeral
"1". A client MUST ignore any ``me`` message with a ``version`` field set to
any other value.

The payload MUST include a field named ``name`` whose value is a string
representing a human-readable name for the server.

The payload MUST include a field named ``endpoints`` whose value is a JSON
object whose fields correspond to endpoint names and whose values correspond to
ZeroMQ-style endpoint addresses. The client MUST ignore any endpoints whose
name it does not recognise. The server MAY advertise any endpoints it wishes
but it MUST include at least a ``control`` endpoint with a ZeroMQ address
corresponding to the control endpoint. The advertised endpoints MAY be
non-unique and MAY have different IP addresses.

The payload MUST include a field named ``devices`` whose value is a JSON array
of device records. A device record is a JSON object. A device record MUST
include a field named ``id`` whose value is a string giving a unique name for a
Kinect connected to the server. A device record MUST include a field named
``endpoints`` whose value takes the same format (but not necessarily the same
value) as the ``endpoints`` object in the payload. This ``endpoints`` object
gives endpoints which are specific to a particular device.

A typical payload will look like the following::

    {
        "version": 1,
        "name": "Bob's Kinect",
        "endpoints": {
            "control": "tcp://10.0.0.1:1234"
        },
        "devices": [
            {
                "id": "123456789abcdefghijklmnopqrstuv",
                "endpoints": {
                    "depth": "tcp://10.0.0.1:1236"
                }
            }
        ],
    }
