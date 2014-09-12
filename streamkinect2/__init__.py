"""Kinect2 streaming server and client

Event handling
==============

Some :py:mod:`streamkinect2` object emit events. The `blinker
<https://pythonhosted.org/blinker/>`_ library is used to handle signals. See the
blinker documentation for full details. As an example, here is how to register
an event handler for a new depth frame from a
:py:class:`streamkinect2.mock.MockKinect` object::

    from streamkinect2.mock import MockKinect

    kinect = MockKinect()

    # The "depth_frame" argument name is important here as the depth frame is
    # passed as a keyword argument.
    def handler_func(kinect, depth_frame):
        print('New depth frame')

    MockKinect.on_depth_frame.connect(handler_func, kinect)

Alternatively, one may use the :py:meth:`connect_via` decorator::

    from streamkinect2.mock import MockKinect

    kinect = MockKinect()

    @MockKinect.on_depth_frame.connect_via(kinect)
    def handler_func(kinect, depth_frame):
        print('New depth frame')

Note that, by default, signal handlers are kept as weak references so that they
do not need to be explicitly disconnected before they can be garbage collected.

"""
# Version metadata
from .version import *
