Example programs
================

Here are some example programs which use the :py:mod:`streamkinect2` API.

Simple ping client
``````````````````

The following program shows how to use the
:py:class:`streamkinect2.server.ServerBrowser` class to discover servers on the
network. For each server, a simple client is created which sends a ``ping`` to
the server and logs when a ``pong`` is received.

.. literalinclude:: ../scripts/ping_client.py

Mock kinect server
``````````````````

The following program shows how to create a simple server which will serve data
from a mock Kinect. See the :py:mod:`streamkinect2.mock` module.

.. literalinclude:: ../scripts/mock_server.py
