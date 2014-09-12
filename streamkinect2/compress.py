from blinker import Signal

import lz4

class DepthFrameCompresser(object):
    on_compressed_frame = Signal()
    """Signal emitted when a new compressed frame is available. Receivers take
    a single keyword argument, *compressed_frame*, which is a sequence of
    Python buffer-like objects containing the compressed frame data."""

    def __init__(self, kinect):
        kinect.on_depth_frame.connect(self._on_depth_frame, sender=kinect)

    def _on_depth_frame(self, kinect, depth_frame):
        self.on_compressed_frame.send(self, compressed_frame=[lz4.dumps(depth_frame.data),])
