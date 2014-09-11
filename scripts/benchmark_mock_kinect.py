from logging import getLogger
import time

from streamkinect2.mock import MockKinect
from streamkinect2.compress import DepthFrameCompresser

def main():
    wait_time = 5

    print('Running mock kinect for {0} seconds...'.format(wait_time))
    state = { 'n_frames': 0 }
    with MockKinect() as kinect:
        then = time.time()
        def f(frame):
            state['n_frames'] += 1
        kinect.add_depth_frame_listener(f)
        time.sleep(wait_time)
        now = time.time()
    delta = now - then
    fps = state['n_frames'] / delta
    print('Mock kinect runs at {0:.2f} frames/second'.format(fps))

    print('Running compressed pipeline for {0} seconds...'.format(wait_time))
    packets = []
    fc = DepthFrameCompresser(lambda p: packets.append(p))
    with MockKinect() as kinect:
        then = time.time()
        kinect.add_depth_frame_listener(fc.add_frame)
        time.sleep(5)
        kinect.remove_depth_frame_listener(fc.add_frame)
        now = time.time()
    delta = now - then
    data_size = sum(sum(len(m) for m in p) for p in packets)
    data_rate = float(data_size) / delta # bytes/sec
    pps = len(packets) / delta
    print('Mock kinect runs at {0:.2f} packets/second w/ compression'.format(pps))
    print('Data rate is {0:2f} Mbytes/second'.format(data_rate / (1024*1024)))


if __name__ == '__main__':
    main()
