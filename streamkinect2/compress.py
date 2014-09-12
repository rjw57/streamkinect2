import lz4

class DepthFrameCompresser(object):
    def __init__(self, output_cb, kinect):
        self.output_cb = output_cb
        self.last_iframe = None
        self.n_pframes = 0
        self.gop_size = 30

        kinect.on_depth_frame.connect(self._on_depth_frame, sender=kinect)

    def _on_depth_frame(self, kinect, depth_frame):
        self.output_cb([lz4.dumps(depth_frame.data),])
