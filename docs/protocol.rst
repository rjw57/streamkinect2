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
by sending a ``who`` message. The server will then respond with a ``me``
message. The client may then send other messages expecting each time a reply
from the server. This is repeated until the client disconnects.

All messages are multipart messages with one or two frames. The first frame
is a single byte which indicates the message type. The second frame, if
present, represents a JSON encoded object which is the "payload" of the
message.

Each message type has its own semantics and payload schema. Some messages may
only be sent by a client and some only by a server.

``error`` type
~~~~~~~~~~~~~~

An ``error`` message (type 0x00) MUST only be sent by the server. The server
MAY send an ``error`` message in reply to any incoming request. The payload
must contain a ``reason`` field with a human-readable description of the error.
The client MAY choose to disconnect from the server or silently ignore the
error.

``ping`` type
~~~~~~~~~~~~~

A ``ping`` message (type 0x01) MUST only be sent by a client. No payload is
required. The server MUST respond with an empty-payload message of type
``pong`` or an ``error`` message.

``pong`` type
~~~~~~~~~~~~~

A ``pong`` message (type 0x02) MUST only be sent by a server. It MUST do so in
response to a ``ping`` if no ``error`` is sent. No payload is required.

``who`` type
~~~~~~~~~~~~

A ``who`` message (type 0x03) MUST only be sent by a client. No payload is
required. The server MUST respond with a ``me`` message or an ``error``
message.

``me`` type
~~~~~~~~~~~

A ``me`` messages MUST only be sent by a server. It MUST do so in
response to a ``who`` message if no ``error`` is sent. A payload MUST be
present. The payload MUST be an object including at least a ``version``
field which should be the numeric value 1. A client MUST ignore any ``me``
message with a ``version`` field set to any other value.

The payload MUST include a field named ``name`` whose value is a string
representing a human-readable name for the server.

The payload MUST include a field named ``endpoints`` whose value is an object
whose fields correspond to endpoint names and whose values correspond to
ZeroMQ-style endpoint addresses. The client MUST ignore any endpoints whose
name it does not recognise. The server MAY advertise any endpoints it wishes
but it MUST include at least a ``control`` endpoint with a ZeroMQ address
corresponding to the control endpoint. The advertised endpoints MAY be
non-unique and MAY have different IP addresses.

The payload MUST include a field named ``devices`` whose value is an array of
device records. A device record is a JSON object. A device record MUST include
a field named ``id`` whose value is a string giving a unique name for a Kinect
connected to the server. A device record MUST include a field named
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
