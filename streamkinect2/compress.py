from blinker import Signal

import lz4
import numpy as np

class DepthFrameCompressor(object):
    """
    .. py:attribute:: kinect

        Kinect object associated with this compressor.
    """

    on_compressed_frame = Signal()
    """Signal emitted when a new compressed frame is available. Receivers take
    a single keyword argument, *compressed_frame*, which is a Python
    buffer-like object containing the compressed frame data."""

    def __init__(self, kinect):
        kinect.on_depth_frame.connect(self._on_depth_frame, sender=kinect)
        self.kinect = kinect
        self.last_frame = None

    def _on_depth_frame(self, kinect, depth_frame):
        compressed_frame = lz4.dumps(bytes(depth_frame.data))
        self.on_compressed_frame.send(self, compressed_frame=compressed_frame)
