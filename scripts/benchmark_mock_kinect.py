from logging import getLogger
import time

from streamkinect2.mock import MockKinect
from streamkinect2.compress import DepthFrameCompressor

def benchmark_compressed(wait_time):
    print('Running compressed pipeline for {0} seconds...'.format(wait_time))
    packets = []
    with MockKinect() as kinect:
        fc = DepthFrameCompressor(kinect)
        @fc.on_compressed_frame.connect_via(fc)
        def new_compressed_frame(_, compressed_frame):
            packets.append(compressed_frame)
        then = time.time()
        time.sleep(5)
        now = time.time()
    delta = now - then
    data_size = sum(len(p) for p in packets)
    data_rate = float(data_size) / delta # bytes/sec
    pps = len(packets) / delta
    print('Mock kinect runs at {0:.2f} packets/second w/ compression'.format(pps))
    print('Data rate is {0:2f} Mbytes/second'.format(data_rate / (1024*1024)))

def benchmark_mock(wait_time):
    print('Running mock kinect for {0} seconds...'.format(wait_time))
    state = { 'n_frames': 0 }
    with MockKinect() as kinect:
        then = time.time()
        @kinect.on_depth_frame.connect_via(kinect)
        def f(kinect, depth_frame):
            state['n_frames'] += 1
        time.sleep(wait_time)
        now = time.time()
    delta = now - then
    fps = state['n_frames'] / delta
    print('Mock kinect runs at {0:.2f} frames/second'.format(fps))

def main():
    wait_time = 5
    benchmark_compressed(wait_time)
    benchmark_mock(wait_time)

if __name__ == '__main__':
    main()
