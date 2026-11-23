"""Camera acquisition preflight: no output recording and no GUI required."""
import argparse
import json
import platform
import time

import cv2


class CameraProbeError(RuntimeError):
    pass


def probe_camera(index=0, frames=30, capture_factory=None):
    if not isinstance(index, int) or index < 0 or not isinstance(frames, int) or frames <= 0:
        raise ValueError('Camera index must be nonnegative and frames must be positive integers')
    factory = capture_factory or cv2.VideoCapture
    # Apple's AVFoundation backend supports webcam capture in OpenCV on macOS.
    backend = cv2.CAP_AVFOUNDATION if platform.system() == 'Darwin' else cv2.CAP_ANY
    camera = factory(index, backend)
    try:
        if not camera.isOpened():
            raise CameraProbeError('Cannot open camera; check camera permission, camera index, and whether another app is using it')
        count = 0
        resolution = None
        started = time.perf_counter()
        for _ in range(frames):
            ok, frame = camera.read()
            if not ok or frame is None:
                break
            h, w = frame.shape[:2]
            resolution = [int(w), int(h)]
            count += 1
        if count == 0:
            raise CameraProbeError('Camera opened but returned no frames; check permissions and device availability')
        elapsed = time.perf_counter() - started
        return {'camera_index': index, 'frames_requested': frames, 'frames_read': count,
                'resolution': resolution, 'read_fps_including_io': round(count / max(elapsed, 1e-9), 2),
                'timestamp_scope': 'host read loop; not camera exposure latency'}
    finally:
        camera.release()


def main():
    parser = argparse.ArgumentParser(description='Probe camera without UI or video output')
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--frames', type=int, default=30)
    args = parser.parse_args()
    try:
        print(json.dumps(probe_camera(args.index, args.frames), indent=2))
    except CameraProbeError as exc:
        parser.exit(2, f'Camera probe failed: {exc}\n')


if __name__ == '__main__':
    main()
