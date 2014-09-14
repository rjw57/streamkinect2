"""
Common elements for both client and server
==========================================

"""
import enum
import json

class ProtocolError(RuntimeError):
    """Raised when some low-level error in the network protocol has been
    detected.
    """

class EndpointType(enum.Enum):
    """
    Enumeration of endpoints exposed by a :py:class:`Server`.

    .. py:attribute:: control

        A *REP* endpoint which accepts JSON-formatted control messages.

    .. py:attribute:: depth

        A *PUB* endpoint which broadcasts compressed depth frames to connected subscribers.

    """
    control = 1
    depth = 2

class MessageType(enum.Enum):
    error = b'\x00'
    ping = b'\x01'
    pong = b'\x02'
    who = b'\x03'
    me = b'\x04'

def make_msg(type, payload):
    if payload is None:
        return [type.value,]
    return [type.value, json.dumps(payload).encode('utf8')]

def parse_msg(msg):
    if len(msg) == 1:
        return MessageType(msg[0]), None
    elif len(msg) == 2:
        return MessageType(msg[0]), json.loads(msg[1].decode('utf8'))

    raise ValueError('Multipart message must have length 1 or 2')
