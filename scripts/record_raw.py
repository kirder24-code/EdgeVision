"""Record original (unannotated) frames for paired offline detector benchmarks.

This intentionally does not estimate sensor exposure time or hardware dropped frames.
The captured clip may reveal private surroundings: it is never uploaded.
"""
import argparse
import json
from pathlib import Path
import time

import cv2


def record_raw(source, output, metadata, *, frames=300, width=640, height=480):
    if not isinstance(frames, int) or isinstance(frames, bool) or frames <= 0:
        raise ValueError('frames must be a positive integer')
    output_file, metadata_file = Path(output).resolve(), Path(metadata).resolve()
    if output_file == metadata_file:
        raise ValueError('Output video and metadata must be distinct')
    if not str(source).isdigit():
        if Path(source).resolve() in (output_file, metadata_file):
            raise ValueError('Cannot overwrite source video')
    source_arg = int(source) if str(source).isdigit() else str(source)
    capture = cv2.VideoCapture(source_arg)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f'Cannot open source video/camera: {source}')
    count, start = 0, time.perf_counter()
    writer = None
    observed = []
    source_fps = capture.get(cv2.CAP_PROP_FPS)
    used_fps = float(source_fps) if 0 < source_fps <= 240 else 30.0
    try:
        if isinstance(source_arg, int):
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        while count < frames:
            ok, frame = capture.read()
            if not ok:
                break
            observed.append(time.perf_counter() - start)
            if writer is None:
                h, w = frame.shape[:2]
                output_file.parent.mkdir(parents=True, exist_ok=True)
                writer = cv2.VideoWriter(str(output_file), cv2.VideoWriter_fourcc(*'MJPG'), used_fps, (w,h))
                if not writer.isOpened():
                    raise RuntimeError(f'Cannot write raw video: {output}')
            writer.write(frame)
            count += 1
    finally:
        capture.release()
        if writer is not None:
            writer.release()
    if count == 0:
        raise RuntimeError('No video frames captured')
    duration = time.perf_counter() - start
    report = {
        'purpose': 'raw_unannotated_capture', 'source': str(source),
        'output': str(output_file), 'frames_written': count,
        'nominal_output_fps': used_fps, 'host_elapsed_seconds': round(duration, 3),
        'host_capture_fps_including_io': round(count/duration, 2),
        'timestamp_scope': 'monotonic host time after VideoCapture.read, not sensor exposure',
        'warnings': 'Raw video may contain private information. File timestamps are not sensor-synchronized. No automatic upload.',
    }
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    metadata_file.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description='Record unannotated camera/video frames for paired offline evaluation')
    parser.add_argument('--source', default='0')
    parser.add_argument('--output', default='artifacts/raw_source.avi')
    parser.add_argument('--metadata', default='artifacts/raw_source.json')
    parser.add_argument('--frames', type=int, default=300)
    args = parser.parse_args()
    print(json.dumps(record_raw(args.source, args.output, args.metadata, frames=args.frames), indent=2))


if __name__ == '__main__':
    main()
