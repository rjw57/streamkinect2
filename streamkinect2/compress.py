import lz4

class DepthFrameCompresser(object):
    def __init__(self, output_cb):
        self.output_cb = output_cb
        self.last_iframe = None
        self.n_pframes = 0
        self.gop_size = 30

    def add_frame(self, frame):
        self.output_cb([lz4.dumps(frame.data),])
