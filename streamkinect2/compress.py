"""
Depth frame compression
=======================

"""
from logging import getLogger
from io import BytesIO
from multiprocessing.pool import Pool
from multiprocessing import cpu_count

from blinker import Signal
import lz4
import numpy as np
from PIL import Image
import tornado.ioloop

log = getLogger(__name__)

def _compress_depth_frame(depth_frame):
    d = np.frombuffer(depth_frame.data, dtype=np.uint16).reshape(
            depth_frame.shape[::-1], order='C')
    d = (d>>4).astype(np.uint8)
    d_im = Image.fromarray(d)

    bio = BytesIO()
    d_im.save(bio, 'jpeg')

    return bio.getvalue()

class DepthFrameCompressor(object):
    """
    Asynchronous compression pipeline for depth frames.

    *kinect* is a :py:class:`streamkinect2.mock.MockKinect`-like object. Depth
    frames emitted by :py:meth:`on_depth_frame` will be compressed with
    frame-drop if the compressor becomes overloaded.

    If *io_loop* is provided, it specifies the
    :py:class:`tornado.ioloop.IOLoop` which is used to co-ordinate the worker
    process. If not provided, the global instance is used.

    .. py:attribute:: kinect

        Kinect object associated with this compressor.
    """

    on_compressed_frame = Signal()
    """Signal emitted when a new compressed frame is available. Receivers take
    a single keyword argument, *compressed_frame*, which is a Python
    buffer-like object containing the compressed frame data. The signal is
    emitted on the IOLoop thread."""

    # The maximum number of frames we can be waiting for before we start
    # dropping them.
    _MAX_IN_FLIGHT = cpu_count() + 1

    def __init__(self, kinect, io_loop=None):
        # Public attributes
        self.kinect = kinect

        # Private attributes
        self._io_loop = io_loop or tornado.ioloop.IOLoop.instance()
        self._pool = Pool() # worker process pool
        self._n_in_flight = 0 # How many frames are we waiting for?
        self._n_dropped = 0

        # Wire ourselves up for depth frame events
        kinect.on_depth_frame.connect(self._on_depth_frame, sender=kinect)

    def __del__(self):
        # As a courtesy, terminate the worker pool to avoid having a sea of
        # dangling processes.
        self._pool.terminate()

    def _on_compressed_frame(self, compressed_frame):
        # Record arrival of frame
        self._n_in_flight -= 1

        # Send signal
        try:
            self._io_loop.add_callback(
                self.on_compressed_frame.send,
                self, compressed_frame=compressed_frame
            )
        except Exception as e:
            # HACK: Since multiprocessing *might* call this handler after the
            # io loop has shut down (which will raise an Exception) and because
            # there's no documented way to determine if the io loop is still
            # alive ahead of time, we swallow exceptions here. This should
            # happen rarely when one is rapidly starting and stopping IOLoops
            # (such as in the test-suite!) so log it as a warning.
            log.warn('DepthFrameCompressor swallowed {0} exception'.format(e))

    def _on_depth_frame(self, kinect, depth_frame):
        # If we aren't waiting on too many frames, submit
        if self._n_in_flight < DepthFrameCompressor._MAX_IN_FLIGHT:
            self._pool.apply_async(_compress_depth_frame,
                    args=(depth_frame,), callback=self._on_compressed_frame)
            self._n_in_flight += 1
        else:
            # Only log every 10 dropped frames to avoid being too spammy
            self._n_dropped += 1
            if self._n_dropped % 10 == 0:
                log.warn('Dropped {0} depth frames'.format(self._n_dropped))

