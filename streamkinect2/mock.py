"""
Mock kinect
===========

.. note::

    This module requires :py:mod:`numpy` to be installed.

Support for a mock kinect when testing.

"""
import threading
import time

import numpy as np

def _make_mock(frame_shape):
    xs, ys = np.meshgrid(np.arange(frame_shape[1]), np.arange(frame_shape[0]))
    wall = np.abs(ys>>1) + 1000
    sphere = np.sqrt((xs-(frame_shape[1]>>1))*(xs-(frame_shape[1]>>1)) + \
            (ys-(frame_shape[0]>>1))*(ys-(frame_shape[0]>>1))) + 500
    return wall.astype(np.uint16), sphere.astype(np.uint16)

class MockKinect(threading.Thread):
    def __init__(self):
        super(MockKinect, self).__init__()

        self._depth_listeners = set()
        self._depth_listeners_lock = threading.Lock()

        self._frame_shape = (1080, 1920)
        self._wall, self._sphere = _make_mock(self._frame_shape)

        self._should_stop = False

    def add_depth_frame_listener(self, listener):
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
            with self._depth_listeners_lock:
                for l in self._depth_listeners:
                    l(df.data)
            now = time.time()

            # HACK: aim for just above 60FPS
            time.sleep(max(0, (1.0/70.0) - (now-then)))
