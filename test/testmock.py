"""
Mock kinect support

"""
from logging import getLogger
import time

log = getLogger(__name__)

import streamkinect2.mock as mock
from streamkinect2.compress import DepthFrameCompressor

from .util import AsyncTestCase

# This is intentionally low to not be too hard on the test server. Use a
# benchmark script if you want to get a better idea of performance.
TARGET_FPS = 10

class TestMock(AsyncTestCase):
    def setUp(self):
        super(TestMock, self).setUp()
        self.kinect = mock.MockKinect()

    def wait_for_frames(self, kinect, min_count, timeout):
        state = { 'count': 0 }

        @kinect.on_depth_frame.connect_via(kinect)
        def frame_listener(kinect, depth_frame):
            state['count'] += 1

        start = time.time()
        self.keep_checking(lambda: state['count'] > min_count or time.time() > start + timeout)
        self.wait()
        end = time.time()

        # Return the number of frames received and how long we waited
        return state['count'], (end-start)

    def wait_for_and_compress_frames(self, kinect, min_count, timeout):
        compressed = []

        fc = DepthFrameCompressor(kinect, io_loop=self.io_loop)
        @fc.on_compressed_frame.connect_via(fc)
        def new_compressed_frame(_, compressed_frame):
            compressed.append(compressed_frame)

        start = time.time()
        self.keep_checking(lambda: len(compressed) > min_count or time.time() > start + timeout)
        self.wait()
        end = time.time()

        # Return the packets received and how long we waited
        return compressed, (end-start)

    def test_create_mock(self):
        with self.kinect as kinect:
            pass

    def test_getting_frames(self):
        with self.kinect as kinect:
            count, t = self.wait_for_frames(kinect, 1, 0.5)
        log.info('Got {0} frame(s) in {1:.2f} seconds'.format(count, t))
        assert count >= 1

    def test_getting_enough_fps(self):
        with self.kinect as kinect:
            count, t = self.wait_for_frames(kinect, 30, 0.5)
        fps = float(count) / t
        log.info('Mock kinect gave {0} frames in {1:.2f} seconds => fps = {2:.2f}'.format(
            count, t, fps))
        if fps < TARGET_FPS:
            log.error('FPS should be > {0}'.format(TARGET_FPS))
        assert fps >= TARGET_FPS

    def test_getting_compressed_frames(self):
        with self.kinect as kinect:
            packets, t = self.wait_for_and_compress_frames(kinect, 10, 0.5)
        log.info('Got {0} compressed packets in {1:.2f} seconds'.format(len(packets), t))
        assert len(packets) > 0

    def test_getting_good_enough_compression(self):
        with self.kinect as kinect:
            packets, t = self.wait_for_and_compress_frames(kinect, 1024, 2.0)
        log.info('Got {0} compressed packets in {1:.2f} seconds'.format(len(packets), t))
        size = sum(len(y) for y in packets)
        data_rate = (float(size) / t) / (1024*1024)
        log.info('Total size is {0} bytes => {1:.2f} Mbytes/s'.format(size, data_rate))
        assert data_rate < 80 * 1024 * 1024

    def test_getting_fast_enough_compression(self):
        with self.kinect as kinect:
            packets, t = self.wait_for_and_compress_frames(kinect, 120, 2.0)
        fps = float(len(packets)) / t
        log.info('Mock kinect gave {0} compressed packets in {1:.2f} seconds => fps = {2:.2f}'.format(
            len(packets), t, fps))
        if fps < TARGET_FPS:
            log.error('FPS should be > {0}'.format(TARGET_FPS))
        assert fps >= TARGET_FPS

    def test_unique_id_exists_and_unique(self):
        assert self.kinect.unique_kinect_id is not None

        other_kinect = mock.MockKinect()
        assert self.kinect.unique_kinect_id != other_kinect.unique_kinect_id
