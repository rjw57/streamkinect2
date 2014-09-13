"""
Depth frame compression
=======================

"""
from io import BytesIO

from blinker import Signal
import lz4
import numpy as np
from PIL import Image
import tornado.ioloop

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
    buffer-like object containing the compressed frame data."""

    def __init__(self, kinect, io_loop=None):
        # Public attributes
        self.kinect = kinect

        # Private attributes
        self._io_loop = io_loop or tornado.ioloop.IOLoop.instance()

        # Wire ourselves up for depth frame events
        kinect.on_depth_frame.connect(self._on_depth_frame, sender=kinect)

    def _on_depth_frame(self, kinect, depth_frame):
        d = np.frombuffer(depth_frame.data, dtype=np.uint16).reshape(
                depth_frame.shape[::-1], order='C')
        d = (d>>4).astype(np.uint8)
        d_im = Image.fromarray(d)

        bio = BytesIO()
        d_im.save(bio, 'jpeg')

        compressed_frame = bio.getvalue()
        self._io_loop.add_callback(
            self.on_compressed_frame.send,
            self, compressed_frame=compressed_frame
        )
