"""
Common elements for both client and server
==========================================

"""
import enum

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
