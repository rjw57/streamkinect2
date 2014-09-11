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

import numpy as np

def _make_mock(frame_shape):
    xs, ys = np.meshgrid(np.arange(frame_shape[1]), np.arange(frame_shape[0]))
    wall = np.abs(ys>>1) + 1000
    sphere = np.sqrt((xs-(frame_shape[1]>>1))*(xs-(frame_shape[1]>>1)) + \
            (ys-(frame_shape[0]>>1))*(ys-(frame_shape[0]>>1))) + 500
    return wall.astype(np.uint16), sphere.astype(np.uint16)

class DepthFrame(namedtuple('DepthFrame', ('data',))):
    """A single frame of depth data.

    .. py:attribute:: data

        Python buffer-like object pointing to raw frame data.
    """

class MockKinect(threading.Thread):
    """A mock Kinect device.
    """
    def __init__(self):
        super(MockKinect, self).__init__()

        self._depth_listeners = set()
        self._depth_listeners_lock = threading.Lock()

        self._frame_shape = (1080, 1920)
        self._wall, self._sphere = _make_mock(self._frame_shape)

        self._should_stop = False

    def add_depth_frame_listener(self, listener):
        """Add *listener* as a callable which is called with a
        :py:class:`DepthFrame`-like object for each depth frame from the
        camera.

        """
        with self._depth_listeners_lock:
            self._depth_listeners.add(listener)

    def remove_depth_frame_listener(self, listener):
        with self._depth_listeners_lock:
            self._depth_listeners.remove(listener)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()

    def stop(self):
        self._should_stop = True
        self.join(1)

    def run(self):
        while not self._should_stop:
            then = time.time()
            dx = int(np.sin(then) * 100)
            df = np.minimum(self._wall, np.roll(self._sphere, dx, 1))
            depth_frame = DepthFrame(data=bytes(df.data))
            with self._depth_listeners_lock:
                for l in self._depth_listeners:
                    l(depth_frame)
            now = time.time()

            # HACK: aim for just above 60FPS
            time.sleep(max(0, (1.0/70.0) - (now-then)))
