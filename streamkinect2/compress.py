from io import BytesIO

from blinker import Signal

import lz4
import numpy as np
from PIL import Image

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
        d = np.frombuffer(depth_frame.data, dtype=np.uint16).reshape(
                depth_frame.shape[::-1], order='C')
        d = (d>>4).astype(np.uint8)
        d_im = Image.fromarray(d)

        bio = BytesIO()
        d_im.save(bio, 'jpeg')

        compressed_frame = bio.getvalue()
        self.on_compressed_frame.send(self, compressed_frame=compressed_frame)
