"""
Mock kinect
===========

.. note::

    This module requires :py:mod:`numpy` to be installed.

Support for a mock kinect when testing.

"""
from collections import namedtuple
import threading
import time
import uuid

from blinker import Signal
import numpy as np

def _make_mock(frame_shape):
    xs, ys = np.meshgrid(np.arange(frame_shape[1]), np.arange(frame_shape[0]))
    wall = np.abs(ys>>1) + 1000
    sphere = np.sqrt((xs-(frame_shape[1]>>1))*(xs-(frame_shape[1]>>1)) + \
            (ys-(frame_shape[0]>>1))*(ys-(frame_shape[0]>>1))) + 500
    return wall.astype(np.uint16), sphere.astype(np.uint16)

class DepthFrame(namedtuple('DepthFrame', ('data', 'shape'))):
    """A single frame of depth data.

    .. py:attribute:: data

        Python buffer-like object pointing to raw frame data as a C-ordered
        array of uint16.

    .. py:attribute:: shape

        Pair giving the width and height of the depth frame.

    """

class MockKinect(threading.Thread):
    """A mock Kinect device.

    This class implements a "virtual" Kinect which generates some mock data. It
    can be used for testing or benchmarking.

    Use :py:meth:`start` and :py:meth:`stop` to start and stop the device or
    wrap it in a ``with`` statement::

        with MockKinect() as kinect:
            # kinect is running here
            pass
        # kinect has stopped running

    .. note::

        Listener callbacks are called in a separate thread. If using something
        like :py:class:`tornado.ioloop.IOLoop`, then you will need to make sure
        that server messages are sent on the right thread. The
        :py:class:`streamkinect2.server.Server` class should take care of that
        in most cases you will encounter.

    .. py:attribute:: unique_kinect_id

        A string with an opaque, unique id for this Kinect.

    """

    on_depth_frame = Signal()
    """A signal which is emitted when a new depth frame is available. Handlers
    should accept a single keyword argument *depth_frame* which will be an
    instance of :py:class:`DepthFrame`."""

    def __init__(self):
        super(MockKinect, self).__init__()

        # Invent unique id
        self.unique_kinect_id = uuid.uuid4().hex

        self._frame_shape = (1080, 1920)
        self._wall, self._sphere = _make_mock(self._frame_shape)

        self._should_stop = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()

    def start(self):
        """Start the mock device running. Mock data is generated on a separate
        thread.

        """
        super(MockKinect, self).start()

    def stop(self):
        """Stop the mock device running. Blocks until the thread shuts down
        gracefully with a one second timeout.

        """
        self._should_stop = True
        self.join(1)

    def run(self):
        while not self._should_stop:
            then = time.time()
            dx = int(np.sin(then) * 100)
            df = np.minimum(self._wall, np.roll(self._sphere, dx, 1))
            df = np.asarray(df, order='C', dtype=np.uint16)
            depth_frame = DepthFrame(data=bytes(df.data), shape=df.shape[::-1])
            self.on_depth_frame.send(self, depth_frame=depth_frame)
            now = time.time()

            # HACK: aim for just above 60FPS
            time.sleep(max(0, (1.0/70.0) - (now-then)))
