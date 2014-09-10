"""
Mock kinect support

"""
import functools
from logging import getLogger
import time
from nose.plugins.skip import SkipTest

log = getLogger(__name__)

# Importing mock can fail if numpy is not installed
try:
    import streamkinect2.mock as mock
except:
    mock = None

from streamkinect2.compress import DepthFrameCompresser

def skip_if_no_mock(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if mock is None:
            raise SkipTest('Mock kinect not available')
        return f(*args, **kwargs)
    return wrapper

def wait_for_frames(kinect, min_count, timeout):
    state = { 'count': 0 }
    def frame_listener(w_and_h, frame):
        state['count'] += 1

    kinect.add_depth_frame_listener(frame_listener)
    start = time.time()
    while state['count'] < min_count and time.time() < start + timeout:
        time.sleep(0.1)
    end = time.time()
    kinect.remove_depth_frame_listener(frame_listener)

    # Return the number of frames received and how long we waited
    return state['count'], (end-start)

def wait_for_and_compress_frames(kinect, min_count, timeout):
    compressed = []
    def new_compressed_frame(c):
        compressed.append(c)

    fc = DepthFrameCompresser(new_compressed_frame)

    kinect.add_depth_frame_listener(fc.add_frame)
    start = time.time()
    while len(compressed) < min_count and time.time() < start + timeout:
        time.sleep(0.1)
    end = time.time()
    kinect.remove_depth_frame_listener(fc.add_frame)

    # Return the packets received and how long we waited
    return compressed, (end-start)

@skip_if_no_mock
def test_create_mock():
    with mock.MockKinect() as kinect:
        pass

@skip_if_no_mock
def test_getting_frames():
    with mock.MockKinect() as kinect:
        count, t = wait_for_frames(kinect, 1, 0.5)
    log.info('Got {0} frame(s) in {1:.2f} seconds'.format(count, t))
    assert count >= 1

@skip_if_no_mock
def test_getting_enough_fps():
    with mock.MockKinect() as kinect:
        count, t = wait_for_frames(kinect, 30, 0.5)
    fps = float(count) / t
    log.info('Mock kinect gave {0} frames in {1:.2f} seconds => fps = {2:.2f}'.format(
        count, t, fps))
    if fps < 55:
        log.error('FPS should be > 55')
    assert fps >= 55

@skip_if_no_mock
def test_getting_compressed_frames():
    with mock.MockKinect() as kinect:
        packets, t = wait_for_and_compress_frames(kinect, 10, 0.5)
    log.info('Got {0} compressed packets in {1:.2f} seconds'.format(len(packets), t))
    assert len(packets) > 0

@skip_if_no_mock
def test_getting_good_enough_compression():
    with mock.MockKinect() as kinect:
        packets, t = wait_for_and_compress_frames(kinect, 1024, 2.0)
    log.info('Got {0} compressed packets in {1:.2f} seconds'.format(len(packets), t))
    size = 0
    for p in packets:
        size += len(p)
    data_rate = (float(size) / t) / (1024*1024)
    log.info('Total size is {0} bytes => {1:.2f} Mbytes/s'.format(size, data_rate))
    assert data_rate < 80 * 1024 * 1024

@skip_if_no_mock
def test_getting_fast_enough_compression():
    with mock.MockKinect() as kinect:
        packets, t = wait_for_and_compress_frames(kinect, 120, 2.0)
    fps = float(len(packets)) / t
    log.info('Mock kinect gave {0} compressed packets in {1:.2f} seconds => fps = {2:.2f}'.format(
        len(packets), t, fps))
    if fps < 55:
        log.error('FPS should be > 55')
    assert fps >= 55
